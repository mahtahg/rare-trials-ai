"""Import v3 item-level review workbooks and compute inter-rater agreement.

    python eval/review/import_review_v3.py review_v3_MHG.xlsx [review_v3_AA.xlsx]
Writes eval/review/ratings_v3_<initials>.jsonl, eval/review/agreement_v3.json, and (from the primary
reviewer, MHG) eval/excluded_questions_v3.json with the items rated Drop.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
KEY = json.loads((ROOT / "eval/review/v3_key.json").read_text())["key"]


def read(path: str) -> tuple[str, dict, list[str]]:
    wb = load_workbook(path, data_only=True)
    ins = {str(r[0]).strip(): r[1] for r in wb["Instructions"].iter_rows(values_only=True) if r[0]}
    ini = "".join(w[0] for w in str(ins.get("Reviewer", "X")).split()).upper()[:3]
    att = ins.get("I rated every item myself, without AI assistance (Yes/No)")
    rows, problems = {}, []
    for r in wb["Review"].iter_rows(min_row=2, values_only=True):
        code = r[0]
        if not code:
            continue
        clear, ans, sound, realism, verdict, note = r[3:9]
        if verdict is None and realism is None:
            continue
        rec = {"code": code, "id": KEY[code], "clear": clear, "answerable": ans, "sound": sound,
               "realism": int(realism) if realism is not None else None, "verdict": (verdict or "").lower() or None, "note": note}
        if (rec["verdict"] in ("edit", "drop") or "No" in (clear, ans, sound)) and not note:
            problems.append(f"{code}: needs a note")
        rows[code] = rec
    if att != "Yes":
        problems.append("attestation not 'Yes' (AI-free independent rating not confirmed)")
    return ini, rows, problems


def cohen(a, b):
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else None


def weighted_kappa(a, b, k=5):
    n = len(a)
    if not n:
        return None
    w = lambda i, j: ((i - j) ** 2) / ((k - 1) ** 2)  # quadratic weights
    ca, cb = Counter(a), Counter(b)
    do = sum(w(x, y) for x, y in zip(a, b)) / n
    de = sum(ca[i] * cb[j] * w(i, j) for i in range(1, k + 1) for j in range(1, k + 1)) / (n * n)
    return round(1 - do / de, 4) if de else None


def main() -> int:
    readers = [read(p) for p in sys.argv[1:]]
    for ini, rows, problems in readers:
        (ROOT / f"eval/review/ratings_v3_{ini}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows.values()) + "\n")
        print(f"{ini}: {len(rows)} rated; problems: {problems or 'none'}")
        if ini == "MHG":
            drops = sorted(r["id"] for r in rows.values() if r["verdict"] == "drop")
            (ROOT / "eval/excluded_questions_v3.json").write_text(json.dumps(drops, indent=1) + "\n")
    if len(readers) == 2:
        (_, a, _), (_, b, _) = readers
        both = sorted(set(a) & set(b))
        res = {"n": len(both)}
        for f in ("clear", "answerable", "sound", "verdict"):
            x, y = [a[c][f] for c in both], [b[c][f] for c in both]
            res[f] = {"agreement": round(sum(i == j for i, j in zip(x, y)) / len(both), 4) if both else None, "kappa": cohen(x, y)}
        x = [a[c]["realism"] for c in both if a[c]["realism"] and b[c]["realism"]]
        y = [b[c]["realism"] for c in both if a[c]["realism"] and b[c]["realism"]]
        res["realism"] = {"n": len(x), "quadratic_weighted_kappa": weighted_kappa(x, y)}
        res["keep_vs_not"] = {"kappa": cohen([a[c]["verdict"] == "keep" for c in both], [b[c]["verdict"] == "keep" for c in both])}
        (ROOT / "eval/review/agreement_v3.json").write_text(json.dumps(res, indent=1))
        print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
