"""Project 6, step 1: candidate cohort from ClinicalTrials.gov (deterministic, no LLM).

Pulls every interventional study first submitted on/after 2010-01-01, keeps those
whose conditions map to (a) an Orphanet rare disorder (EU definition) via MeSH
cross-references or exact name/synonym match, or (b) a WHO NTD via a MeSH-term
lexicon, and that test at least one DRUG intervention. Writes one JSONL row per
candidate with every structured field the protocol needs, plus the matching
evidence, so each inclusion decision is auditable.

LLM-assisted steps (condition confirmation, repurposing judgement, stop-reason and
funder classification) run later on this file; nothing here is model-dependent.

    python project6/pipeline/build_cohort.py --out project6/data/cohort_ctgov.jsonl.gz
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from biomcp.sources.orphanet import classify_rarity  # protocol §4.2 rarity rule

UA = {"User-Agent": "rare-trials-ai/project6 (+https://github.com/mahtahg/rare-trials-ai)"}
CTG = "https://clinicaltrials.gov/api/v2/studies"
ORPHA_XREF = "https://www.orphadata.com/data/xml/en_product1.xml"
ORPHA_PREV = "https://www.orphadata.com/data/xml/en_product9_prev.xml"

# WHO NTD groups -> case-insensitive patterns over condition text and MeSH terms (protocol §4.2; version-controlled)
NTD_LEXICON = {
    "Buruli ulcer": r"buruli|mycobacterium ulcerans",
    "Chagas disease": r"chagas|trypanosoma cruzi",
    "Dengue": r"\bdengue",
    "Dracunculiasis": r"dracuncul|guinea.worm",
    "Echinococcosis": r"echinococc|hydatid",
    "Foodborne trematodiases": r"fasciol|clonorch|opisthorch|paragonim",
    "Human African trypanosomiasis": r"african trypanosomiasis|sleeping sickness|trypanosoma brucei",
    "Leishmaniasis": r"leishmania|kala.azar",
    "Leprosy": r"lepros|leprosy|hansen'?s disease|mycobacterium leprae",
    "Lymphatic filariasis": r"lymphatic filariasis|wuchereria|brugia|elephantiasis, filarial",
    "Mycetoma, chromoblastomycosis and other deep mycoses": r"mycetoma|chromoblastomycosis|sporotrich|paracoccidioid|histoplasmosis",
    "Noma": r"\bnoma\b|cancrum oris",
    "Onchocerciasis": r"onchocerc|river blindness",
    "Rabies": r"\brabies",
    "Scabies and other ectoparasitoses": r"scabies|tungiasis",
    "Schistosomiasis": r"schistosom|bilharzi",
    "Soil-transmitted helminthiases": r"ascari|hookworm|ancylostom|necator|trichuri|strongyloid|soil.transmitted helminth",
    "Snakebite envenoming": r"snake ?bite|snake venom|envenom",
    "Taeniasis/cysticercosis": r"taenia|cysticerc",
    "Trachoma": r"trachoma",
    "Yaws": r"\byaws\b|treponema pertenue",
}
NTD_RE = {k: re.compile(v, re.IGNORECASE) for k, v in NTD_LEXICON.items()}

FIELDS = ",".join([  # noqa: FLY002
    "protocolSection.identificationModule", "protocolSection.statusModule", "protocolSection.sponsorCollaboratorsModule",
    "protocolSection.conditionsModule", "protocolSection.designModule", "protocolSection.armsInterventionsModule",
    "protocolSection.eligibilityModule", "protocolSection.contactsLocationsModule",
    "derivedSection.conditionBrowseModule", "derivedSection.interventionBrowseModule", "hasResults",
])


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def load_orphanet(c: httpx.Client) -> tuple[dict, dict, dict]:
    """-> (mesh_id -> [orpha], normalized name/synonym -> orpha, orpha -> info)."""
    info, mesh, names = {}, {}, {}
    r = c.get(ORPHA_XREF)
    r.raise_for_status()
    for _, el in ET.iterparse(io.BytesIO(r.content), events=("end",)):
        if el.tag != "Disorder":
            continue
        code = el.findtext("OrphaCode")
        grp = el.findtext("DisorderGroup/Name")
        nm = el.findtext("Name")
        info[code] = {"name": nm, "group": grp}
        for t in [nm] + [s.text for s in el.iterfind("SynonymList/Synonym")]:
            if t and len(norm(t)) > 4:
                names.setdefault(norm(t), code)
        for x in el.iterfind("ExternalReferenceList/ExternalReference"):
            if x.findtext("Source") == "MeSH" and x.findtext("DisorderMappingValidationStatus/Name") == "Validated":
                rel = (x.findtext("DisorderMappingRelation/Name") or "")[:4]
                if rel.startswith(("E ", "NTBT")):  # exact, or Orphanet narrower than MeSH (MeSH term covers it)
                    mesh.setdefault(x.findtext("Reference"), []).append((code, rel.strip()))
        el.clear()
    r = c.get(ORPHA_PREV)
    r.raise_for_status()
    for _, el in ET.iterparse(io.BytesIO(r.content), events=("end",)):
        if el.tag != "Disorder":
            continue
        code = el.findtext("OrphaCode")
        rows = [{"PrevalenceType": p.findtext("PrevalenceType/Name"), "PrevalenceClass": p.findtext("PrevalenceClass/Name"),
                 "PrevalenceGeographic": p.findtext("PrevalenceGeographic/Name"),
                 "PrevalenceValidationStatus": p.findtext("PrevalenceValidationStatus/Name")}
                for p in el.iterfind("PrevalenceList/Prevalence")]
        if code in info:
            info[code]["rarity"] = classify_rarity(rows)
        el.clear()
    for code, v in info.items():
        v.setdefault("rarity", classify_rarity([]))
    return mesh, names, info


def match(study: dict, mesh: dict, names: dict, info: dict) -> dict:
    ps = study.get("protocolSection", {})
    conds = (ps.get("conditionsModule") or {}).get("conditions", [])
    meshes = ((study.get("derivedSection") or {}).get("conditionBrowseModule") or {}).get("meshes", [])
    rare_hits, ntd_hits = [], []
    for m in meshes:
        for code, rel in mesh.get(m.get("id"), []):
            if rel.startswith("E") and info.get(code, {}).get("rarity", {}).get("rare_eu"):
                rare_hits.append({"orpha": code, "via": f"MeSH {m.get('id')} ({m.get('term')}) exact"})
    for cnd in conds:
        code = names.get(norm(cnd))
        if code and info.get(code, {}).get("rarity", {}).get("rare_eu"):
            rare_hits.append({"orpha": code, "via": f"condition text '{cnd}' = Orphanet name/synonym"})
    text = " | ".join(conds + [m.get("term", "") for m in meshes])
    for k, rx in NTD_RE.items():
        if rx.search(text):
            ntd_hits.append(k)
    # NTBT MeSH matches are recorded but flagged for LLM/human confirmation (MeSH term broader than the rare entity)
    broad = []
    for m in meshes:
        for code, rel in mesh.get(m.get("id"), []):
            if rel.startswith("NTBT") and info.get(code, {}).get("rarity", {}).get("rare_eu"):
                broad.append({"orpha": code, "via": f"MeSH {m.get('id')} ({m.get('term')}) broader"})
    seen = set()
    rare_hits = [h for h in rare_hits if not (h["orpha"] in seen or seen.add(h["orpha"]))]
    return {"rare": rare_hits, "rare_broad_only": broad[:5] if not rare_hits else [], "ntd": sorted(set(ntd_hits))}


def flatten(study: dict, m: dict) -> dict:
    ps = study.get("protocolSection", {})
    idm, sm, dm = ps.get("identificationModule", {}), ps.get("statusModule", {}), ps.get("designModule", {})
    sp = ps.get("sponsorCollaboratorsModule", {})
    locs = (ps.get("contactsLocationsModule") or {}).get("locations", [])
    em = ps.get("eligibilityModule", {})
    return {
        "registry": "ClinicalTrials.gov", "trial_id": idm.get("nctId"),
        "secondary_ids": [s.get("id") for s in idm.get("secondaryIdInfos", []) or []],
        "org_study_id": (idm.get("orgStudyIdInfo") or {}).get("id"),
        "title": idm.get("briefTitle"), "official_title": idm.get("officialTitle"),
        "overall_status": sm.get("overallStatus"), "last_known_status": sm.get("lastKnownStatus"), "why_stopped": sm.get("whyStopped"),
        "first_submitted": sm.get("studyFirstSubmitDate"), "start_date": (sm.get("startDateStruct") or {}).get("date"),
        "primary_completion_date": (sm.get("primaryCompletionDateStruct") or {}).get("date"),
        "primary_completion_type": (sm.get("primaryCompletionDateStruct") or {}).get("type"),
        "completion_date": (sm.get("completionDateStruct") or {}).get("date"),
        "last_update_posted": (sm.get("lastUpdatePostDateStruct") or {}).get("date"),
        "phases": dm.get("phases", []), "allocation": (dm.get("designInfo") or {}).get("allocation"),
        "masking": ((dm.get("designInfo") or {}).get("maskingInfo") or {}).get("masking"),
        "enrollment": (dm.get("enrollmentInfo") or {}).get("count"), "enrollment_type": (dm.get("enrollmentInfo") or {}).get("type"),
        "lead_sponsor": (sp.get("leadSponsor") or {}).get("name"), "lead_sponsor_class": (sp.get("leadSponsor") or {}).get("class"),
        "collaborators": [x.get("name") for x in sp.get("collaborators", []) or []],
        "conditions": (ps.get("conditionsModule") or {}).get("conditions", []),
        "condition_mesh": [x.get("term") for x in ((study.get("derivedSection") or {}).get("conditionBrowseModule") or {}).get("meshes", [])],
        "drugs": [i.get("name") for i in (ps.get("armsInterventionsModule") or {}).get("interventions", []) if i.get("type") == "DRUG"],
        "drug_other_names": sorted({o for i in (ps.get("armsInterventionsModule") or {}).get("interventions", []) if i.get("type") == "DRUG"
                                    for o in i.get("otherNames", []) or []}),
        "n_sites": len(locs), "countries": sorted({x.get("country") for x in locs if x.get("country")}),
        "min_age": em.get("minimumAge"), "max_age": em.get("maximumAge"), "has_results": study.get("hasResults", False),
        "match": m,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "project6/data/cohort_ctgov.jsonl.gz"))
    ap.add_argument("--from-date", default="2010-01-01")
    ap.add_argument("--max-pages", type=int, default=0)
    a = ap.parse_args()
    c = httpx.Client(headers=UA, timeout=120, follow_redirects=True)
    mesh, names, info = load_orphanet(c)
    print(f"orphanet: {len(info)} entities, {len(mesh)} MeSH keys, {len(names)} names", flush=True)
    ver = c.get("https://clinicaltrials.gov/api/v2/version").json()
    params = {"query.term": f"AREA[StudyType]INTERVENTIONAL AND AREA[StudyFirstSubmitDate]RANGE[{a.from_date},MAX]",
              "pageSize": 1000, "fields": FIELDS, "countTotal": "true"}
    token, page, scanned, kept = None, 0, 0, 0
    total = None
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out, "wt", encoding="utf-8") as f:
        while True:
            if token:
                params["pageToken"] = token
            for i in range(6):
                r = c.get(CTG, params=params)
                if r.status_code == 200:
                    break
                time.sleep(2 ** i)
            r.raise_for_status()
            b = r.json()
            total = total or b.get("totalCount")
            for st in b.get("studies", []):
                scanned += 1
                m = match(st, mesh, names, info)
                ps = st.get("protocolSection", {})
                has_drug = any(i.get("type") == "DRUG" for i in (ps.get("armsInterventionsModule") or {}).get("interventions", []))
                if has_drug and (m["rare"] or m["ntd"] or m["rare_broad_only"]):
                    rec = flatten(st, m)
                    for h in rec["match"]["rare"] + rec["match"]["rare_broad_only"]:
                        h["name"] = info[h["orpha"]]["name"]
                        h["rarity_basis"] = info[h["orpha"]]["rarity"]["basis"]
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    kept += 1
            page += 1
            print(f"page {page}: scanned {scanned}/{total}, candidates {kept}", flush=True)
            token = b.get("nextPageToken")
            if not token or (a.max_pages and page >= a.max_pages):
                break
            time.sleep(0.3)
    manifest = {"built_at": datetime.now(timezone.utc).isoformat(), "ctgov_version": ver, "from_date": a.from_date,
                "scanned": scanned, "total_reported": total, "candidates": kept, "ntd_lexicon": NTD_LEXICON,
                "orphanet_files": [ORPHA_XREF, ORPHA_PREV]}
    Path(str(out).replace(".jsonl.gz", ".manifest.json")).write_text(json.dumps(manifest, indent=1))
    print(json.dumps(manifest, indent=1)[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
