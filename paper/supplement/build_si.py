"""Build the Supplementary Information as one merged PDF (npj Digital Medicine requirement).

Takes eval/results/SUPPLEMENT.md (Supplementary Tables 1-5, generated from saved results) and
paper/supplement/tripod_llm.md (Supplementary Note 1), renames internal template ids to the names used in
the paper, adds a title page and table legends, and renders A4 PDF with Arial (or metrically identical
Liberation Sans), all text black.

    python paper/supplement/build_si.py   ->   paper/supplement/Supplementary_Information.pdf (+ .html)
"""

from __future__ import annotations

import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/supplement"
TITLE = ("Open source-grounded tools for language models answering clinical-development questions "
         "in rare and neglected tropical diseases")

NAMES = {
    "trial_why_stopped": "Why a trial stopped", "trial_enrollment": "Enrolment (count and actual/estimated)",
    "trial_has_sap": "Statistical analysis plan uploaded", "trial_n_sites": "Number of sites",
    "trial_count": "Terminated or withdrawn trial count", "disease_top_targets": "Top five associated targets",
    "disease_late_stage_drugs": "Drugs at phase 3 or later", "disease_rarity": "EU rarity (10 rare, 10 not)",
    "drug_generic_us": "Marketed US generic", "drug_first_approval": "First approval year", "drug_targets": "Drug targets",
    "multihop_generic_late_stage": "Late-stage drugs with a US generic", "not_found": "Non-existent identifier",
    "h_recruitment_footprint": "Countries recruiting for a disease", "h_late_generic_boxed": "Late-stage, generic and boxed warning",
    "h_eligibility_check": "Age and sex eligibility at a boundary", "h_source_conflict": "ChEMBL versus FDA first-approval year",
    "h_untested_target_drugs": "Approved drugs on the top target not yet tested in the disease",
}
LEGENDS = {
    1: "Percentage of questions answered correctly by Claude Sonnet 5.5 / Claude Haiku 5.5 (S/H) against the audited gold "
       "answers (v1.1), one run per question, model and condition. RareMCP 0.1.1 is the post hoc re-run of the "
       "Drugs@FDA-dependent templates; – marks a template that was not re-run, whose answers are unchanged from RareMCP 0.1.0.",
    2: "Accuracy of each condition scored against the original gold answers (v1.0) and against the audited gold answers "
       "(v1.1), which correct eight Drugs@FDA-dependent answers (Supplementary Table 4; Methods, Gold audit and correction).",
    3: "Exploratory. Percentage correct for Claude Sonnet 5.5 / Claude Haiku 5.5 against gold v1.1, with RareMCP 0.1.0. "
       "NTD questions come only from aggregate templates, so the second row restricts rare-disease questions to the same templates.",
    4: "Rule for v1.1: Drugs@FDA applications are the union of searches on openfda.generic_name and "
       "products.active_ingredients.name, de-duplicated by application number. Evidence is summarised from the archived "
       "Drugs@FDA payloads in the code repository (eval/review/gold_v1_1). ANDA, abbreviated new drug application; NDA, new drug application.",
    5: "Excerpts from no-tools answers by Claude Haiku 5.5 that describe tool calls and their results although the run made "
       "no tool calls (7 of 314 answers). Identified by a regular-expression screen and confirmed by reading each answer; "
       "ellipses mark truncation and [?] an undecodable character in the logged output. Run and question identifiers refer to the raw logs in the code repository.",
}

CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { color: #000; }
body { font-family: Arial, Helvetica, 'Liberation Sans', sans-serif; font-size: 9pt; line-height: 1.35; }
h1 { font-size: 14pt; margin: 0 0 6mm; } h2 { font-size: 11pt; margin: 9mm 0 2mm; break-after: avoid; }
h3 { font-size: 10pt; margin: 6mm 0 2mm; break-after: avoid; }
p { margin: 0 0 2.5mm; } .legend { font-size: 8.5pt; margin-top: 1.5mm; }
table { border-collapse: collapse; width: 100%; font-size: 8pt; margin: 1mm 0 1mm; }
th, td { text-align: left; vertical-align: top; padding: 1.2mm 1.6mm; border: none; }
thead th { border-top: 0.8pt solid #000; border-bottom: 0.5pt solid #000; font-weight: bold; }
tbody tr:last-child td { border-bottom: 0.8pt solid #000; }
tr { break-inside: avoid; } ul { padding-left: 5mm; } li { margin-bottom: 2mm; }
code { font-family: inherit; } .title { break-after: page; } .contents li { margin-bottom: 1mm; }
"""


def main() -> int:
    sup = (ROOT / "eval/results/SUPPLEMENT.md").read_text()
    sup = sup.split("\n", 3)[3] if sup.startswith("# ") else sup  # drop generator header
    for k, v in sorted(NAMES.items(), key=lambda kv: -len(kv[0])):
        sup = re.sub(rf"\| {k} \|", f"| {v} |", sup)
    sup = sup.replace("\ufffd", "[?]")  # undecodable bytes in the logged model output
    sup = re.sub(r"\| base \|", "| Base |", sup)
    sup = re.sub(r"\| hard \|", "| Hard |", sup)
    sup = sup.replace("NTD questions come only from aggregate templates; the 'NTD templates only' row restricts rare-disease questions to those templates.\n", "")
    sup = re.sub(r"^Rule: .*\n", "", sup, flags=re.M)
    parts = re.split(r"(?m)^## (Supplementary Table (\d)\..*)$", sup)
    body = []
    for i in range(1, len(parts), 3):
        head, n, content = parts[i], int(parts[i + 1]), parts[i + 2].strip()
        body.append(f"## {head}\n\n{content}\n\n<p class='legend'>{LEGENDS[n]}</p>\n")
    tripod = (ROOT / "paper/supplement/tripod_llm.md").read_text()
    contents = ("<ul class='contents'>" + "".join(f"<li>{re.sub(r'^## ', '', b.splitlines()[0]).split('. ')[0]}. "
                f"{re.sub(r'^## Supplementary Table \d\. ', '', b.splitlines()[0])}</li>" for b in body)
                + "<li>Supplementary Note 1. TRIPOD-LLM checklist</li></ul>")
    md = "\n".join(body) + "\n" + tripod
    html = markdown.markdown(md, extensions=["tables"])
    doc = (f"<!doctype html><html><head><meta charset='utf-8'><title>Supplementary Information</title><style>{CSS}</style></head><body>"
           f"<div class='title'><h1>Supplementary Information</h1><p><b>{TITLE}</b></p>"
           f"<p>Mahta Haghighat Ghahfarokhi and Amin Arshi, King's College London, London, UK</p>"
           f"<h3>Contents</h3>{contents}</div>{html}</body></html>")
    (OUT / "Supplementary_Information.html").write_text(doc)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(doc, wait_until="load")
        pg.pdf(path=str(OUT / "Supplementary_Information.pdf"), format="A4", print_background=True,
               display_header_footer=True, header_template="<span></span>",
               footer_template="<div style='width:100%;text-align:center;font-family:Arial,Helvetica,Liberation Sans,sans-serif;font-size:8pt;color:#000'><span class='pageNumber'></span></div>",
               margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"})
        b.close()
    print(f"wrote {OUT / 'Supplementary_Information.pdf'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
