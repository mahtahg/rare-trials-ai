"""Robustness check: does searching Drugs@FDA by openfda.generic_name (used for the gold answers) miss
applications that a search by products.active_ingredients.name finds? Older applications often lack the
openfda block. Re-derives the Drugs@FDA-dependent gold answers both ways and writes
eval/review/fda_search_check.{jsonl,md}. No model calls.

    python eval/review/fda_search_check.py
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
FDA = "https://api.fda.gov/drug/drugsfda.json"
C = httpx.Client(timeout=60, headers={"User-Agent": "rare-trials-ai fda check (+github.com/mahtahg/rare-trials-ai)"})


def fetch(search: str) -> list[dict]:
    out, skip, total = [], 0, 1
    while skip < total and skip < 1000:
        for i in range(5):
            r = C.get(FDA, params={"search": search, "limit": 100, "skip": skip})
            if r.status_code in (429, 500, 502, 503):
                time.sleep(2 ** i)
                continue
            break
        if r.status_code == 404:
            return out
        r.raise_for_status()
        b = r.json()
        out += b["results"]
        total = b["meta"]["results"]["total"]
        skip += 100
    return out


def by_generic(name):
    return fetch(f'openfda.generic_name:"{name}"')


def by_ingredient(name):
    return fetch(f'products.active_ingredients.name:"{name}"')


def earliest_nda(apps):
    yrs = [int(s["submission_status_date"][:4]) for a in apps if a["application_number"].startswith("NDA")
           for s in a.get("submissions", []) if s.get("submission_type") == "ORIG" and s.get("submission_status") == "AP" and s.get("submission_status_date")]
    return min(yrs) if yrs else None


def marketed_anda(apps):
    return any(a["application_number"].startswith("ANDA") and any(p.get("marketing_status") in ("Prescription", "Over-the-counter")
               for p in a.get("products", [])) for a in apps) if apps else None


def main() -> int:
    qs = []
    for f in ("eval/questions.jsonl", "eval/questions_hard.jsonl"):
        qs += [json.loads(x) for x in (ROOT / f).read_text().splitlines() if x.strip()]
    rows = []
    for q in qs:
        if q["template"] == "h_source_conflict":
            name = re.search(r"year for (.+?) \(CHEMBL", q["question"]).group(1)
            g, i = by_generic(name), by_ingredient(name.upper())
            fa = q["basis"]["chembl_first_approval"]
            eg, ei = earliest_nda(g), earliest_nda(i)
            rows.append({"id": q["id"], "drug": name, "gold": q["gold"], "chembl_year": fa, "nda_year_generic_search": eg,
                         "nda_year_ingredient_search": ei, "answer_ingredient_search": (fa == ei) if ei else None,
                         "changes": ((fa == ei) if ei else None) != q["gold"]})
        elif q["template"] == "drug_generic_us":
            name = re.search(r"Is (.+?) currently available", q["question"]).group(1)
            g, i = by_generic(name), by_ingredient(name.upper())
            mg, mi = marketed_anda(g), marketed_anda(i)
            rows.append({"id": q["id"], "drug": name, "gold": q["gold"], "generic_search": mg, "ingredient_search": mi, "changes": mi is not None and mi != q["gold"]})
        print(rows[-1] if rows and rows[-1]["id"] == q["id"] else "", flush=True)
    (ROOT / "eval/review/fda_search_check.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    ch = [r for r in rows if r["changes"]]
    md = ["# Drugs@FDA search robustness", "", f"{len(rows)} Drugs@FDA-dependent questions re-derived with an active-ingredient search; "
          f"{len(ch)} would change answer.", "", "| id | drug | gold | generic-name search | ingredient search |", "|---|---|---|---|---|"]
    for r in rows:
        a = (r.get("nda_year_generic_search"), r.get("nda_year_ingredient_search")) if "chembl_year" in r else (r.get("generic_search"), r.get("ingredient_search"))
        md.append(f"| {r['id']} | {r['drug']} | {r['gold']} | {a[0]} | {a[1]} |" + (" **changes**" if r["changes"] else ""))
    (ROOT / "eval/review/fda_search_check.md").write_text("\n".join(md) + "\n")
    print(md[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
