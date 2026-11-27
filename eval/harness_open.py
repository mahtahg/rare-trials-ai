"""Run the RareMCP evaluation with open-weight models served locally (llama.cpp `llama-server`), at no cost.

Same questions, system prompt, answer block, turn cap and record format as eval/harness.py, so score.py,
compare.py and the figures work unchanged. Only the client differs: an OpenAI-compatible chat loop with tool
calling against a model served on this machine.

Stops caused by the model (turn cap, 1,200-s timeout, context window full) are recorded in stop_reason and scored
from whatever answer block the model produced, usually none, so they count as incorrect. Only infrastructure failures
(server unreachable, HTTP errors other than a full context) set `error`; score.py drops those and a resume re-runs them.

Cost guard: the harness refuses any model endpoint that is not on localhost, so it cannot call a paid API.

Conditions
  no_tools    no tools
  web_search  web_search (DuckDuckGo via the `ddgs` package, free) and web_fetch (plain HTTP GET, text only);
              Claude runs used Claude Code's built-in WebSearch/WebFetch, so this condition is comparable in
              purpose, not identical in implementation
  biomcp      the RareMCP servers (stdio MCP, same code users install)
  biomcp_go   GenomOncology BioMCP (`biomcp serve`, pinned; Python MCP client, which stays connected)

    llama-server -m model.gguf --jinja -c 32768 &
    python eval/harness_open.py --model-label gemma-4-26b-a4b-it-q4_0 --conditions no_tools,web_search,biomcp_go,biomcp \
        --questions eval/questions.jsonl --run-id open-gemma4 [--shard 0/4]
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import re
import shutil
import sys
import time
from contextlib import AsyncExitStack
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
from harness import MAX_TURNS, SYSTEM, parse_answer

TIMEOUT_S = 1200          # per run; CPU inference is slow
TOOL_OUTPUT_CHARS = 12000  # per tool result, so multi-turn runs fit a 32k-token context
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

WEB_TOOLS = [
    {"type": "function", "function": {"name": "web_search", "description": "Search the web. Returns titles, URLs and snippets.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "web_fetch", "description": "Fetch a web page by URL and return its text.",
     "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
]


def html_to_text(s: str) -> str:
    s = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


async def web_search(query: str) -> tuple[str, bool]:
    def _run():
        from ddgs import DDGS
        return list(DDGS().text(query, max_results=8))
    try:
        res = await asyncio.to_thread(_run)
        return json.dumps([{"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")} for r in res]), False
    except Exception as e:  # noqa: BLE001
        return f"search error: {type(e).__name__}: {e}", True


async def web_fetch(url: str) -> tuple[str, bool]:
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (research evaluation)"}) as c:
            r = await c.get(url)
        if r.status_code >= 400:
            return f"HTTP {r.status_code}", True
        ct = r.headers.get("content-type", "")
        return (r.text if "json" in ct or "text/plain" in ct else html_to_text(r.text)), False
    except Exception as e:  # noqa: BLE001
        return f"fetch error: {type(e).__name__}: {e}", True


class McpTools:
    """Holds one MCP stdio session for a run; exposes its tools in OpenAI format."""

    def __init__(self, command: str, args: list[str], prefix: str):
        self.command, self.args, self.prefix = command, args, prefix
        self.stack = AsyncExitStack()
        self.session = None
        self.tools: list[dict] = []

    async def __aenter__(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        devnull = self.stack.enter_context(open(os.devnull, "w"))  # noqa: ASYNC230, SIM115
        r, w = await self.stack.enter_async_context(stdio_client(
            StdioServerParameters(command=self.command, args=self.args, env=dict(os.environ)), errlog=devnull))
        self.session = await self.stack.enter_async_context(ClientSession(r, w))
        await self.session.initialize()
        listed = await self.session.list_tools()
        self.tools = [{"type": "function", "function": {"name": t.name, "description": (t.description or "")[:1024],
                                                         "parameters": (getattr(t, "input_schema", None) or getattr(t, "inputSchema", None) or {"type": "object", "properties": {}})}}
                      for t in listed.tools]
        return self

    async def __aexit__(self, *exc):
        await self.stack.aclose()

    async def call(self, name: str, args: dict) -> tuple[str, bool]:
        try:
            res = await self.session.call_tool(name, args)
            text = "\n".join(getattr(c, "text", "") for c in (res.content or []))
            return text, bool(getattr(res, "is_error", False))
        except Exception as e:  # noqa: BLE001
            return f"tool error: {type(e).__name__}: {e}", True


def mcp_for(condition: str) -> McpTools | None:
    if condition == "biomcp":
        exe = shutil.which("raremcp-all") or str(Path(sys.executable).parent / "raremcp-all")
        return McpTools(exe, [], "mcp__raremcp__")
    if condition == "biomcp_go":
        exe = shutil.which("biomcp") or str(Path(sys.executable).parent / "biomcp")
        return McpTools(exe, ["serve"], "mcp__bgo__")
    return None


SAMPLING: dict = {"temperature": 1.0}  # set from the command line; defaults follow the model developers' recommendations


# A turn that ends with no text, or with a tool call written as text (a call the server could not parse, usually
# because no tools were offered), gets one reply, as Claude Code answers a call to a tool it does not have.
TEXT_TOOL_CALL = re.compile(r"<\|?tool_call|<tool_call>|\bcall:[\w.]+[:{]|to=functions\.|\[TOOL_CALLS\]", re.IGNORECASE)
NUDGE_NO_TOOLS = "No tools are available here. Answer from your own knowledge and end with the required <answer> block."
NUDGE_EMPTY = "Your last turn had no text. Give your final answer now, ending with the required <answer> block."


async def chat(client: httpx.AsyncClient, base: str, messages: list, tools: list | None, timeout: float) -> dict:
    body = {"model": "local", "messages": messages, **SAMPLING}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    r = await client.post(f"{base}/chat/completions", json=body, timeout=timeout)
    r.raise_for_status()
    return r.json()


async def run_one(q: dict, label: str, condition: str, rep: int, base: str) -> dict:
    prompt = q["question"] + (f"\n\nAnswer format: {q['answer_format']}" if q.get("answer_format") else "")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    calls, outputs, served, usage = [], [], set(), {"prompt_tokens": 0, "completion_tokens": 0}
    final, error, stop, turns, nudges, reasoning = "", None, None, 0, [], ""
    t0 = time.monotonic()
    mcp = mcp_for(condition)
    try:
        async with AsyncExitStack() as stack:
            tools = None
            if mcp:
                await stack.enter_async_context(mcp)
                tools = mcp.tools
            elif condition == "web_search":
                tools = WEB_TOOLS
            async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
                while turns < MAX_TURNS:
                    if time.monotonic() - t0 > TIMEOUT_S:
                        stop = "timeout"
                        break
                    turns += 1
                    resp = await chat(client, base, messages, tools, max(60.0, TIMEOUT_S - (time.monotonic() - t0) + 30))
                    served.add(resp.get("model") or label)
                    for k in usage:
                        usage[k] += (resp.get("usage") or {}).get(k, 0) or 0
                    msg = resp["choices"][0]["message"]
                    tcs = msg.get("tool_calls") or []
                    content = msg.get("content") or ""
                    reasoning = (msg.get("reasoning_content") or reasoning)[-2000:]
                    messages.append({"role": "assistant", "content": content, **({"tool_calls": tcs} if tcs else {})})
                    if content.strip():
                        final = content
                    if not tcs:
                        kind = "text_tool_call" if TEXT_TOOL_CALL.search(content) else "empty" if not content.strip() else None
                        if kind and not nudges and parse_answer(content) is None:
                            nudges.append(kind)
                            messages.append({"role": "user", "content": NUDGE_NO_TOOLS if (kind == "text_tool_call" or not tools) else NUDGE_EMPTY})
                            continue
                        break
                    for tc in tcs:
                        name = tc["function"]["name"]
                        try:
                            args = json.loads(tc["function"].get("arguments") or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        if mcp:
                            out, is_err = await mcp.call(name, args)
                            logged = mcp.prefix + name
                        elif name == "web_search":
                            out, is_err = await web_search(str(args.get("query", "")))
                            logged = "WebSearch"
                        elif name == "web_fetch":
                            out, is_err = await web_fetch(str(args.get("url", "")))
                            logged = "WebFetch"
                        else:
                            out, is_err, logged = f"unknown tool {name}", True, name
                        out = out[:TOOL_OUTPUT_CHARS]
                        calls.append({"name": logged, "input": args, "is_error": is_err, "output_chars": len(out)})
                        outputs.append(out)
                        messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": out})
                else:
                    stop = "max_turns"
    except httpx.HTTPStatusError as e:
        body = e.response.text[:400]
        if e.response.status_code == 400 and re.search(r"context|n_ctx|too long|exceed", body, re.IGNORECASE):
            stop = "context_limit"  # the conversation outgrew the 32k-token window: a model-side stop, scored as answered
        else:
            error = f"error: HTTP {e.response.status_code}: {body}"
    except Exception as e:  # noqa: BLE001
        error = f"error: {type(e).__name__}: {str(e)[:400]}"
    return {"qid": q["id"], "template": q["template"], "model": label, "condition": condition, "rep": rep,
            "served_models": sorted(served), "parsed": parse_answer(final), "final_text": final[-4000:],
            "error": error, "stop_reason": stop, "nudges": nudges, "reasoning_tail": reasoning, "usage_limited": False, "tool_calls": calls, "tool_outputs": outputs,
            "n_web_searches": sum(1 for c in calls if c["name"] == "WebSearch"), "num_turns": turns, "usage": usage,
            "api_equivalent_cost_usd": 0.0, "latency_s": round(time.monotonic() - t0, 2),
            "finished_at": datetime.now(timezone.utc).isoformat()}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(ROOT / "eval/questions.jsonl"))
    ap.add_argument("--model-label", required=True, help="recorded as the model id, e.g. gemma-4-26b-a4b-it-q4_0")
    ap.add_argument("--conditions", default="no_tools,web_search,biomcp_go,biomcp")
    ap.add_argument("--base-url", default=os.getenv("OPEN_BASE_URL", "http://127.0.0.1:8080/v1"))
    ap.add_argument("--shard", default="0/1", help="i/N: run every N-th question starting at i")
    ap.add_argument("--max-minutes", type=float, default=330)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--sampling", default='{"temperature": 1.0}', help="JSON sampling settings sent with every request")
    a = ap.parse_args()
    SAMPLING.clear()
    SAMPLING.update(json.loads(a.sampling))
    host = urlparse(a.base_url).hostname
    if host not in LOCAL_HOSTS:
        print(f"Refusing to run: {a.base_url} is not a local endpoint (cost guard).", file=sys.stderr)
        return 2
    i, n = (int(x) for x in a.shard.split("/"))
    qs = [json.loads(x) for x in Path(a.questions).read_text().splitlines() if x.strip()]
    qs = [q for k, q in enumerate(q for q in qs if q.get("status", "active") == "active") if k % n == i]
    out_dir = ROOT / "eval/results" / a.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / f"raw.shard{i}of{n}.jsonl" if n > 1 else out_dir / "raw.jsonl"
    done = set()
    if raw.exists():
        for line in raw.read_text().splitlines():
            r = json.loads(line)
            if not r.get("error"):
                done.add((r["qid"], r["condition"]))
    jobs = [(q, c) for q in qs for c in a.conditions.split(",") if (q["id"], c) not in done]
    print(f"{len(jobs)} runs pending ({len(done)} done) for {a.model_label}, shard {a.shard}", flush=True)
    t_end = time.monotonic() + 60 * a.max_minutes
    with raw.open("a") as f:
        for k, (q, c) in enumerate(jobs, 1):
            if time.monotonic() > t_end:
                print("time budget reached; re-run to resume", flush=True)
                break
            rec = await run_one(q, a.model_label, c, 0, a.base_url)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            print(f"{k:4d}/{len(jobs)} {c:<10} {q['id']:<32} parsed={rec['parsed'] is not None} calls={len(rec['tool_calls'])} "
                  f"{rec['latency_s']}s {rec['error'] or ''}", flush=True)
    meta = out_dir / "meta.json"
    m = json.loads(meta.read_text()) if meta.exists() else {"run_id": a.run_id, "model": a.model_label, "sessions": []}
    m["sampling"] = SAMPLING
    m["tool_output_chars"], m["timeout_s"], m["max_turns"] = TOOL_OUTPUT_CHARS, TIMEOUT_S, MAX_TURNS
    m["sessions"].append({"shard": a.shard, "finished_at": datetime.now(timezone.utc).isoformat(), "pending_at_start": len(jobs)})
    meta.write_text(json.dumps(m, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
