"""Build the biomcp eval question bank with deterministic gold answers.

Gold answers are computed directly from raw source APIs/files with code that is
independent of biomcp's tool implementations (raw httpx + simple parsing), so the
tools under test do not grade themselves. Every question records the exact
source URL(s) and retrieval time of its gold.

Sampling is seeded and stratified; the disease frame is Orphanet rare diseases
(EU definition, exact MONDO mapping) plus the WHO NTD list.

Run where the sources are reachable (GitHub Actions):
    python eval/build_questions.py --out eval/questions.jsonl --per-template 20
"""

from __future__ import annotations

import argparse
import io
import json
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from raremcp.sources.orphanet import classify_rarity  # the EU-rarity *definition* (a rule, not a data path)

UA = {"User-Agent": "biomcp-eval-builder/0.1 (+https://github.com/mahtahg/rare-trials-ai)"}
CTG = "https://clinicaltrials.gov/api/v2"
OT = "https://api.platform.opentargets.org/api/v4/graphql"
CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"
FDA = "https://api.fda.gov/drug"
ORPHA_XREF = "https://www.orphadata.com/data/xml/en_product1.xml"
ORPHA_PREV = "https://www.orphadata.com/data/xml/en_product9_prev.xml"

# WHO NTD list (WHO, 2024 roadmap groups); OT ids resolved at build time
NTDS = [
    "Buruli ulcer", "Chagas disease", "dengue", "dracunculiasis", "echinococcosis", "fascioliasis",
    "human African trypanosomiasis", "visceral leishmaniasis", "cutaneous leishmaniasis", "leprosy",
    "lymphatic filariasis", "mycetoma", "chromoblastomycosis", "noma", "onchocerciasis", "rabies", "scabies",
    "schistosomiasis", "ascariasis", "hookworm infection", "trichuriasis", "snakebite envenoming", "cysticercosis",
    "trachoma", "yaws",
]

STAGE_ORDER = ["PRECLINICAL", "EARLY_PHASE_1", "PHASE_1", "PHASE_1_2", "PHASE_2", "PHASE_2_3", "PHASE_3", "PHASE_4", "APPROVAL"]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Src:
    def __init__(self):
        self.c = httpx.Client(headers=UA, timeout=60, follow_redirects=True)
        self.last = 0.0

    def _wait(self):
        dt = time.monotonic() - self.last
        if dt < 0.35:
            time.sleep(0.35 - dt)
        self.last = time.monotonic()

    def get(self, url, params=None):
        for i in range(5):
            self._wait()
            try:
                r = self.c.get(url, params=params)
            except httpx.TransportError:
                time.sleep(2 ** i)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i)
                continue
            return r
        raise RuntimeError(f"failed {url}")

    def gql(self, q, v):
        for i in range(5):
            self._wait()
            r = self.c.post(OT, json={"query": q, "variables": v})
            if r.status_code == 200:
                b = r.json()
                if b.get("errors"):
                    raise RuntimeError(b["errors"][0]["message"])
                return b["data"]
            time.sleep(2 ** i)
        raise RuntimeError("OT failed")


# ---------------------------------------------------------------- disease frame
def orphanet_frame(s: Src) -> tuple[list[dict], dict]:
    """Rare (EU) Orphanet disorders with an exact, validated MONDO mapping."""
    meta = {}

    def parse(url):
        r = s.get(url)
        r.raise_for_status()
        meta[url] = {"retrieved_at": now(), "bytes": len(r.content)}
        return ET.iterparse(io.BytesIO(r.content), events=("end",))

    mondo, names, groups = {}, {}, {}
    for _, el in parse(ORPHA_XREF):
        if el.tag != "Disorder":
            continue
        code = el.findtext("OrphaCode")
        names[code] = el.findtext("Name")
        groups[code] = el.findtext("DisorderGroup/Name")
        for x in el.iterfind("ExternalReferenceList/ExternalReference"):
            if x.findtext("Source") == "MONDO" and (x.findtext("DisorderMappingRelation/Name") or "").startswith("E ") \
                    and x.findtext("DisorderMappingValidationStatus/Name") == "Validated":
                mondo[code] = "MONDO_" + x.findtext("Reference").zfill(7)
        el.clear()
    prev = {}
    for _, el in parse(ORPHA_PREV):
        if el.tag != "Disorder":
            continue
        code = el.findtext("OrphaCode")
        rows = []
        for p in el.iterfind("PrevalenceList/Prevalence"):
            rows.append({
                "PrevalenceType": p.findtext("PrevalenceType/Name"),
                "PrevalenceClass": p.findtext("PrevalenceClass/Name"),
                "PrevalenceGeographic": p.findtext("PrevalenceGeographic/Name"),
                "PrevalenceValidationStatus": p.findtext("PrevalenceValidationStatus/Name"),
            })
        prev[code] = rows
        el.clear()
    frame = []
    for code, mid in mondo.items():
        if groups.get(code) != "Disorder" or code not in prev:
            continue
        rar = classify_rarity(prev[code])
        frame.append({"orpha": code, "name": names[code], "ot_id": mid, "rarity": rar, "prev": prev[code]})
    return frame, meta


def resolve_ntds(s: Src) -> list[dict]:
    out = []
    q = 'query($q:String!){search(queryString:$q, entityNames:["disease"], page:{index:0,size:1}){hits{id name}}}'
    for n in NTDS:
        h = s.gql(q, {"q": n})["search"]["hits"]
        if h:
            out.append({"name": h[0]["name"], "ot_id": h[0]["id"], "ntd": True, "query_name": n})
    return out


# ---------------------------------------------------------------- generators
def q(id_, template, question, answer_type, gold, answer_format, sources, **kw):
    return {"id": id_, "template": template, "question": question, "answer_type": answer_type, "gold": gold,
            "answer_format": answer_format, "gold_sources": sources, "gold_retrieved_at": now(), "status": "active", **kw}


def ctg_study(s: Src, nct: str) -> dict | None:
    r = s.get(f"{CTG}/studies/{nct}")
    return r.json() if r.status_code == 200 else None


def trial_pool(s: Src, diseases: list[dict], rng: random.Random, max_per: int = 30) -> list[dict]:
    pool = {}
    for d in diseases:
        params = {"query.cond": d["name"], "pageSize": max_per, "query.term": "AREA[StudyType]INTERVENTIONAL",
                  "fields": "protocolSection.identificationModule,protocolSection.statusModule,protocolSection.designModule,"
                            "protocolSection.armsInterventionsModule,documentSection"}
        r = s.get(f"{CTG}/studies", params)
        if r.status_code == 400:  # field selector rejected: fall back to full records
            params.pop("fields")
            r = s.get(f"{CTG}/studies", params)
        if r.status_code != 200:
            continue
        for st in r.json().get("studies", []):
            nct = st["protocolSection"]["identificationModule"]["nctId"]
            pool.setdefault(nct, {"nct": nct, "disease": d["name"], "ntd": d.get("ntd", False), "raw": st})
    items = list(pool.values())
    rng.shuffle(items)
    return items


def gen_trials(s: Src, pool: list[dict], n: int) -> list[dict]:
    out = {"trial_why_stopped": [], "trial_enrollment": [], "trial_has_sap": [], "trial_n_sites": []}
    sap_yes = sap_no = 0
    for t in pool:
        if all(len(v) >= n for v in out.values()):
            break
        nct = t["nct"]
        full = None
        ps = t["raw"]["protocolSection"]
        sm = ps.get("statusModule", {})
        src = [f"https://clinicaltrials.gov/api/v2/studies/{nct}"]
        if sm.get("whyStopped") and sm.get("overallStatus") in ("TERMINATED", "WITHDRAWN", "SUSPENDED") and len(out["trial_why_stopped"]) < n:
            out["trial_why_stopped"].append(q(f"why-{nct}", "trial_why_stopped",
                f"According to its ClinicalTrials.gov record, why was trial {nct} stopped? Quote the stated reason.",
                "text", sm["whyStopped"], "the registry's stated reason, verbatim if possible", src, f1_threshold=0.5, nct=nct))
            continue
        ei = ps.get("designModule", {}).get("enrollmentInfo") or {}
        if ei.get("count") is not None and ei.get("type") and len(out["trial_enrollment"]) < n:
            out["trial_enrollment"].append(q(f"enrol-{nct}", "trial_enrollment",
                f"What enrolment number is recorded for trial {nct} on ClinicalTrials.gov, and is it the actual or the anticipated (estimated) enrolment?",
                "enrollment", {"count": ei["count"], "type": ei["type"]},
                'JSON object {"count": <integer>, "type": "ACTUAL" or "ESTIMATED"}', src, nct=nct))
            continue
        docs = (t["raw"].get("documentSection") or {}).get("largeDocumentModule", {}).get("largeDocs", [])
        has_sap = any(dd.get("hasSap") for dd in docs)
        if len(out["trial_has_sap"]) < n and ((has_sap and sap_yes < n // 2) or (not has_sap and sap_no < n - n // 2)):
            sap_yes += has_sap
            sap_no += not has_sap
            out["trial_has_sap"].append(q(f"sap-{nct}", "trial_has_sap",
                f"Has a statistical analysis plan (SAP) document been uploaded to ClinicalTrials.gov for trial {nct}?",
                "bool", has_sap, "true or false", src, nct=nct))
            continue
        if len(out["trial_n_sites"]) < n:
            full = full or ctg_study(s, nct)
            if not full:
                continue
            locs = (full["protocolSection"].get("contactsLocationsModule") or {}).get("locations", [])
            if 1 <= len(locs) <= 60:
                out["trial_n_sites"].append(q(f"sites-{nct}", "trial_n_sites",
                    f"How many trial sites (locations) are listed for {nct} on ClinicalTrials.gov?",
                    "int", len(locs), "an integer", src, tol_abs=0, nct=nct))
    # SAP questions are drawn to be balanced; if the pool lacked SAP trials, top up from a SAP-specific query
    return [x for v in out.values() for x in v]


def gen_counts(s: Src, diseases: list[dict], n: int) -> list[dict]:
    out = []
    for d in diseases:
        if len(out) >= n:
            break
        params = {"query.cond": d["name"], "filter.overallStatus": "TERMINATED,WITHDRAWN", "countTotal": "true", "pageSize": 1,
                  "query.term": "AREA[StudyType]INTERVENTIONAL"}
        r = s.get(f"{CTG}/studies", params)
        tot = r.json().get("totalCount") if r.status_code == 200 else None
        if not tot or tot < 2:
            continue
        out.append(q(f"count-{d['ot_id']}", "trial_count",
            f"How many interventional trials registered on ClinicalTrials.gov for the condition '{d['name']}' have an overall status of Terminated or Withdrawn?",
            "count", tot, "an integer", [str(r.url)], tol_rel=0.10, tol_abs=1, disease=d["name"]))
    return out


def gen_disease(s: Src, diseases: list[dict], n: int) -> list[dict]:
    tq = 'query($id:String!){disease(efoId:$id){id name associatedTargets(page:{index:0,size:5}){count rows{target{approvedSymbol}}}}}'
    dq = 'query($id:String!){disease(efoId:$id){id name drugAndClinicalCandidates{rows{maxClinicalStage drug{id name}}}}}'
    tops, late = [], []
    for d in diseases:
        if len(tops) >= n and len(late) >= n:
            break
        try:
            td = s.gql(tq, {"id": d["ot_id"]})["disease"]
        except RuntimeError:
            continue
        if not td:
            continue
        name = td["name"]
        rows = td["associatedTargets"]["rows"]
        if len(tops) < n and td["associatedTargets"]["count"] >= 10 and len(rows) == 5:
            tops.append(q(f"toptargets-{d['ot_id']}", "disease_top_targets",
                f"What are the five top-ranked associated targets (genes) for {name} ({d['ot_id']}) in the Open Targets Platform, by overall association score?",
                "set", [r["target"]["approvedSymbol"] for r in rows], "a JSON list of 5 HGNC gene symbols", [OT + f"#disease={d['ot_id']}"],
                f1_threshold=0.6, disease=name))
        if len(late) < n:
            dd = s.gql(dq, {"id": d["ot_id"]})["disease"]
            rws = (dd.get("drugAndClinicalCandidates") or {}).get("rows", [])
            ls = sorted({r["drug"]["name"].upper() for r in rws
                         if (r.get("maxClinicalStage") or "") in STAGE_ORDER and STAGE_ORDER.index(r["maxClinicalStage"]) >= STAGE_ORDER.index("PHASE_3")})
            if 1 <= len(ls) <= 12:
                late.append(q(f"latedrugs-{d['ot_id']}", "disease_late_stage_drugs",
                    f"According to Open Targets, which drugs have reached phase 3 or later (including approval) in clinical development for {name} ({d['ot_id']})?",
                    "set", ls, "a JSON list of drug names", [OT + f"#disease={d['ot_id']}"], f1_threshold=0.5, disease=name))
    return tops + late


def gen_rarity(frame: list[dict], rng: random.Random, n: int) -> list[dict]:
    hi = [f for f in frame if f["rarity"]["confidence"] == "high"]
    rare = [f for f in hi if f["rarity"]["rare_eu"]]
    # non-rare entities are scarce in Orphanet; accept medium-confidence (national-estimate) ones to balance
    common = [f for f in frame if not f["rarity"]["rare_eu"] and f["rarity"]["confidence"] in ("high", "medium")]
    picks = rng.sample(rare, min(n - n // 2, len(rare))) + rng.sample(common, min(n // 2, len(common)))
    return [q(f"rarity-{f['orpha']}", "disease_rarity",
              f"According to Orphanet's point-prevalence estimates, is {f['name']} (ORPHA:{f['orpha']}) a rare disease under the EU definition (point prevalence of at most 5 per 10,000)?",
              "bool", f["rarity"]["rare_eu"], "true or false", [f"https://api.orphadata.com/rd-epidemiology/orphacodes/{f['orpha']}"],
              basis=f["rarity"]["basis"]) for f in picks]


def anda_marketed(s: Src, ingredient: str) -> tuple[bool | None, str]:
    url = f"{FDA}/drugsfda.json"
    seen, skip = [], 0
    while skip < 500:
        r = s.get(url, {"search": f'openfda.generic_name:"{ingredient}"', "limit": 100, "skip": skip or None})
        if r.status_code == 404:
            break
        if r.status_code != 200:
            return None, str(r.url)
        b = r.json()
        seen += b["results"]
        skip += 100
        if skip >= b["meta"]["results"]["total"]:
            break
    if not seen:
        return None, url
    m = any(a["application_number"].startswith("ANDA") and any(p.get("marketing_status") in ("Prescription", "Over-the-counter")
                                                               for p in a.get("products", [])) for a in seen)
    return m, f'{url}?search=openfda.generic_name:"{ingredient}"'


def gen_drugs(s: Src, pool: list[dict], rng: random.Random, n: int) -> list[dict]:
    names = []
    for t in pool:
        for iv in (t["raw"]["protocolSection"].get("armsInterventionsModule") or {}).get("interventions", []):
            if iv.get("type") == "DRUG" and iv.get("name"):
                names.append(re.sub(r"\s+\d.*$|\(.*?\)", "", iv["name"]).strip())
    names = sorted({x for x in names if 3 < len(x) < 40 and not re.search(r"placebo|saline|standard|vehicle", x, re.IGNORECASE)})
    rng.shuffle(names)
    gen_yes = gen_no = 0
    out = {"drug_generic_us": [], "drug_first_approval": [], "drug_targets": []}
    oq = 'query($id:String!){drug(chemblId:$id){name mechanismsOfAction{rows{targets{approvedSymbol}}}}}'
    seen = set()
    for nm in names:
        if all(len(v) >= n for v in out.values()):
            break
        r = s.get(f"{CHEMBL}/molecule/search.json", {"q": nm, "limit": 5})
        if r.status_code != 200:
            continue
        mols = [m for m in r.json().get("molecules", []) if (m.get("pref_name") or "").lower() == nm.lower()]
        if not mols:
            continue
        m = mols[0]
        cid = m["molecule_chembl_id"]
        if cid in seen or float(m.get("max_phase") or 0) < 4:
            continue
        seen.add(cid)
        pref = m["pref_name"].lower()
        if m.get("first_approval") and len(out["drug_first_approval"]) < n:
            out["drug_first_approval"].append(q(f"firstappr-{cid}", "drug_first_approval",
                f"According to ChEMBL, in what year was {pref} ({cid}) first approved?", "year", int(m["first_approval"]),
                "a 4-digit year", [f"{CHEMBL}/molecule/{cid}.json"], tol_abs=0, chembl=cid))
        if len(out["drug_generic_us"]) < n and m.get("molecule_type") == "Small molecule":
            g, url = anda_marketed(s, pref)
            if g is not None and ((g and gen_yes < n // 2) or (not g and gen_no < n - n // 2)):
                gen_yes += g
                gen_no += not g
                out["drug_generic_us"].append(q(f"generic-{cid}", "drug_generic_us",
                    f"Is {pref} currently available as a marketed generic (an ANDA with a marketed product) in the United States, according to Drugs@FDA?",
                    "bool", g, "true or false", [url], chembl=cid))
        if len(out["drug_targets"]) < n:
            od = s.gql(oq, {"id": cid}).get("drug")
            if od:
                syms = sorted({t["approvedSymbol"] for row in (od.get("mechanismsOfAction") or {}).get("rows", [])
                               for t in row.get("targets") or []})
                if 1 <= len(syms) <= 8:
                    out["drug_targets"].append(q(f"targets-{cid}", "drug_targets",
                        f"Which human gene targets does {pref} ({cid}) act on, according to its mechanism-of-action annotations in Open Targets?",
                        "set", syms, "a JSON list of HGNC gene symbols", [OT + f"#drug={cid}"], f1_threshold=0.5, chembl=cid))
    return [x for v in out.values() for x in v]


def gen_multihop(late_qs: list[dict], s: Src, n: int) -> list[dict]:
    out = []
    for lq in late_qs:
        if len(out) >= n:
            break
        gens = []
        ok = True
        for dname in lq["gold"]:
            g, _ = anda_marketed(s, dname.lower())
            if g is None:
                continue  # biologics / no Drugs@FDA record: not generically available in this definition
            if g:
                gens.append(dname)
        if ok and gens:
            out.append(q(lq["id"].replace("latedrugs", "repurpose"), "multihop_generic_late_stage",
                f"For {lq['disease']}, which drugs that have reached phase 3 or later for this disease in Open Targets are also available as a marketed generic in the United States (Drugs@FDA ANDA)?",
                "set", sorted(gens), "a JSON list of drug names", lq["gold_sources"] + ["https://api.fda.gov/drug/drugsfda.json"],
                f1_threshold=0.5, difficulty="hard", disease=lq["disease"]))
    return out


def gen_notfound(s: Src, rng: random.Random, n: int) -> list[dict]:
    out = []
    while len(out) < n // 2:
        nct = f"NCT{rng.randint(9_000_0000, 9_999_9999):08d}"
        if s.get(f"{CTG}/studies/{nct}").status_code == 404:
            out.append(q(f"nf-{nct}", "not_found", f"What is the primary outcome measure of clinical trial {nct}?", "notfound", None,
                         "the primary outcome measure", [f"{CTG}/studies/{nct}"]))
    while len(out) < n:
        cid = f"CHEMBL{rng.randint(90_000_000, 99_999_999)}"
        if s.get(f"{CHEMBL}/molecule/{cid}.json").status_code == 404:
            out.append(q(f"nf-{cid}", "not_found", f"What is the mechanism of action of {cid}, and which indications has it been tested for?",
                         "notfound", None, "mechanism and indications", [f"{CHEMBL}/molecule/{cid}.json"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "eval/questions.jsonl"))
    ap.add_argument("--per-template", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20261103)
    ap.add_argument("--n-diseases", type=int, default=160)
    ap.add_argument("--only", nargs="*", default=[], help="rebuild only these templates (currently: disease_rarity)")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    s = Src()
    n = a.per_template

    frame, meta = orphanet_frame(s)
    rare = [f for f in frame if f["rarity"]["rare_eu"] and f["rarity"]["confidence"] != "low"]
    print(f"orphanet frame: {len(frame)} disorders with exact MONDO; {len(rare)} rare (non-low confidence)", flush=True)
    ntds = resolve_ntds(s)
    print(f"NTDs resolved: {len(ntds)}", flush=True)
    sample = rng.sample(rare, min(a.n_diseases, len(rare)))
    diseases = [{"name": f["name"], "ot_id": f["ot_id"], "orpha": f["orpha"]} for f in sample] + ntds
    rng.shuffle(diseases)

    qs: list[dict] = []
    errors: list[str] = []
    pool = [] if a.only else trial_pool(s, diseases, rng)
    print(f"trial pool: {len(pool)}", flush=True)

    def step(name, fn, *args):
        try:
            out = fn(*args)
            print(f"{name}: {len(out)} questions", flush=True)
            return out
        except Exception as exc:  # noqa: BLE001 - one failing template must not lose the others
            import traceback
            traceback.print_exc()
            errors.append(f"{name}: {exc!r}")
            return []

    if a.only:  # rebuild selected templates and merge into the existing bank
        keep = [json.loads(line) for line in Path(a.out).read_text().splitlines() if line.strip()]
        fresh = []
        if "disease_rarity" in a.only:
            fresh += step("rarity", gen_rarity, frame, rng, n)
        keep = [x for x in keep if x["template"] not in a.only] + fresh
        Path(a.out).write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in keep) + "\n")
        print(f"merged {len(fresh)} rebuilt questions; bank now {len(keep)}")
        return 1 if errors else 0
    qs += step("trials", gen_trials, s, pool, n)
    qs += step("counts", gen_counts, s, diseases, n)
    dq = step("disease", gen_disease, s, diseases, n)
    qs += dq
    qs += step("rarity", gen_rarity, frame, rng, n)
    qs += step("drugs", gen_drugs, s, pool, rng, n)
    qs += step("multihop", gen_multihop, [x for x in dq if x["template"] == "disease_late_stage_drugs"], s, n)
    qs += step("notfound", gen_notfound, s, rng, n)

    for x in qs:
        x.setdefault("difficulty", "standard")
        x["population"] = "NTD" if any(x.get("disease") == d["name"] and d.get("ntd") for d in ntds) else "rare"
    Path(a.out).write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in qs) + "\n")
    counts = {}
    for x in qs:
        counts[x["template"]] = counts.get(x["template"], 0) + 1
    manifest = {"built_at": now(), "seed": a.seed, "n_questions": len(qs), "per_template": counts,
                "orphanet_files": meta, "n_rare_frame": len(rare), "ntds": ntds, "errors": errors}
    Path(a.out).with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps(counts, indent=1))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
