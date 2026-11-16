"""Why was web search wrong? A check for stale or disagreeing web sources.

For every web-search answer scored incorrect against gold v1.1 (all 314 questions, both models), compare the
answer and the gold answer with what the run actually retrieved (WebSearch results and WebFetch page summaries,
as logged in raw.jsonl):

  abstained            the model said it could not find the answer
  gold retrieved       the retrieved text contained the gold answer (>= half of a gold set), so the error was in
                       reading or reasoning, not in the source
  source disagrees     the retrieved text supported the model's (wrong) answer but not the gold answer: a web
                       source that differs from the database at retrieval time, the signature of staleness
  not retrieved        neither appeared: the model did not reach data containing the answer and answered from
                       partial results or memory
  yes/no judgement     EU-rarity and other yes/no items, where string matching cannot tell these apart; split by
                       whether any prevalence figure was retrieved

String matching is approximate (synonyms and name variants are missed), so "not retrieved" is an upper bound and
"gold retrieved" a lower bound. Writes eval/results/WEB_STALENESS.md and .json.

    python eval/staleness_check.py
"""

from __future__ import annotations

import ast
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "eval/results"
RUNS = ("v1-sonnet", "v1-haiku", "hard-sonnet", "hard-haiku")
YESNO = {"disease_rarity", "trial_has_sap", "drug_generic_us", "h_eligibility_check", "h_source_conflict"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def present(item, text: str) -> bool:
    n = norm(item)
    return bool(n) and (f" {n} " in f" {text} ")


def parsed_answer(x: dict):
    p = x.get("parsed")
    if isinstance(p, str):
        try:
            p = ast.literal_eval(p)
        except Exception:  # noqa: BLE001
            try:
                p = json.loads(p)
            except Exception:  # noqa: BLE001
                p = None
    return p if isinstance(p, dict) else {}


def main() -> int:
    qs = {}
    for f in ("eval/questions.jsonl", "eval/questions_hard.jsonl"):
        for line in (ROOT / f).read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                qs[q["id"]] = q
    corr = json.loads((ROOT / "eval/gold_corrections_v1_1.json").read_text())["corrections"]
    rows = []
    for run in RUNS:
        wrong = {}
        for line in (RES / run / "all_scored.jsonl").read_text().splitlines():
            s = json.loads(line)
            if s["condition"] == "web_search" and not s.get("error") and not s["correct"]:
                wrong[s["qid"]] = s
        raw = {}
        for line in (RES / run / "raw.jsonl").read_text().splitlines():
            x = json.loads(line)
            if x["condition"] == "web_search" and x["qid"] in wrong:
                raw[x["qid"]] = x  # last record wins, as in scoring
        for qid, x in raw.items():
            q = qs[qid]
            gold = corr[qid]["new"] if qid in corr else q["gold"]
            p = parsed_answer(x)
            ans = p.get("answer")
            outs = x.get("tool_outputs") or []
            text = " " + norm(" ".join(o if isinstance(o, str) else json.dumps(o) for o in outs)) + " "
            fetched = [t.get("input", {}).get("url", "") for t in x["tool_calls"] if t["name"] == "WebFetch"]
            n_calls = len(x["tool_calls"])
            if p.get("not_found") or ans in (None, "", [], "unknown"):
                cat = "abstained"
            elif q["template"] in YESNO:
                prev = bool(re.search(r"prevalence|per 100 000|per 10 000|1 \d+ 000|incidence", text))
                cat = "yes/no judgement, prevalence retrieved" if (q["template"] == "disease_rarity" and prev) else (
                    "yes/no judgement, no prevalence retrieved" if q["template"] == "disease_rarity" else "yes/no judgement")
            else:
                g = gold if isinstance(gold, list) else [gold]
                a = ans if isinstance(ans, list) else [ans]
                g_cov = sum(present(i, text) for i in g) / max(1, len(g))
                a_cov = sum(present(i, text) for i in a) / max(1, len(a))
                if g_cov >= 0.5:
                    cat = "gold retrieved"
                elif a_cov >= 0.5:
                    cat = "source disagrees"
                else:
                    cat = "not retrieved"
            rows.append({"run": run, "qid": qid, "template": q["template"], "category": cat, "n_tool_calls": n_calls,
                         "fetched_hosts": sorted({re.sub(r"^https?://([^/]+).*", r"\1", u) for u in fetched if u}),
                         "gold_retrieved_at": q.get("gold_retrieved_at"), "finished_at": x.get("finished_at")})
    by_cat = collections.Counter(r["category"] for r in rows)
    by_tc = collections.Counter((r["template"], r["category"]) for r in rows)
    hosts = collections.Counter(h for r in rows for h in r["fetched_hosts"])
    md = ["# Why web search was wrong: staleness check (gold v1.1, all 314 questions, both models)", "",
          f"Incorrect web-search answers: {len(rows)}", "", "| Category | n | % |", "|---|---|---|"]
    for c, n in by_cat.most_common():
        md.append(f"| {c} | {n} | {100 * n / len(rows):.0f} |")
    md += ["", "## By template", "", "| Template | Category | n |", "|---|---|---|"]
    for (t, c), n in sorted(by_tc.items()):
        md.append(f"| {t} | {c} | {n} |")
    md += ["", "## Hosts fetched in incorrect runs (top 12)", "", "| Host | runs |", "|---|---|"]
    for h, n in hosts.most_common(12):
        md.append(f"| {h} | {n} |")
    (RES / "WEB_STALENESS.md").write_text("\n".join(md) + "\n")
    (RES / "WEB_STALENESS.json").write_text(json.dumps({"summary": dict(by_cat), "rows": rows}, indent=1))
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
