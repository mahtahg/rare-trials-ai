"""Diagnose 'Connection closed' failures of the BioMCP comparator (no model calls).

Replays the tool-call sequences of BioMCP runs that lost their server connection, each against a fresh
`biomcp serve` process (as in the evaluation), N at a time, and records whether the server process exits,
its exit code and the tail of its stderr.

    python tools/bgo_replay.py --concurrency 2 --cache shared|separate
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def replay(seq: dict, cache: str, sem: asyncio.Semaphore, logdir: Path, i: int) -> dict:
    async with sem:
        env = dict(os.environ)
        if cache == "separate":
            env["BIOMCP_CACHE_DIR"] = tempfile.mkdtemp(prefix=f"bgo{i}_")
        errf = logdir / f"stderr_{i:03d}.log"
        res = {"i": i, "qid": seq["qid"], "n_calls": len(seq["calls"]), "results": []}
        t0 = time.time()
        try:
            with errf.open("w") as ef:
                p = StdioServerParameters(command=shutil.which("biomcp"), args=["serve"], env=env)
                async with stdio_client(p, errlog=ef) as (r, w), ClientSession(r, w) as s:
                    await s.initialize()
                    for c in seq["calls"]:
                        t = time.time()
                        try:
                            out = await asyncio.wait_for(s.call_tool(c["name"], c["input"]), 300)
                            txt = out.content[0].text if out.content else ""
                            res["results"].append({"call": c, "is_error": bool(getattr(out, "is_error", False)),
                                                   "secs": round(time.time() - t, 1), "head": txt[:160]})
                        except Exception as e:  # noqa: BLE001
                            res["results"].append({"call": c, "exception": f"{type(e).__name__}: {e}"[:300], "secs": round(time.time() - t, 1)})
                            break
        except Exception as e:  # noqa: BLE001
            res["session_exception"] = f"{type(e).__name__}: {e}"[:300]
        res["secs"] = round(time.time() - t0, 1)
        res["stderr_tail"] = errf.read_text()[-1500:] if errf.exists() else ""
        res["closed"] = any("exception" in x for x in res["results"]) or "session_exception" in res
        print(f"{i:3d} {seq['qid']:<40} calls={len(res['results'])}/{len(seq['calls'])} closed={res['closed']} {res['secs']}s", flush=True)
        return res


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--cache", choices=["shared", "separate"], default="shared")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--out", default="eval/review/bgo_diag")
    a = ap.parse_args()
    seqs = [json.loads(x) for x in (ROOT / "eval/review/bgo_replay.jsonl").read_text().splitlines() if x.strip()][: a.limit]
    out = ROOT / a.out / f"c{a.concurrency}_{a.cache}"
    out.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(a.concurrency)
    rs = await asyncio.gather(*(replay(s, a.cache, sem, out, i) for i, s in enumerate(seqs)))
    summary = {"concurrency": a.concurrency, "cache": a.cache, "n": len(rs), "closed": sum(r["closed"] for r in rs)}
    (out / "results.json").write_text(json.dumps({"summary": summary, "runs": rs}, indent=1))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
