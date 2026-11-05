"""Import a filled-in biomcp_question_review.xlsx.

Writes eval/review/ratings.jsonl (one row per rated question) and eval/excluded_questions.json
(question ids with verdict Drop, or a gold check answered No), which score.py --exclude reads.

    python eval/review/import_review_xlsx.py path/to/biomcp_question_review.xlsx
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ws = load_workbook(sys.argv[1], data_only=True)["Questions"]
    head = [c.value for c in ws[1]]
    ix = {h: i for i, h in enumerate(head)}
    rows, problems = [], []
    for r in ws.iter_rows(min_row=2, values_only=True):
        qid = r[ix["Question ID"]]
        if not qid:
            continue
        v, re_, g, note = (r[ix[k]] for k in ("Verdict", "Realism (1-5)", "Gold correct?", "Edited wording / notes"))
        if v is None and re_ is None:
            continue
        v = (v or "").strip().lower() or None
        if v not in (None, "keep", "edit", "drop"):
            problems.append(f"{qid}: verdict {v!r}")
        if v in ("edit", "drop") and not note:
            problems.append(f"{qid}: {v} without a note")
        rows.append({"id": qid, "verdict": v, "realism": int(re_) if re_ is not None else None,
                     "gold_ok": (g or "").strip().lower() or None, "note": note or None,
                     "spot_check": r[ix["Gold check?"]] == "Yes"})
    out = ROOT / "eval/review/ratings.jsonl"
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n")
    excl = sorted({x["id"] for x in rows if x["verdict"] == "drop" or x["gold_ok"] == "no"})
    (ROOT / "eval/excluded_questions.json").write_text(json.dumps(excl, indent=1) + "\n")
    print(f"{len(rows)} rated; {len(excl)} excluded; problems: {problems or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
