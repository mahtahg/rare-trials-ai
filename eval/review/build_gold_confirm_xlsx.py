"""Workbook for human confirmation of the 41 gold answers against archived primary-source extracts (gold_audit.jsonl)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[2]
rows = [json.loads(x) for x in (ROOT / "eval/review/gold_audit.jsonl").read_text().splitlines() if x.strip()]
_gc = ROOT / "eval/gold_corrections_v1_1.json"
CORR = json.loads(_gc.read_text())["corrections"] if _gc.exists() else {}
for _r in rows:  # show the current (v1.1) gold and its evidence for corrected items
    if _r["id"] in CORR:
        c = CORR[_r["id"]]
        _r["evidence"] = f"[Gold corrected in v1.1; v1 gold was {json.dumps(c['old'])}] " + c["evidence"]
        _r["gold"] = c["new"]
F = "Arial"
b, h, t = Font(name=F, size=10), Font(name=F, size=10, bold=True, color="FFFFFF"), Font(name=F, size=13, bold=True)
fill_h, fill_in = PatternFill("solid", fgColor="1F3A5F"), PatternFill("solid", fgColor="FFF4C2")
thin = Side(style="thin", color="CCCCCC")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical="top")

wb = Workbook()
ins = wb.active
ins.title = "Instructions"
ins.column_dimensions["A"].width = 24
ins.column_dimensions["B"].width = 100
ins["A1"] = "Gold-answer confirmation (41 items)"
ins["A1"].font = t
for i, (k, v) in enumerate([
    ("What", "Each row shows the gold answer and the relevant field(s) copied from the primary record, re-fetched and archived on the audit date."),
    ("Your job", ("Read the question, the gold answer and the primary-record extract. If the extract supports the gold, choose Yes; if not, No and say why. "
                  "Open the source link if the extract is unclear. Unsure only if the extract and the live record both fail to settle it.")),
    ("Fill in", "Yellow cells only: Confirmed?, Reviewer initials, Note."),
    ("Machine check", "An automatic re-derivation by separate code matched all 41 v1 gold answers, but used the same Drugs@FDA search as the gold. A broader search then found one of these 41 wrong (now corrected, marked below). Machine checks are not human verification; this sheet is."),
    ("Example", "Confirmed? = Yes; Initials = MHG; Note = (blank unless No/Unsure)"),
    ("Corrected items", "Rows marked [Gold corrected in v1.1] had a wrong v1 gold, found by this audit: the original Drugs@FDA search missed older applications. Confirm the corrected answer against the source link."),
    ("Independence", "Check each row yourself against the source link or the archived extract. Do not use an AI assistant to decide. Sign the attestation below when done."),
], 3):
    ins.cell(i, 1, k).font = Font(name=F, size=10, bold=True)
    c = ins.cell(i, 2, v)
    c.font, c.alignment = b, wrap

ws = wb.create_sheet("Confirm")
cols = [("Question ID", 22), ("Type", 20), ("Question", 60), ("Gold answer", 28), ("Primary-record extract (archived)", 70),
        ("Source link", 40), ("Gold created", 12), ("Audited", 12), ("Machine match", 9), ("Confirmed?", 11), ("Reviewer initials", 10), ("Note", 40)]
for j, (c, w) in enumerate(cols, 1):
    x = ws.cell(1, j, c)
    x.font, x.fill, x.alignment, x.border = h, fill_h, Alignment(wrap_text=True, vertical="center"), box
    ws.column_dimensions[x.column_letter].width = w
for i, r in enumerate(rows, 2):
    g = r["gold"]
    gd = "does not exist" if g is None else (", ".join(g) if isinstance(g, list) else json.dumps(g) if isinstance(g, dict) else str(g))
    vals = [r["id"], r["template"], r["question"], gd or "(empty list)", r["evidence"], (r["primary_sources"] or [""])[0],
            (r["gold_retrieved_at"] or "")[:10], r["audited_at"][:10], "Yes" if r["auto_match"] else "No", None, None, None]
    for j, v in enumerate(vals, 1):
        x = ws.cell(i, j, v)
        x.font, x.alignment, x.border = b, wrap, box
    for j in (10, 11, 12):
        ws.cell(i, j).fill = fill_in
last = len(rows) + 1
dv = DataValidation(type="list", formula1='"Yes,No,Unsure"', allow_blank=True)
ws.add_data_validation(dv)
dv.add(f"J2:J{last}")
ws.freeze_panes = "D2"
ws.auto_filter.ref = f"A1:L{last}"
for _i, _k in enumerate(("I checked every row myself, without AI assistance (Yes/No)", "Name", "Date finished"), 13):
    ins.cell(_i, 1, _k).font = b
    ins.cell(_i, 1).alignment = wrap
    ins.cell(_i, 2).fill = fill_in
ins.cell(12, 1, "Attestation").font = Font(name=F, size=10, bold=True)
ins.cell(10, 1, "Confirmed so far").font = Font(name=F, size=10, bold=True)
ins.cell(10, 2, f'=COUNTIF(Confirm!J2:J{last},"Yes")&" yes / "&COUNTIF(Confirm!J2:J{last},"No")&" no / "&COUNTIF(Confirm!J2:J{last},"Unsure")&" unsure of {len(rows)}"').font = b
wb.active = 1
wb.save(sys.argv[1] if len(sys.argv) > 1 else "gold_confirm.xlsx")
print(len(rows), "rows")
