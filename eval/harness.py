"""Run the biomcp eval: each question x condition x model x repeat.

Conditions
  no_tools    model answers from parametric knowledge only
  web_search  Anthropic server-side web search (strong generic baseline)
  biomcp      the biomcp MCP tools, executed in-process via the same MCPServer the stdio server uses

Outputs one JSON record per run in eval/results/<run_id>/raw.jsonl with the full
transcript, tool calls, token usage, latency and the parsed final answer.

Usage
  python eval/harness.py --questions eval/questions.jsonl --models claude-sonnet-5-5 \
      --conditions no_tools,web_search,biomcp --repeats 1 --max-usd 20
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from biomcp.servers.all import server as BIOMCP  # noqa: E402

# USD per million tokens (input, output); https://platform.claude.com/docs/en/about-claude/pricing (Nov 2026)
PRICES = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-fable-5-1": (10.0, 50.0),
}
CACHE_READ_MULT = 0.05
CACHE_WRITE_MULT = 1.25
WEB_SEARCH_USD = 0.01
WEB_SEARCH_TOOL = {"type": "web_search_20260318", "name": "web_search", "max_uses": 5}

MAX_TURNS = 16
MAX_TOOL_RESULT_CHARS = 20_000

SYSTEM = """You are assisting a clinical-development team working on rare and neglected diseases.
Answer the question accurately. Use tools when they are available and helpful.
If you cannot determine the answer, or the entity does not exist, say so: set "not_found": true or a low confidence. Never invent identifiers.

End your reply with exactly one block:
<answer>{"answer": <value in the requested format>, "identifiers": [<every NCT/CHEMBL/PMID/EFO/MONDO/ORPHA/Ensembl ID you relied on>], "not_found": <true|false>, "confidence": <0.0-1.0>}</answer>"""


def cost_usd(model: str, usage: dict, n_web: int) -> float:
    pin, pout = PRICES.get(model, (5.0, 25.0))
    inp = usage.get("input_tokens", 0)
    cr = usage.get("cache_read_input_tokens", 0) or 0
    cw = usage.get("cache_creation_input_tokens", 0) or 0
    out = usage.get("output_tokens", 0)
    return (inp * pin + cr * pin * CACHE_READ_MULT + cw * pin * CACHE_WRITE_MULT + out * pout) / 1e6 + n_web * WEB_SEARCH_USD


async def biomcp_tool_defs() -> list[dict]:
    tools = await BIOMCP.list_tools()
    defs = [{"name": t.name, "description": (t.description or "")[:1024], "input_schema": t.input_schema} for t in tools]
    defs[-1]["cache_control"] = {"type": "ephemeral"}  # cache the (large, static) tool block
    return defs


async def exec_biomcp(name: str, args: dict) -> tuple[str, bool]:
    try:
        res = await BIOMCP.call_tool(name, args)
    except Exception as exc:  # ToolError carries a model-readable message
        return f"ERROR: {exc}", True
    if getattr(res, "structured_content", None) is not None:
        text = json.dumps(res.structured_content, ensure_ascii=False)
    else:
        parts = [getattr(c, "text", "") for c in getattr(res, "content", []) or []]
        text = "\n".join(parts)
    if len(text) > MAX_TOOL_RESULT_CHARS:
        text = text[:MAX_TOOL_RESULT_CHARS] + "…[truncated]"
    return text, bool(getattr(res, "is_error", False))


ANSWER_RE = re.compile(r"<answer>\s*(\{.*?\})\s*</answer>", re.S)


def parse_answer(text: str) -> dict | None:
    m = ANSWER_RE.findall(text or "")
    if not m:
        return None
    try:
        return json.loads(m[-1])
    except json.JSONDecodeError:
        return None


def block_to_dict(b) -> dict:
    return b.model_dump(exclude_none=True) if hasattr(b, "model_dump") else dict(b)


async def run_one(client: anthropic.AsyncAnthropic, q: dict, model: str, condition: str, rep: int, tools: list[dict]) -> dict:
    prompt = q["question"] + (f"\n\nAnswer format: {q['answer_format']}" if q.get("answer_format") else "")
    messages: list[dict] = [{"role": "user", "content": prompt}]
    tool_calls: list[dict] = []
    usage_tot: dict[str, int] = {}
    n_web = 0
    t0 = time.monotonic()
    kwargs: dict = {"model": model, "max_tokens": 4096, "system": SYSTEM}
    if condition == "biomcp":
        kwargs["tools"] = tools
    elif condition == "web_search":
        kwargs["tools"] = [WEB_SEARCH_TOOL]
    final_text, stop, error = "", None, None
    for _turn in range(MAX_TURNS):
        try:
            resp = await client.messages.create(messages=messages, **kwargs)
        except anthropic.APIError as exc:
            error = f"{type(exc).__name__}: {exc}"
            break
        for k, v in (resp.usage.model_dump() if resp.usage else {}).items():
            if isinstance(v, int):
                usage_tot[k] = usage_tot.get(k, 0) + v
        stu = getattr(resp.usage, "server_tool_use", None)
        if stu is not None:
            n_web += getattr(stu, "web_search_requests", 0) or 0
        content = [block_to_dict(b) for b in resp.content]
        messages.append({"role": "assistant", "content": content})
        stop = resp.stop_reason
        final_text = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
        if stop == "tool_use":
            results = []
            for b in content:
                if b.get("type") != "tool_use":
                    continue
                t1 = time.monotonic()
                out, is_err = await exec_biomcp(b["name"], b.get("input") or {})
                tool_calls.append({"name": b["name"], "input": b.get("input"), "is_error": is_err,
                                   "latency_s": round(time.monotonic() - t1, 3), "output_chars": len(out)})
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": out, "is_error": is_err})
            messages.append({"role": "user", "content": results})
            continue
        if stop == "pause_turn":  # server tool (web search) paused a long turn; resume
            continue
        break
    else:
        error = "max_turns"
    return {
        "qid": q["id"], "template": q["template"], "model": model, "condition": condition, "rep": rep,
        "parsed": parse_answer(final_text), "final_text": final_text[-4000:], "stop_reason": stop, "error": error,
        "tool_calls": tool_calls, "n_web_searches": n_web, "usage": usage_tot,
        "cost_usd": round(cost_usd(model, usage_tot, n_web), 5), "latency_s": round(time.monotonic() - t0, 2),
        "transcript": messages if os.getenv("EVAL_KEEP_TRANSCRIPT", "1") == "1" else None,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(ROOT / "eval/questions.jsonl"))
    ap.add_argument("--models", default="claude-sonnet-5-5")
    ap.add_argument("--conditions", default="no_tools,web_search,biomcp")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="first N questions (stratified sample if --sample)")
    ap.add_argument("--sample", action="store_true", help="stratified random sample of --limit questions")
    ap.add_argument("--seed", type=int, default=20261103)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--max-usd", type=float, default=float(os.getenv("EVAL_MAX_USD", "20")))
    ap.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    a = ap.parse_args()

    qs = [json.loads(line) for line in Path(a.questions).read_text().splitlines() if line.strip()]
    qs = [q for q in qs if q.get("status", "active") == "active"]
    if a.limit:
        if a.sample:
            rng = random.Random(a.seed)
            by_t: dict[str, list] = {}
            for q in qs:
                by_t.setdefault(q["template"], []).append(q)
            per = max(1, a.limit // len(by_t))
            qs = [q for t in sorted(by_t) for q in rng.sample(by_t[t], min(per, len(by_t[t])))]
        else:
            qs = qs[: a.limit]

    out_dir = ROOT / "eval/results" / a.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / "raw.jsonl"
    done = set()
    if raw.exists():  # resume
        for line in raw.read_text().splitlines():
            r = json.loads(line)
            if not r.get("error"):
                done.add((r["qid"], r["model"], r["condition"], r["rep"]))

    jobs = [(q, m, c, r) for r in range(a.repeats) for m in a.models.split(",") for c in a.conditions.split(",") for q in qs
            if (q["id"], m, c, r) not in done]
    meta = {"run_id": a.run_id, "args": vars(a), "n_questions": len(qs), "n_jobs": len(jobs),
            "biomcp_version": __import__("biomcp").__version__, "started_at": datetime.now(timezone.utc).isoformat()}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    print(f"{len(jobs)} jobs -> {raw}", flush=True)

    client = anthropic.AsyncAnthropic(max_retries=6)
    tools = await biomcp_tool_defs()
    sem = asyncio.Semaphore(a.concurrency)
    spent = 0.0
    lock = asyncio.Lock()
    stop_flag = asyncio.Event()

    async def worker(job):
        nonlocal spent
        if stop_flag.is_set():
            return
        async with sem:
            if stop_flag.is_set():
                return
            rec = await run_one(client, *job, tools)
        async with lock:
            spent += rec["cost_usd"]
            with raw.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"${spent:7.3f}  {rec['condition']:<10} {rec['qid']:<28} parsed={rec['parsed'] is not None} err={rec['error']}", flush=True)
            if spent >= a.max_usd:
                print(f"BUDGET CAP ${a.max_usd} reached; stopping", flush=True)
                stop_flag.set()

    await asyncio.gather(*(worker(j) for j in jobs))
    meta["spent_usd"] = round(spent, 4)
    meta["finished_at"] = datetime.now(timezone.utc).isoformat()
    meta["budget_capped"] = stop_flag.is_set()
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
