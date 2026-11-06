"""Hard tier: multi-step / multi-source questions with deterministic gold (eval/questions_hard.jsonl).

H1 recruitment_footprint   count distinct countries with sites across all RECRUITING interventional trials for a disease
H2 late_generic_boxed      phase>=3 drugs for a disease (Open Targets) that are US-generic (Drugs@FDA) AND carry a boxed warning (FDA label)
H3 eligibility_check       is a described patient age/sex-eligible for a trial (unit-aware age parsing, boundary cases)
H4 source_conflict         does ChEMBL's first-approval year equal the year of the earliest original NDA approval in Drugs@FDA
H5 untested_target_drugs   approved drugs acting on the disease's top-ranked target that have no clinical record for that disease

Gold is computed from raw source responses, independent of biomcp code. Reuses the disease frame from build_questions.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
import build_questions as bq

CTG, OT, CHEMBL, FDA = bq.CTG, bq.OT, bq.CHEMBL, bq.FDA


def ctg_all(s, params, max_pages=10):
    out, token = [], None
    for _ in range(max_pages):
        p = dict(params, pageSize=100)
        if token:
            p["pageToken"] = token
        r = s.get(f"{CTG}/studies", p)
        if r.status_code != 200:
            return None
        b = r.json()
        out += b.get("studies", [])
        token = b.get("nextPageToken")
        if not token:
            return out
    return None  # too many pages: skip disease


def h1(s, diseases, n):
    qs = []
    for d in diseases:
        if len(qs) >= n:
            break
        st = ctg_all(s, {"query.cond": d["name"], "filter.overallStatus": "RECRUITING", "query.term": "AREA[StudyType]INTERVENTIONAL",
                         "fields": "protocolSection.identificationModule,protocolSection.contactsLocationsModule"}, max_pages=3)
        if not st or not (3 <= len(st) <= 150):
            continue
        countries = sorted({loc.get("country") for x in st for loc in (x["protocolSection"].get("contactsLocationsModule") or {}).get("locations", [])
                            if loc.get("country")})
        if len(countries) < 2:
            continue
        qs.append(bq.q(f"h1-{d['ot_id']}", "h_recruitment_footprint",
            f"Across all interventional trials for '{d['name']}' on ClinicalTrials.gov that are currently Recruiting, in how many distinct countries are trial sites listed?",
            "count", len(countries), "an integer", [f"{CTG}/studies?query.cond={d['name']}&filter.overallStatus=RECRUITING"],
            tol_abs=1, tol_rel=0.05, difficulty="hard", disease=d["name"], n_trials=len(st)))
    return qs


def boxed(s, name):
    r = s.get(f"{FDA}/label.json", {"search": f'openfda.generic_name:"{name}"', "limit": 5})
    if r.status_code == 404:
        return False
    if r.status_code != 200:
        return None
    return any(x.get("boxed_warning") for x in r.json().get("results", []))


def h2(s, late_qs, n):
    qs = []
    for lq in late_qs:
        if len(qs) >= n:
            break
        gold, ok = [], True
        for dn in lq["gold"]:
            g, _ = bq.anda_marketed(s, dn.lower())
            if g is None:
                continue
            b = boxed(s, dn.lower())
            if b is None:
                ok = False
                break
            if g and b:
                gold.append(dn)
        if ok:
            qs.append(bq.q(lq["id"].replace("latedrugs", "h2"), "h_late_generic_boxed",
                f"For {lq['disease']}, which drugs that reached phase 3 or later for this disease in Open Targets are BOTH available as a marketed US generic (Drugs@FDA ANDA) AND carry a boxed warning on their current FDA label? Answer an empty list if none.",
                "set", sorted(gold), "a JSON list of drug names (possibly empty)", lq["gold_sources"] + [f"{FDA}/label.json"],
                f1_threshold=0.5, difficulty="hard", disease=lq["disease"]))
    return qs


AGE_RE = re.compile(r"(\d+)\s*(Year|Month|Week|Day)", re.IGNORECASE)


def age_years(txt):
    if not txt:
        return None
    m = AGE_RE.search(txt)
    if not m:
        return None
    v, u = int(m.group(1)), m.group(2).lower()
    return v / {"year": 1, "month": 12, "week": 52.1775, "day": 365.25}[u]


def h3(s, pool, rng, n):
    qs = []
    for t in pool:
        if len(qs) >= n:
            break
        full = bq.ctg_study(s, t["nct"])
        if not full:
            continue
        em = full["protocolSection"].get("eligibilityModule") or {}
        lo, hi, sex = age_years(em.get("minimumAge")), age_years(em.get("maximumAge")), em.get("sex")
        if lo is None or sex not in ("ALL", "FEMALE", "MALE"):
            continue
        # boundary-probing patient: just inside or just outside an age limit, sometimes wrong sex
        choice = rng.choice(["in_low", "out_low", "in_high", "out_high", "sex"] if hi else ["in_low", "out_low", "sex"])
        if choice == "in_low":
            age = lo + (0.5 if lo < 2 else 1)
        elif choice == "out_low":
            age = max(0.1, lo - (0.25 if lo < 2 else 1))
        elif choice == "in_high":
            age = hi - (min(0.5, (hi - lo) / 2) if hi < 2 else 1)
        elif choice == "out_high":
            age = hi + (0.5 if hi < 2 else 1)
        else:
            age = lo + 1 if not hi else (lo + hi) / 2
        psex = ("male" if sex == "FEMALE" else "female") if (choice == "sex" and sex != "ALL") else rng.choice(
            ["female", "male"] if sex == "ALL" else [sex.lower()])
        if age <= 0 or (age < 2 and round(age * 12) < 1):
            continue  # never emit impossible ages (review found a '-4-month-old' from an 8-week upper limit)
        elig = (age >= lo) and (hi is None or age <= hi) and (sex == "ALL" or psex == sex.lower())
        age_txt = f"{round(age * 12)}-month-old" if age < 2 else f"{int(age)}-year-old"
        if age >= 2 and int(age) != age:
            continue
        qs.append(bq.q(f"h3-{t['nct']}", "h_eligibility_check",
            f"Based only on the age and sex criteria registered on ClinicalTrials.gov for {t['nct']}, would a {age_txt} {psex} be eligible to enrol?",
            "bool", elig, "true or false", [f"{CTG}/studies/{t['nct']}"], difficulty="hard", nct=t["nct"],
            basis={"minimumAge": em.get("minimumAge"), "maximumAge": em.get("maximumAge"), "sex": sex}))
    return qs


def earliest_nda_year(s, name):
    r = s.get(f"{FDA}/drugsfda.json", {"search": f'openfda.generic_name:"{name}"', "limit": 100})
    if r is None or r.status_code != 200:
        return None
    yrs = [int(sub["submission_status_date"][:4]) for a in r.json()["results"] if a["application_number"].startswith("NDA")
           for sub in a.get("submissions", []) if sub.get("submission_type") == "ORIG" and sub.get("submission_status") == "AP"
           and sub.get("submission_status_date")]
    return min(yrs) if yrs else None


def h4(s, drug_qs, n):
    qs = []
    for dq in drug_qs:
        if len(qs) >= n:
            break
        cid = dq["chembl"]
        name = re.search(r"was (.+?) \(CHEMBL", dq["question"]).group(1)
        fy = earliest_nda_year(s, name)
        if fy is None:
            continue
        qs.append(bq.q(f"h4-{cid}", "h_source_conflict",
            f"Does ChEMBL's first-approval year for {name} ({cid}) match the year of the earliest original NDA approval for {name} recorded in Drugs@FDA? Answer true if they are the same year.",
            "bool", dq["gold"] == fy, "true or false", dq["gold_sources"] + [f"{FDA}/drugsfda.json"], difficulty="hard",
            chembl=cid, basis={"chembl_first_approval": dq["gold"], "fda_earliest_nda_year": fy}))
    return qs


def h5(s, diseases, n):
    tq = 'query($id:String!){disease(efoId:$id){id name associatedTargets(page:{index:0,size:1}){rows{target{id approvedSymbol}}} drugAndClinicalCandidates{rows{drug{id}}}}}'
    gq = 'query($id:String!){target(ensemblId:$id){drugAndClinicalCandidates{rows{maxClinicalStage drug{id name}}}}}'
    qs = []
    for d in diseases:
        if len(qs) >= n:
            break
        try:
            dd = s.gql(tq, {"id": d["ot_id"]})["disease"]
        except RuntimeError:
            continue
        if not dd or not dd["associatedTargets"]["rows"]:
            continue
        tgt = dd["associatedTargets"]["rows"][0]["target"]
        tested = {r["drug"]["id"] for r in (dd.get("drugAndClinicalCandidates") or {}).get("rows", [])}
        tg = s.gql(gq, {"id": tgt["id"]}).get("target") or {}
        approved = {r["drug"]["id"]: r["drug"]["name"] for r in (tg.get("drugAndClinicalCandidates") or {}).get("rows", [])
                    if r.get("maxClinicalStage") == "APPROVAL"}
        gold = sorted(approved[i].upper() for i in approved if i not in tested)
        if not (1 <= len(gold) <= 8):
            continue
        qs.append(bq.q(f"h5-{d['ot_id']}", "h_untested_target_drugs",
            f"In Open Targets, the top-ranked target for {dd['name']} ({d['ot_id']}) is {tgt['approvedSymbol']}. Which APPROVED drugs acting on {tgt['approvedSymbol']} have no clinical record (no drug/clinical candidate entry) for {dd['name']}? These are naive repurposing candidates.",
            "set", gold, "a JSON list of drug names", [OT + f"#disease={d['ot_id']}", OT + f"#target={tgt['id']}"],
            f1_threshold=0.5, difficulty="hard", disease=dd["name"]))
    return qs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-template", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20261104)
    ap.add_argument("--out", default=str(ROOT / "eval/questions_hard.jsonl"))
    a = ap.parse_args()
    rng = random.Random(a.seed)
    s = bq.Src()
    n = a.per_template
    frame, _ = bq.orphanet_frame(s)
    rare = [f for f in frame if f["rarity"]["rare_eu"] and f["rarity"]["confidence"] != "low"]
    diseases = [{"name": f["name"], "ot_id": f["ot_id"]} for f in rng.sample(rare, min(220, len(rare)))] + bq.resolve_ntds(s)
    rng.shuffle(diseases)
    base = [json.loads(line) for line in (ROOT / "eval/questions.jsonl").read_text().splitlines() if line.strip()]
    base_ids = {x["id"] for x in base}
    pool = bq.trial_pool(s, diseases[:80], rng)
    pool = [t for t in pool if f"sites-{t['nct']}" not in base_ids and f"enrol-{t['nct']}" not in base_ids]
    late = [x for x in base if x["template"] == "disease_late_stage_drugs"]
    drug_fa = [x for x in base if x["template"] == "drug_first_approval"]
    qs, errors = [], []
    for name, fn, args in [("h1", h1, (s, diseases, n)), ("h2", h2, (s, late, n)), ("h3", h3, (s, pool, rng, n)),
                           ("h4", h4, (s, drug_fa, n)), ("h5", h5, (s, diseases, n))]:
        try:
            out = fn(*args)
            print(f"{name}: {len(out)}", flush=True)
            qs += out
        except Exception as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            errors.append(f"{name}: {exc!r}")
    for x in qs:
        x["population"] = "NTD" if any(x.get("disease") == d["name"] and d.get("ntd") for d in diseases) else "rare"
    Path(a.out).write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in qs) + "\n")
    print(f"{len(qs)} hard questions; errors: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
