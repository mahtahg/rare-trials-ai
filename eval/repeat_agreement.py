"""Run-to-run agreement: the full evaluation repeated once (rep2-* runs) against the main runs.

Scores the rep2 runs on all 314 questions against gold v1.1 (prefix all_, no exclusions), then compares
correct/incorrect per question with the main runs, per tier, model and condition: percent agreement, Cohen's
kappa, and accuracy in each run. The repeat used RareMCP 0.1.1, so its RareMCP condition is compared with the
post hoc composite (0.1.0 answers, with the 58 Drugs@FDA-dependent questions from the 0.1.1 re-run); BioMCP is
compared with the proxied BioMCP arm. Writes eval/results/REPEAT_AGREEMENT.md and .json.

    python eval/repeat_agreement.py [--no-score]
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "eval/results"
PAIRS = [("base", "sonnet", "v1-sonnet", "rep2-sonnet", "eval/questions.jsonl"),
         ("base", "haiku", "v1-haiku", "rep2-haiku", "eval/questions.jsonl"),
         ("hard", "sonnet", "hard-sonnet", "rep2-hard-sonnet", "eval/questions_hard.jsonl"),
         ("hard", "haiku", "hard-haiku", "rep2-hard-haiku", "eval/questions_hard.jsonl")]
CONDS = [("no_tools", "No tools"), ("web_search", "Web search"), ("biomcp_go", "BioMCP"), ("biomcp", "RareMCP (0.1.1)")]


def cells(run: str) -> dict:
    out: dict = {}
    for line in (RES / run / "all_scored.jsonl").read_text().splitlines():
        x = json.loads(line)
        if not x.get("error"):
            out.setdefault(x["condition"], {})[x["qid"]] = bool(x["correct"])
    return out


def kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def main() -> int:
    if "--no-score" not in sys.argv:
        for _, _, _, rep, q in PAIRS:
            subprocess.run([sys.executable, str(ROOT / "eval/score.py"), "--questions", q, "--run", str(RES / rep),
                            "--exclude", "", "--prefix", "all_"], check=True)
    rows, md = [], ["# Run-to-run agreement (main runs versus one full repeat; gold v1.1, all questions)", "",
                    "| Tier | Model | Condition | n | Agreement | Cohen's kappa | Accuracy, run 1 | Accuracy, run 2 |",
                    "|---|---|---|---|---|---|---|---|"]
    pooled_a, pooled_b = [], []
    for tier, model, main_run, rep, _ in PAIRS:
        m, r = cells(main_run), cells(rep)
        fix = cells(f"fda011-{model}").get("biomcp", {})
        m["biomcp"] = {**m.get("biomcp", {}), **{q: v for q, v in fix.items() if q in m.get("biomcp", {})}}
        for cond, name in CONDS:
            q = sorted(set(m.get(cond, {})) & set(r.get(cond, {})))
            if not q:
                continue
            a, b = [m[cond][i] for i in q], [r[cond][i] for i in q]
            pooled_a += a
            pooled_b += b
            agr, k = sum(x == y for x, y in zip(a, b)) / len(q), kappa(a, b)
            rows.append({"tier": tier, "model": model, "condition": cond, "n": len(q), "agreement": agr, "kappa": k,
                         "acc1": sum(a) / len(q), "acc2": sum(b) / len(q)})
            md.append(f"| {tier} | {model} | {name} | {len(q)} | {100 * agr:.1f}% | {k:.2f} | {100 * sum(a) / len(q):.1f}% | {100 * sum(b) / len(q):.1f}% |")
    if pooled_a:
        agr, k = sum(x == y for x, y in zip(pooled_a, pooled_b)) / len(pooled_a), kappa(pooled_a, pooled_b)
        md += ["", f"Pooled over all tiers, models and conditions: n = {len(pooled_a)}, agreement {100 * agr:.1f}%, Cohen's kappa {k:.2f}."]
        rows.append({"pooled": True, "n": len(pooled_a), "agreement": agr, "kappa": k})
    (RES / "REPEAT_AGREEMENT.md").write_text("\n".join(md) + "\n")
    (RES / "REPEAT_AGREEMENT.json").write_text(json.dumps(rows, indent=1))
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
