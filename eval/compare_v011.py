"""RareMCP 0.1.1 analysis: the server condition with the Drugs@FDA fix.

The main runs used RareMCP 0.1.0, whose Drugs@FDA search missed applications without an openFDA block (the
same error that was in gold v1.0). The 58 Drugs@FDA-dependent questions were re-run with 0.1.1
(eval/results/fda011-*). This script substitutes those answers into the server condition and compares the
composite ("biomcp_v011") with web search, the external comparator and no tools, scored against gold v1.1.
Writes eval/results/V011_COMPARISON.md and .json.

    python eval/compare_v011.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
from compare import boot
from score import mcnemar_exact, wilson

RES = ROOT / "eval/results"


def cells(run: str, prefix: str = "all_") -> dict:
    out: dict = {}
    f = RES / run / f"{prefix}scored.jsonl"
    for line in f.read_text().splitlines():
        x = json.loads(line)
        if not x.get("error"):
            out.setdefault(x["condition"], {})[x["qid"]] = bool(x["correct"])
    return out


def main() -> int:
    md = ["# RareMCP 0.1.1 (Drugs@FDA fix) versus comparators, gold v1.1", "",
          "Server condition = 0.1.0 answers, with the 58 Drugs@FDA-dependent questions replaced by 0.1.1 re-runs.", ""]
    res = []
    for tier, runs in (("base", {"sonnet": "v1-sonnet", "haiku": "v1-haiku"}), ("hard", {"sonnet": "hard-sonnet", "haiku": "hard-haiku"})):
        md += [f"## {tier} tier", "", "| model | condition | n | accuracy (95% CI) |", "|---|---|---|---|"]
        comp = ["| model | comparison | n | 0.1.1 only | other only | McNemar p | Δacc (95% CI) |", "|---|---|---|---|---|---|---|"]
        for m, run in runs.items():
            c = cells(run)
            fix = cells(f"fda011-{m}").get("biomcp", {})
            v = dict(c.get("biomcp", {}))
            v.update({q: ok for q, ok in fix.items() if q in v})
            c["biomcp_v011"] = v
            for cond in ("no_tools", "web_search", "biomcp_go", "biomcp", "biomcp_v011"):
                if cond in c:
                    k, n = sum(c[cond].values()), len(c[cond])
                    lo, hi = wilson(k, n)
                    md.append(f"| {m} | {cond} | {n} | {k / n:.3f} ({lo:.3f}–{hi:.3f}) |")
                    res.append({"tier": tier, "model": m, "condition": cond, "n": n, "k": k, "ci": [lo, hi]})
            for other in ("web_search", "biomcp_go", "no_tools", "biomcp"):
                if other not in c:
                    continue
                a, b = c["biomcp_v011"], c[other]
                q = sorted(set(a) & set(b))
                bo, oo = sum(a[i] and not b[i] for i in q), sum(b[i] and not a[i] for i in q)
                d = boot(lambda s, a=a, b=b: sum(a[i] - b[i] for i in s) / len(s), q)
                p = mcnemar_exact(bo, oo)
                comp.append(f"| {m} | 0.1.1 vs {other} | {len(q)} | {bo} | {oo} | {p:.3g} | {d[0]:+.3f} ({d[1]:+.3f}, {d[2]:+.3f}) |")
                res.append({"tier": tier, "model": m, "vs": other, "n": len(q), "b": bo, "c": oo, "p": p, "delta": d})
            md.append(f"| {m} | (0.1.1 re-run answers substituted: {len(fix)}) | | |")
        md += ["", *comp, ""]
    (RES / "V011_COMPARISON.md").write_text("\n".join(md) + "\n")
    (RES / "V011_COMPARISON.json").write_text(json.dumps(res, indent=1))
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
