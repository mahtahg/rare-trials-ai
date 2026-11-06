"""Run the RareMCP eval through headless Claude Code (`claude -p`).

Condition id `biomcp` = the RareMCP servers (named biomcp-rare until 2026-11-06; the id is kept so earlier runs stay comparable).

Authentication is the Claude subscription OAuth token (CLAUDE_CODE_OAUTH_TOKEN,
from `claude setup-token`), so runs draw on subscription usage, not API billing.
If ANTHROPIC_API_KEY is present the harness refuses to start, so a stray key can
never silently switch billing.

Conditions (identical system prompt, model and turn cap; only the tools differ)
  no_tools    no built-in tools, no MCP servers
  web_search  Claude Code's WebSearch + WebFetch only
  biomcp      the RareMCP servers only (stdio, same code users install)
  biomcp_go   external comparator: GenomOncology BioMCP (biomcp-cli, pinned)

Each run is recorded as one JSON line in eval/results/<run_id>/raw.jsonl with
the full event stream (tool calls + results), turns, latency, the model that
actually served the run, and Claude Code's API-equivalent cost estimate (not billed).

Usage limits: when the subscription limit is hit the harness stops cleanly;
re-running with the same --run-id resumes where it left off.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SYSTEM = """You are assisting a clinical-development team working on rare and neglected diseases.
Answer the question accurately. Use the tools available to you when they help; do not use tools you were not given.
If you cannot determine the answer, or the entity does not exist, say so: set "not_found": true or give a low confidence. Never invent identifiers.

End your reply with exactly one block:
<answer>{"answer": <value in the requested format>, "identifiers": [<every NCT/CHEMBL/PMID/EFO/MONDO/ORPHA/Ensembl ID you relied on>], "not_found": <true|false>, "confidence": <0.0-1.0>}</answer>"""

MAX_TURNS = 20
TIMEOUT_S = 600
LIMIT_PATTERNS = re.compile(r"usage limit|rate limit|limit reached|hit your .{0,20}limit|resets \d|too many requests|overloaded|429", re.IGNORECASE)
ANSWER_RE = re.compile(r"<answer>\s*(\{.*?\})\s*</answer>", re.DOTALL)


def parse_answer(text: str) -> dict | None:
    m = ANSWER_RE.findall(text or "")
    if not m:
        return None
    try:
        return json.loads(m[-1])
    except json.JSONDecodeError:
        return None


def mcp_config(path: Path) -> Path:
    exe = shutil.which("raremcp-all") or str(Path(sys.executable).parent / "raremcp-all")
    path.write_text(json.dumps({"mcpServers": {"raremcp": {"command": exe, "args": []}}}))
    return path


def mcp_config_external(path: Path) -> Path:
    """External comparator: GenomOncology BioMCP (`pip install biomcp-cli`, MIT), run over stdio as `biomcp serve`."""
    exe = shutil.which("biomcp") or str(Path(sys.executable).parent / "biomcp")
    path.write_text(json.dumps({"mcpServers": {"bgo": {"command": exe, "args": ["serve"]}}}))
    return path


def build_cmd(prompt: str, model: str, condition: str, cfg: Path) -> list[str]:
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--output-format", "stream-json", "--verbose",
        "--append-system-prompt", SYSTEM,
        "--max-turns", str(MAX_TURNS),
        "--no-session-persistence",
        "--permission-prompts", "none",
        "--strict-mcp-config",
        "--setting-sources", "",
    ]
    if condition == "no_tools":
        cmd += ["--tools", "", "--disallowedTools", "mcp__*"]
    elif condition == "web_search":
        cmd += ["--tools", "WebSearch,WebFetch", "--allowedTools", "WebSearch,WebFetch"]
    elif condition == "biomcp":
        cmd += ["--tools", "", "--mcp-config", str(cfg), "--allowedTools", "mcp__raremcp__*"]
    elif condition == "biomcp_go":
        cmd += ["--tools", "", "--mcp-config", str(cfg.with_name("bgo-mcp.json")), "--allowedTools", "mcp__bgo__*"]
    else:
        raise ValueError(condition)
    return cmd


def summarize_events(events: list[dict]) -> dict:
    tool_calls, tool_results = [], {}
    final, result_ev, models = "", None, set()
    for ev in events:
        t = ev.get("type")
        if t == "assistant":
            msg = ev.get("message", {})
            if msg.get("model"):
                models.add(msg["model"])
            for b in msg.get("content", []) or []:
                if b.get("type") == "tool_use":
                    tool_calls.append({"id": b.get("id"), "name": b.get("name"), "input": b.get("input")})
                elif b.get("type") == "text":
                    final = b.get("text", "")
        elif t == "user":
            for b in (ev.get("message", {}) or {}).get("content", []) or []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    c = b.get("content")
                    if isinstance(c, list):
                        c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
                    tool_results[b.get("tool_use_id")] = {"is_error": bool(b.get("is_error")), "content": c}
        elif t == "result":
            result_ev = ev
    for tc in tool_calls:
        r = tool_results.get(tc["id"], {})
        tc["is_error"] = r.get("is_error", False)
        tc["output"] = r.get("content")
    if result_ev and result_ev.get("result"):
        final = result_ev["result"]
    return {"tool_calls": tool_calls, "final_text": final, "result": result_ev, "models": sorted(models)}


async def run_one(q: dict, model: str, condition: str, rep: int, cfg: Path, workdir: Path) -> dict:
    prompt = q["question"] + (f"\n\nAnswer format: {q['answer_format']}" if q.get("answer_format") else "")
    cmd = build_cmd(prompt, model, condition, cfg)
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    t0 = time.monotonic()
    proc = await asyncio.create_subprocess_exec(*cmd, cwd=workdir, env=env,
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), TIMEOUT_S)
        timed_out = False
    except asyncio.TimeoutError:
        proc.kill()
        out, err = await proc.communicate()
        timed_out = True
    events = []
    for line in out.decode("utf-8", "replace").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    s = summarize_events(events)
    res = s["result"] or {}
    err_txt = err.decode("utf-8", "replace")[-2000:]
    error = None
    if timed_out:
        error = "timeout"
    elif res.get("is_error") or proc.returncode != 0:
        error = (res.get("subtype") or "error") + ": " + str(res.get("result") or err_txt)[:500]
    limited = bool(error and LIMIT_PATTERNS.search(error + err_txt))
    return {
        "qid": q["id"], "template": q["template"], "model": model, "condition": condition, "rep": rep,
        "served_models": s["models"], "parsed": parse_answer(s["final_text"]), "final_text": (s["final_text"] or "")[-4000:],
        "error": error, "usage_limited": limited,
        "tool_calls": [{k: tc.get(k) for k in ("name", "input", "is_error")} | {"output_chars": len(tc.get("output") or "")}
                       for tc in s["tool_calls"]],
        "tool_outputs": [tc.get("output") for tc in s["tool_calls"]],
        "n_web_searches": sum(1 for tc in s["tool_calls"] if tc["name"] == "WebSearch"),
        "num_turns": res.get("num_turns"), "usage": res.get("usage"),
        "api_equivalent_cost_usd": res.get("total_cost_usd"),  # Claude Code's estimate; NOT billed on subscription
        "latency_s": round(time.monotonic() - t0, 2),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(ROOT / "eval/questions.jsonl"))
    ap.add_argument("--models", default="claude-sonnet-5-5")
    ap.add_argument("--conditions", default="no_tools,web_search,biomcp")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sample", action="store_true", help="stratified sample of --limit questions")
    ap.add_argument("--seed", type=int, default=20261103)
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--max-runs", type=int, default=0, help="stop after this many runs in this invocation")
    ap.add_argument("--max-minutes", type=float, default=300)
    ap.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    a = ap.parse_args()

    if os.getenv("ANTHROPIC_API_KEY"):
        print("Refusing to run: ANTHROPIC_API_KEY is set (would bill the API). Use CLAUDE_CODE_OAUTH_TOKEN.", file=sys.stderr)
        return 2
    if not os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        print("CLAUDE_CODE_OAUTH_TOKEN not set", file=sys.stderr)
        return 2

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
    if raw.exists():
        for line in raw.read_text().splitlines():
            r = json.loads(line)
            if not r.get("error"):
                done.add((r["qid"], r["model"], r["condition"], r["rep"]))

    # interleave conditions per question so a usage-limit stop leaves balanced, paired data
    jobs = [(q, m, c, r) for r in range(a.repeats) for q in qs for m in a.models.split(",") for c in a.conditions.split(",")
            if (q["id"], m, c, r) not in done]
    if a.max_runs:
        jobs = jobs[: a.max_runs]
    meta_p = out_dir / "meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {"run_id": a.run_id, "sessions": []}
    meta.update({"args": vars(a), "n_questions": len(qs), "auth": "claude-subscription-oauth",
                 "system_prompt": SYSTEM, "max_turns": MAX_TURNS})
    sess = {"started_at": datetime.now(timezone.utc).isoformat(), "pending_jobs": len(jobs)}
    meta["sessions"].append(sess)
    meta_p.write_text(json.dumps(meta, indent=1))
    print(f"{len(jobs)} pending jobs -> {raw}", flush=True)

    workdir = Path(tempfile.mkdtemp(prefix="biomcp-eval-"))  # empty cwd: no repo CLAUDE.md or files leak in
    cfg = mcp_config(workdir.parent / "biomcp-mcp.json")
    if "biomcp_go" in a.conditions:
        mcp_config_external(workdir.parent / "bgo-mcp.json")
        meta["external_comparator_version"] = os.getenv("BGO_VERSION", "unrecorded")  # set by the workflow from `biomcp version`
        meta_p.write_text(json.dumps(meta, indent=1))
    sem = asyncio.Semaphore(a.concurrency)
    lock = asyncio.Lock()
    stop = asyncio.Event()
    deadline = time.monotonic() + a.max_minutes * 60
    n_done = 0

    async def worker(job):
        nonlocal n_done
        if stop.is_set() or time.monotonic() > deadline:
            return
        async with sem:
            if stop.is_set() or time.monotonic() > deadline:
                return
            rec = await run_one(*job, cfg, workdir)
        async with lock:
            if rec["usage_limited"]:
                stop.set()
                print(f"USAGE LIMIT reached ({rec['error'][:120]}); stopping. Re-run with --run-id {a.run_id} to resume.", flush=True)
                return  # not recorded: will be retried on resume
            with raw.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_done += 1
            print(f"{n_done:4d} {rec['condition']:<10} {rec['qid']:<30} parsed={rec['parsed'] is not None} "
                  f"tools={len(rec['tool_calls'])} err={rec['error']}", flush=True)

    await asyncio.gather(*(worker(j) for j in jobs))
    sess.update({"finished_at": datetime.now(timezone.utc).isoformat(), "completed_runs": n_done,
                 "stopped_for_usage_limit": stop.is_set()})
    meta_p.write_text(json.dumps(meta, indent=1))
    remaining = len(jobs) - n_done
    print(f"done {n_done}, remaining {remaining}", flush=True)
    (out_dir / "REMAINING").write_text(str(remaining))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
