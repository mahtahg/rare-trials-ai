"""Item-level question review workbooks (v3), one per reviewer.

Designed so that ratings are made item by item: questions are in a seeded random order, carry neutral codes
(R001...) instead of template ids, show no question type and no gold answer, and every Edit/Drop or "No"
needs a note. The code key stays in the repo (eval/review/v3_key.json), not in the workbook.

    python eval/review/build_review_v3.py OUT_DIR
Writes review_v3_MHG.xlsx (all 314) and review_v3_AA.xlsx (stratified 100, for inter-rater agreement).
"""

from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[2]
F = "Arial"
B, BOLD, HDR, TITLE = Font(name=F, size=10), Font(name=F, size=10, bold=True), Font(name=F, size=10, bold=True, color="FFFFFF"), Font(name=F, size=14, bold=True)
FH, FIN, GREY = PatternFill("solid", fgColor="1F3A5F"), PatternFill("solid", fgColor="FFF4C2"), PatternFill("solid", fgColor="F2F2F2")
thin = Side(style="thin", color="CCCCCC")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")

ANCHORS = [
    ("5", "Routine: a trial or repurposing team asks this most weeks (e.g. why did this trial stop; is this drug available as a generic)."),
    ("4", "Common: asked when planning or reviewing a programme, though not weekly."),
    ("3", "Occasional: a real need for some projects or roles."),
    ("2", "Unusual: plausible, but few people would ask it in this form."),
    ("1", "Contrived: exists to test the system rather than to meet a real need (e.g. a made-up identifier)."),
]


def load():
    qs = []
    for f in ("eval/questions.jsonl", "eval/questions_hard.jsonl"):
        qs += [json.loads(x) for x in (ROOT / f).read_text().splitlines() if x.strip()]
    return qs


def sheet(wb: Workbook, reviewer: str, initials: str, items: list[dict], n_total: int):
    ins = wb.active
    ins.title = "Instructions"
    ins.column_dimensions["A"].width = 26
    ins.column_dimensions["B"].width = 100
    ins["A1"] = "RareMCP evaluation: item-level question review"
    ins["A1"].font = TITLE
    rows = [
        ("Reviewer", reviewer),
        ("Items", f"{len(items)} questions" + ("" if len(items) == n_total else f" (a stratified random sample of the {n_total}, for inter-rater agreement)")),
        ("Purpose", "Judge each question on its own: is it clear, answerable from the source it names, clinically sound, and something a rare-disease or NTD trial or repurposing team would need answered?"),
        ("How", "Work down the Review sheet in the order given. Read the question. Open the source it names if you need to (ClinicalTrials.gov, Open Targets, ChEMBL, Drugs@FDA, Orphanet). Fill the five yellow cells. About 1 minute per item."),
        ("Independence", "Do this on your own. Do not discuss items with the other reviewer, and do not use an AI assistant or tool to rate, draft notes or check sources. If you used one for any item, say so in that item's note."),
        ("Not shown", "Question types and the gold answers are hidden on purpose, so each item is judged on its wording. Gold answers are checked separately."),
        ("1. Clear?", "Yes = a competent reader would understand exactly what is asked and what form the answer takes. No = ambiguous (say what is ambiguous)."),
        ("2. Answerable?", "Yes = the named source can settle it as of a given date. No = the source cannot settle it, or the answer depends on an unstated choice (say which). Unsure = you could not tell."),
        ("3. Clinically sound?", "Yes = the premise makes clinical and pharmacological sense. No = the premise is misleading or unsafe, e.g. it treats a drug that acts on a target as a candidate regardless of whether it activates or blocks it (say why). Unsure = outside your expertise."),
        ("4. Realism (1-5)", "How often would a trial team or repurposing scientist in rare diseases or NTDs need this answered? Use the anchors below."),
        ("5. Verdict", "Keep = use as written. Edit = useful but needs rewording; write the new wording in the note. Drop = remove (clarity, answerability or soundness fails and cannot be fixed by rewording)."),
        ("Note", "Required for Edit, Drop, and any No. Make it specific to this item. Leave blank for a plain Keep."),
        ("When done", "Fill in the attestation below, save, and send the file back to Mahta."),
    ]
    r = 3
    for k, v in rows:
        ins.cell(r, 1, k).font = BOLD
        c = ins.cell(r, 2, v)
        c.font, c.alignment = B, WRAP
        r += 1
    r += 1
    ins.cell(r, 1, "Realism anchors").font = BOLD
    for a, t in ANCHORS:
        r += 1
        ins.cell(r, 1, a).font = B
        c = ins.cell(r, 2, t)
        c.font, c.alignment = B, WRAP
    r += 2
    ins.cell(r, 1, "Example (format only)").font = BOLD
    for k, v in (("Clear?", "No"), ("Answerable?", "Yes"), ("Clinically sound?", "Yes"), ("Realism", "4"),
                 ("Verdict", "Edit"), ("Note", "'Sites' could mean facilities or countries; ask for 'facility locations listed'.")):
        r += 1
        ins.cell(r, 1, k).font = B
        c = ins.cell(r, 2, v)
        c.font = Font(name=F, size=10, italic=True, color="555555")
    r += 2
    ins.cell(r, 1, "Attestation").font = BOLD
    att = r
    for k in ("I rated every item myself, without AI assistance (Yes/No)", "Name", "Date finished"):
        r += 1
        ins.cell(r, 1, k).font = B
        ins.cell(r, 1).alignment = WRAP
        ins.cell(r, 2).fill = FIN
    dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True)
    ins.add_data_validation(dv)
    dv.add(f"B{att + 1}")
    r += 2
    last = len(items) + 1
    ins.cell(r, 1, "Progress").font = BOLD
    ins.cell(r, 2, f'=COUNTIFS(Review!H2:H{last},"<>",Review!G2:G{last},"<>")&" of {len(items)} rated; "&COUNTIFS(Review!H2:H{last},"Edit",Review!I2:I{last},"")+COUNTIFS(Review!H2:H{last},"Drop",Review!I2:I{last},"")&" Edit/Drop without a note"').font = B

    ws = wb.create_sheet("Review")
    cols = [("Code", 7), ("Question", 70), ("Expected answer format", 24), ("1. Clear?", 9), ("2. Answerable?", 11),
            ("3. Clinically sound?", 11), ("4. Realism (1-5)", 9), ("5. Verdict", 10), ("Note", 50)]
    for j, (c, w) in enumerate(cols, 1):
        x = ws.cell(1, j, c)
        x.font, x.fill, x.border, x.alignment = HDR, FH, BOX, Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[x.column_letter].width = w
    ws.row_dimensions[1].height = 32
    for i, it in enumerate(items, 2):
        for j, v in enumerate([it["code"], it["question"], it.get("answer_format") or "", None, None, None, None, None, None], 1):
            x = ws.cell(i, j, v)
            x.font, x.alignment, x.border = B, WRAP, BOX
            if j >= 4:
                x.fill = FIN
    for rng, f in ((f"D2:D{last}", '"Yes,No"'), (f"E2:E{last}", '"Yes,No,Unsure"'), (f"F2:F{last}", '"Yes,No,Unsure"'), (f"H2:H{last}", '"Keep,Edit,Drop"')):
        dv = DataValidation(type="list", formula1=f, allow_blank=True, showErrorMessage=True)
        ws.add_data_validation(dv)
        dv.add(rng)
    dv = DataValidation(type="whole", operator="between", formula1="1", formula2="5", allow_blank=True, showErrorMessage=True, error="1 to 5")
    ws.add_data_validation(dv)
    dv.add(f"G2:G{last}")
    ws.conditional_formatting.add(f"I2:I{last}", FormulaRule(
        formula=['AND($I2="",OR($H2="Edit",$H2="Drop",$D2="No",$E2="No",$F2="No"))'], fill=PatternFill("solid", fgColor="F8D3D3")))
    ws.freeze_panes = "C2"
    wb.active = 1


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    qs = load()
    rng = random.Random(20261107)
    order = qs[:]
    rng.shuffle(order)
    key = {}
    for i, q in enumerate(order, 1):
        key[f"R{i:03d}"] = q["id"]
        q["code"] = f"R{i:03d}"
    (ROOT / "eval/review/v3_key.json").write_text(json.dumps({"seed": 20261107, "key": key}, indent=0))
    by = defaultdict(list)
    for q in order:
        by[q["template"]].append(q)
    n_sub = 100
    sub = []
    for t, xs in sorted(by.items()):  # proportional allocation, at least 3 per template
        k = max(3, round(n_sub * len(xs) / len(qs)))
        sub += rng.sample(xs, min(k, len(xs)))
    sub = sorted(sub, key=lambda q: q["code"])[:n_sub] if len(sub) > n_sub else sorted(sub, key=lambda q: q["code"])
    (ROOT / "eval/review/v3_second_reviewer_subset.json").write_text(json.dumps(sorted(q["code"] for q in sub)))
    for who, ini, items in (("Mahta Haghighat Ghahfarokhi", "MHG", order), ("Amin Arshi", "AA", sub)):
        wb = Workbook()
        sheet(wb, who, ini, items, len(qs))
        wb.save(out / f"review_v3_{ini}.xlsx")
        print(ini, len(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
