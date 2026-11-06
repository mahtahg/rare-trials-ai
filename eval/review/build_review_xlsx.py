"""Build the offline review spreadsheet (same fields as the web review form) from eval/review/review_items.json."""
import json

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

items = json.loads(__import__("pathlib").Path(__file__).with_name("review_items.json").read_text())
items.sort(key=lambda x: (x["_chunk"].startswith("h"), x["_chunk"], x.get("order", 0)))
LABELS = {"trial_why_stopped": "Why stopped", "trial_enrollment": "Enrolment", "trial_has_sap": "SAP uploaded", "trial_n_sites": "Site count",
  "trial_count": "Trial counts", "disease_top_targets": "Top targets", "disease_late_stage_drugs": "Late-stage drugs",
  "disease_rarity": "EU rarity", "drug_generic_us": "US generic", "drug_first_approval": "First approval", "drug_targets": "Drug targets",
  "multihop_generic_late_stage": "Repurposing (multi-hop)", "not_found": "Non-existent entity",
  "h_recruitment_footprint": "Hard: Recruitment footprint", "h_late_generic_boxed": "Hard: Generic + boxed warning",
  "h_eligibility_check": "Hard: Eligibility", "h_source_conflict": "Hard: Source conflict", "h_untested_target_drugs": "Hard: Untested target drugs"}

F = "Arial"
base = Font(name=F, size=10); bold = Font(name=F, size=10, bold=True); hdr = Font(name=F, size=10, bold=True, color="FFFFFF")
title = Font(name=F, size=14, bold=True)
HFILL = PatternFill("solid", fgColor="1F3A5F"); INFILL = PatternFill("solid", fgColor="FFF4C2"); GOLD = PatternFill("solid", fgColor="E8F0FA")
GREY = PatternFill("solid", fgColor="EEEEEE")
thin = Side(style="thin", color="CCCCCC"); box = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical="top")

wb = Workbook()
ins = wb.active; ins.title = "Instructions"
q = wb.create_sheet("Questions")

cols = ["#", "Question ID", "Tier", "Type", "Population", "Question", "Expected answer format", "Gold check?",
        "Gold answer", "Source", "Verdict", "Realism (1-5)", "Gold correct?", "Edited wording / notes"]
widths = [5, 24, 6, 22, 9, 70, 22, 8, 28, 40, 10, 9, 10, 45]
for i, (c, w) in enumerate(zip(cols, widths), 1):
    cell = q.cell(1, i, c); cell.font = hdr; cell.fill = HFILL; cell.alignment = Alignment(wrap_text=True, vertical="center"); cell.border = box
    q.column_dimensions[get_column_letter(i)].width = w
q.row_dimensions[1].height = 30
for r, x in enumerate(items, 2):
    spot = bool(x.get("spot_check"))
    vals = [r - 1, x["id"], "Hard" if x["_chunk"].startswith("h") else "Base", LABELS.get(x["template"], x["template"]),
            x.get("population", "rare"), x["question"], x.get("answer_format") or "", "Yes" if spot else "",
            x.get("gold_display") if spot else "", "\n".join(x.get("gold_sources") or []) if spot else "", None, None, None, None]
    for c, v in enumerate(vals, 1):
        cell = q.cell(r, c, v); cell.font = base; cell.alignment = wrap; cell.border = box
    for c in (11, 12, 14):
        q.cell(r, c).fill = INFILL
    q.cell(r, 13).fill = INFILL if spot else GREY
    if spot:
        for c in (8, 9, 10):
            q.cell(r, c).fill = GOLD
        q.cell(r, 8).font = bold
last = len(items) + 1
q.freeze_panes = "G2"
q.auto_filter.ref = f"A1:N{last}"

dv_v = DataValidation(type="list", formula1='"Keep,Edit,Drop"', allow_blank=True, showErrorMessage=True,
                      errorTitle="Verdict", error="Choose Keep, Edit or Drop.")
dv_r = DataValidation(type="whole", operator="between", formula1="1", formula2="5", allow_blank=True, showErrorMessage=True,
                      errorTitle="Realism", error="Enter a whole number from 1 to 5.")
dv_g = DataValidation(type="list", formula1='"Yes,No,Unsure"', allow_blank=True, showErrorMessage=True,
                      errorTitle="Gold correct?", error="Choose Yes, No or Unsure.")
for dv, col in ((dv_v, "K"), (dv_r, "L"), (dv_g, "M")):
    q.add_data_validation(dv); dv.add(f"{col}2:{col}{last}")
for v, color in (("Keep", "D6F0DC"), ("Edit", "FCE8C8"), ("Drop", "F8D3D3")):
    q.conditional_formatting.add(f"K2:K{last}", FormulaRule(formula=[f'$K2="{v}"'], fill=PatternFill("solid", fgColor=color)))
# flag Edit/Drop without a note
q.conditional_formatting.add(f"N2:N{last}", FormulaRule(formula=['AND(OR($K2="Edit",$K2="Drop"),$N2="")'],
                             fill=PatternFill("solid", fgColor="F8D3D3")))

# Instructions sheet
ins.column_dimensions["A"].width = 30; ins.column_dimensions["B"].width = 95
ins["A1"] = "RareMCP eval: question review"; ins["A1"].font = title
rows = [
 ("Who", "Mahta Haghighat Ghahfarokhi (domain review of the eval question set)."),
 ("What", f"{len(items)} questions: 254 base tier + 60 hard tier. 41 are gold checks (shaded blue)."),
 ("Fill in", "Only the yellow cells on the Questions sheet: Verdict, Realism, Gold correct? (gold-check rows only) and Notes."),
 ("Verdict", "Keep = use as is. Edit = useful but badly phrased; write the better wording in Notes. Drop = ambiguous, unanswerable or wrong; say why in Notes."),
 ("Realism (1-5)", "Would a trial team or repurposing scientist working on a rare or neglected disease plausibly need this answered? 5 = routine need, 1 = contrived."),
 ("Gold correct?", "Gold-check rows only: open the Source link and confirm the Gold answer. Yes / No / Unsure. If No, write the correct answer in Notes."),
 ("Blinding", "Gold answers are shown only for the 41 gold-check rows, as in the web form. Rate the others on the question alone."),
 ("Tips", "Filter on column D (Type) to rate one question type at a time. Notes turn red if you chose Edit/Drop but left them empty."),
 ("When done", "Send the file back in this chat. It is imported into eval/review/ratings.jsonl; dropped questions go into eval/excluded_questions.json and are excluded from scoring."),
]
for i, (a, b) in enumerate(rows, 3):
    ins.cell(i, 1, a).font = bold; c = ins.cell(i, 2, b); c.font = base; c.alignment = wrap
r0 = 3 + len(rows) + 1
ins.cell(r0, 1, "Example row (format only)").font = bold
ex = [("Verdict", "Edit"), ("Realism (1-5)", "4"), ("Gold correct?", "Yes"),
      ("Edited wording / notes", "Ask for 'participating countries' rather than 'countries with sites' so it matches registry wording.")]
for j, (a, b) in enumerate(ex, r0 + 1):
    ins.cell(j, 1, a).font = base; c = ins.cell(j, 2, b); c.font = Font(name=F, size=10, italic=True, color="555555"); c.alignment = wrap
p0 = r0 + len(ex) + 2
ins.cell(p0, 1, "Progress (updates as you fill in)").font = bold
prog = [
 ("Rated (verdict + realism)", f'=COUNTIFS(Questions!K2:K{last},"<>",Questions!L2:L{last},"<>")'),
 ("Total questions", f"=COUNTA(Questions!B2:B{last})"),
 ("Keep", f'=COUNTIF(Questions!K2:K{last},"Keep")'),
 ("Edit", f'=COUNTIF(Questions!K2:K{last},"Edit")'),
 ("Drop", f'=COUNTIF(Questions!K2:K{last},"Drop")'),
 ("Gold checks done", f'=COUNTIFS(Questions!H2:H{last},"Yes",Questions!M2:M{last},"<>")'),
 ("Gold checks total", f'=COUNTIF(Questions!H2:H{last},"Yes")'),
 ("Gold answers marked wrong", f'=COUNTIF(Questions!M2:M{last},"No")'),
 ("Mean realism", f'=IFERROR(AVERAGE(Questions!L2:L{last}),"-")'),
]
for j, (a, f) in enumerate(prog, p0 + 1):
    ins.cell(j, 1, a).font = base; c = ins.cell(j, 2, f); c.font = bold; c.alignment = Alignment(horizontal="left")
ins.cell(p0 + len(prog), 2).number_format = "0.00"
wb.active = 1
wb.save(__import__("sys").argv[1] if len(__import__("sys").argv) > 1 else "biomcp_question_review.xlsx")
print(last - 1, "rows")
