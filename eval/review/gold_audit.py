"""Primary-source audit of the 41 gold-check questions.

Re-fetches each question's primary record from the source API at audit time, archives the raw payloads
(eval/review/gold_audit/<qid>/*.json), re-derives the answer with code written separately from
eval/build_questions.py (deliberately not imported), and writes eval/review/gold_audit.jsonl + .md with
an evidence excerpt per item so a human can confirm each one against the archived primary record.

A mismatch is not automatically a gold error: registry records drift between gold creation
(gold_retrieved_at) and the audit. Each row records both timestamps.

    python eval/review/gold_audit.py
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "eval/review/gold_audit"
CTG = "https://clinicaltrials.gov/api/v2"
OT = "https://api.platform.opentargets.org/api/v4/graphql"
CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"
FDA = "https://api.fda.gov/drug"
ORPHA = "https://api.orphadata.com"
LATE = {"PHASE_3", "PHASE_4", "APPROVAL"}
C = httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "rare-trials-ai gold audit (+github.com/mahtahg/rare-trials-ai)"})


class Archive:
    def __init__(self, qid: str):
        self.dir = OUT / qid
        self.dir.mkdir(parents=True, exist_ok=True)
        self.files: list[str] = []

    def save(self, name: str, url: str, status: int, body) -> None:
        p = self.dir / f"{len(self.files):02d}_{name}.json"
        p.write_text(json.dumps({"url": url, "status": status, "retrieved_at": datetime.now(timezone.utc).isoformat(), "body": body},
                                ensure_ascii=False, indent=1))
        self.files.append(str(p.relative_to(ROOT)))


def get(ar: Archive, name: str, url: str, params=None):
    for i in range(5):
        try:
            r = C.get(url, params=params)
        except httpx.TransportError:
            time.sleep(2 ** i)
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** i)
            continue
        try:
            body = r.json()
        except ValueError:
            body = r.text[:5000]
        ar.save(name, str(r.url), r.status_code, body)
        return r.status_code, body
    raise RuntimeError(f"unreachable: {url}")


def gql(ar: Archive, name: str, query: str, var: dict):
    for i in range(5):
        try:
            r = C.post(OT, json={"query": query, "variables": var})
        except httpx.TransportError:
            time.sleep(2 ** i)
            continue
        if r.status_code >= 500:
            time.sleep(2 ** i)
            continue
        body = r.json()
        ar.save(name, OT, r.status_code, {"query": query, "variables": var, "response": body})
        return body.get("data") or {}
    raise RuntimeError("Open Targets unreachable")


def study(ar, nct):
    st, b = get(ar, "ctgov_study", f"{CTG}/studies/{nct}")
    return b if st == 200 else None


def years(txt):
    m = re.search(r"(\d+)\s*(Year|Month|Week|Day)", txt or "", re.IGNORECASE)
    return None if not m else int(m.group(1)) / {"year": 1, "month": 12, "week": 52.1775, "day": 365.25}[m.group(2).lower()]


def generic(ar, name):
    rows, skip, total = [], 0, 1
    while skip < total and skip < 500:
        st, b = get(ar, f"drugsfda_{name[:20]}_{skip}", f"{FDA}/drugsfda.json", {"search": f'openfda.generic_name:"{name}"', "limit": 100, "skip": skip})
        if st == 404:
            break
        if st != 200:
            return None, "Drugs@FDA error"
        rows += b["results"]
        total = b["meta"]["results"]["total"]
        skip += 100
    if not rows:
        return None, "no Drugs@FDA record"
    andas = [a["application_number"] for a in rows if a["application_number"].startswith("ANDA")
             and any(p.get("marketing_status") in ("Prescription", "Over-the-counter") for p in a.get("products", []))]
    return bool(andas), f"marketed ANDAs: {len(andas)} (e.g. {', '.join(andas[:3])})" if andas else "no marketed ANDA"


def late_drugs(ar, did):
    d = gql(ar, "ot_disease_drugs", "query($id:String!){disease(efoId:$id){name drugAndClinicalCandidates{rows{maxClinicalStage drug{id name}}}}}",
            {"id": did}).get("disease") or {}
    return sorted({r["drug"]["name"].upper() for r in (d.get("drugAndClinicalCandidates") or {}).get("rows", []) if r.get("maxClinicalStage") in LATE})


def did_of(q):
    return re.search(r"(MONDO_\d+|EFO_\d+|Orphanet_\d+)", q["id"] + " " + " ".join(q.get("gold_sources", []))).group(1)


def derive(q, ar):
    t, qt = q["template"], q["question"]
    if t in ("trial_why_stopped", "trial_enrollment", "trial_has_sap", "trial_n_sites", "h_eligibility_check"):
        s = study(ar, q["nct"])
        if s is None:
            return None, "record not retrievable"
        ps = s["protocolSection"]
        if t == "trial_why_stopped":
            sm = ps.get("statusModule", {})
            return sm.get("whyStopped"), f"overallStatus={sm.get('overallStatus')}; whyStopped={sm.get('whyStopped')!r}"
        if t == "trial_enrollment":
            ei = ps.get("designModule", {}).get("enrollmentInfo") or {}
            return {"count": ei.get("count"), "type": ei.get("type")}, f"enrollmentInfo={ei}"
        if t == "trial_has_sap":
            docs = (s.get("documentSection") or {}).get("largeDocumentModule", {}).get("largeDocs", [])
            return any(d.get("hasSap") for d in docs), f"largeDocs={[{k: d.get(k) for k in ('typeAbbrev', 'hasSap', 'filename')} for d in docs]}"
        if t == "trial_n_sites":
            locs = (ps.get("contactsLocationsModule") or {}).get("locations", [])
            return len(locs), f"{len(locs)} locations: " + "; ".join(f"{x.get('facility')}, {x.get('country')}" for x in locs[:5])
        em = ps.get("eligibilityModule") or {}
        m = re.search(r"would an? (\d+)-(month|year)-old (male|female)", qt)
        age = int(m.group(1)) / (12 if m.group(2) == "month" else 1)
        lo, hi, sex = years(em.get("minimumAge")), years(em.get("maximumAge")), em.get("sex")
        ok = (lo is None or age >= lo) and (hi is None or age <= hi) and (sex in ("ALL", None) or sex.lower() == m.group(3))
        return ok, f"patient {m.group(1)} {m.group(2)}s {m.group(3)}; minimumAge={em.get('minimumAge')}, maximumAge={em.get('maximumAge')}, sex={sex}"
    if t == "trial_count":
        st, b = get(ar, "ctgov_count", f"{CTG}/studies", {"query.cond": q["disease"], "filter.overallStatus": "TERMINATED,WITHDRAWN",
                                                            "query.term": "AREA[StudyType]INTERVENTIONAL", "countTotal": "true", "pageSize": 100})
        return (b.get("totalCount") if st == 200 else None), f"totalCount={b.get('totalCount')}; e.g. " + ", ".join(
            x["protocolSection"]["identificationModule"]["nctId"] for x in b.get("studies", [])[:6])
    if t == "h_recruitment_footprint":
        countries, token, n = set(), None, 0
        for i in range(5):
            p = {"query.cond": q["disease"], "filter.overallStatus": "RECRUITING", "query.term": "AREA[StudyType]INTERVENTIONAL", "pageSize": 100}
            if token:
                p["pageToken"] = token
            st, b = get(ar, f"ctgov_recruiting_{i}", f"{CTG}/studies", p)
            for x in b.get("studies", []):
                n += 1
                countries |= {loc.get("country") for loc in (x["protocolSection"].get("contactsLocationsModule") or {}).get("locations", []) if loc.get("country")}
            token = b.get("nextPageToken")
            if not token:
                break
        return len(countries), f"{n} recruiting trials; countries: {', '.join(sorted(countries))}"
    if t == "disease_top_targets":
        d = gql(ar, "ot_targets", "query($id:String!){disease(efoId:$id){name associatedTargets(page:{index:0,size:5}){rows{score target{approvedSymbol}}}}}",
                {"id": did_of(q)}).get("disease") or {}
        rows = d.get("associatedTargets", {}).get("rows", [])
        return [r["target"]["approvedSymbol"] for r in rows], "; ".join(f"{r['target']['approvedSymbol']} {r['score']:.3f}" for r in rows)
    if t == "disease_late_stage_drugs":
        ls = late_drugs(ar, did_of(q))
        return ls, f"phase 3+ drugs: {ls}"
    if t in ("multihop_generic_late_stage", "h_late_generic_boxed"):
        ls, keep, ev = late_drugs(ar, did_of(q)), [], []
        for dn in ls:
            g, why = generic(ar, dn.lower())
            item = f"{dn}: {why}"
            if t == "h_late_generic_boxed" and g:
                st, b = get(ar, f"label_{dn[:20]}", f"{FDA}/label.json", {"search": f'openfda.generic_name:"{dn.lower()}"', "limit": 5})
                bx = st == 200 and any(x.get("boxed_warning") for x in b.get("results", []))
                item += f"; boxed warning on a current label: {bx}"
                g = g and bx
            ev.append(item)
            if g:
                keep.append(dn)
        return sorted(keep), " | ".join(ev)
    if t == "drug_generic_us":
        name = re.search(r"Is (.+?) currently available", qt).group(1)
        g, why = generic(ar, name)
        return g, why
    if t in ("drug_first_approval", "h_source_conflict"):
        cid = q["chembl"]
        st, m = get(ar, "chembl_molecule", f"{CHEMBL}/molecule/{cid}.json")
        fa = m.get("first_approval") if st == 200 else None
        if t == "drug_first_approval":
            return fa, f"{cid} pref_name={m.get('pref_name')}, first_approval={fa}"
        name = re.search(r"year for (.+?) \(CHEMBL", qt).group(1)
        st, b = get(ar, "drugsfda", f"{FDA}/drugsfda.json", {"search": f'openfda.generic_name:"{name}"', "limit": 100})
        yrs = sorted(int(s["submission_status_date"][:4]) for a in (b.get("results", []) if st == 200 else []) if a["application_number"].startswith("NDA")
                     for s in a.get("submissions", []) if s.get("submission_type") == "ORIG" and s.get("submission_status") == "AP" and s.get("submission_status_date"))
        ey = yrs[0] if yrs else None
        return (fa == ey) if (fa and ey) else None, f"ChEMBL first_approval={fa}; earliest ORIG-AP NDA in Drugs@FDA={ey}"
    if t == "drug_targets":
        d = gql(ar, "ot_drug", "query($id:String!){drug(chemblId:$id){name mechanismsOfAction{rows{mechanismOfAction targets{approvedSymbol}}}}}",
                {"id": q["chembl"]}).get("drug") or {}
        rows = (d.get("mechanismsOfAction") or {}).get("rows", [])
        return sorted({t2["approvedSymbol"] for r in rows for t2 in r.get("targets") or []}), "; ".join(
            f"{r['mechanismOfAction']} -> {[t2['approvedSymbol'] for t2 in r.get('targets') or []]}" for r in rows)
    if t == "h_untested_target_drugs":
        did = did_of(q)
        d = gql(ar, "ot_disease", "query($id:String!){disease(efoId:$id){associatedTargets(page:{index:0,size:1}){rows{target{id approvedSymbol}}} drugAndClinicalCandidates{rows{drug{id}}}}}",
                {"id": did}).get("disease") or {}
        tgt = d["associatedTargets"]["rows"][0]["target"]
        tested = {r["drug"]["id"] for r in (d.get("drugAndClinicalCandidates") or {}).get("rows", [])}
        g = gql(ar, "ot_target", "query($id:String!){target(ensemblId:$id){drugAndClinicalCandidates{rows{maxClinicalStage drug{id name}}}}}",
                {"id": tgt["id"]}).get("target") or {}
        appr = {r["drug"]["id"]: r["drug"]["name"].upper() for r in (g.get("drugAndClinicalCandidates") or {}).get("rows", []) if r.get("maxClinicalStage") == "APPROVAL"}
        return sorted(v for k, v in appr.items() if k not in tested), f"top target {tgt['approvedSymbol']}; approved on target: {sorted(appr.values())}; tested for disease: {len(tested)} drugs"
    if t == "not_found":
        ident = re.search(r"(NCT\d{8}|CHEMBL\d+)", qt).group(1)
        url = f"{CTG}/studies/{ident}" if ident.startswith("NCT") else f"{CHEMBL}/molecule/{ident}.json"
        st, _ = get(ar, "lookup", url)
        return None if st == 404 else "EXISTS", f"HTTP {st} for {ident}"
    if t == "disease_rarity":
        code = re.search(r"ORPHA:(\d+)", qt).group(1)
        st, b = get(ar, "orphadata_epi", f"{ORPHA}/rd-epidemiology/orphacodes/{code}")
        prevs = (((b or {}).get("data") or {}).get("results") or {}).get("Prevalence") or [] if st == 200 else []
        upper = {">1 / 1000": 99.0, "6-9 / 10 000": 9.0, "1-5 / 10 000": 5.0, "1-9 / 100 000": 0.9, "1-9 / 1 000 000": 0.09, "<1 / 1 000 000": 0.01}
        pts = [p for p in prevs if p.get("PrevalenceType") == "Point prevalence" and p.get("PrevalenceClass") in upper]
        pts = [p for p in pts if p.get("PrevalenceValidationStatus") == "Validated"] or pts
        rare = None
        for geo in ("Worldwide", "Europe", None):
            cand = [p for p in pts if geo is None or p.get("PrevalenceGeographic") == geo]
            if cand:  # highest class in the preferred geography (conservative)
                rare = max(upper[p["PrevalenceClass"]] for p in cand) <= 5.0
                break
        ev = "; ".join(f"{p.get('PrevalenceGeographic')}: {p.get('PrevalenceClass')} ({p.get('PrevalenceType')}, {p.get('PrevalenceValidationStatus')})" for p in prevs[:6])
        return rare, ev or f"HTTP {st}; no prevalence rows"
    return None, f"no audit rule for {t}"


def norm(x):
    if isinstance(x, list):
        return sorted(re.sub(r"\s+", " ", str(v)).strip().upper() for v in x)
    if isinstance(x, str):
        return re.sub(r"\s+", " ", x).strip().lower()
    return x


def main() -> int:
    items = json.loads((ROOT / "eval/review/review_items.json").read_text())
    spot = [x["id"] for x in items if x.get("spot_check")]
    qs = {}
    for f in ("eval/questions.jsonl", "eval/questions_hard.jsonl"):
        for line in (ROOT / f).read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                qs[q["id"]] = q
    excluded = set(json.loads((ROOT / "eval/excluded_questions.json").read_text())) if (ROOT / "eval/excluded_questions.json").exists() else set()
    rows = []
    for qid in spot:
        q = qs[qid]
        ar = Archive(qid)
        try:
            val, ev = derive(q, ar)
            err = None
        except Exception as e:  # noqa: BLE001 - recorded per item
            val, ev, err = None, "", repr(e)
        g = q["gold"]
        if q["template"] == "trial_count" or q["template"] == "h_recruitment_footprint":
            match = val is not None and abs(val - g) <= max(q.get("tol_abs", 0), q.get("tol_rel", 0) * g)
        elif q["template"] == "trial_why_stopped":
            match = norm(val) == norm(g)
        else:
            match = norm(val) == norm(g)
        rows.append({"id": qid, "template": q["template"], "question": q["question"], "gold": g, "audit_value": val,
                     "auto_match": bool(match) if err is None else None, "evidence": ev[:1500], "error": err,
                     "gold_retrieved_at": q.get("gold_retrieved_at"), "audited_at": datetime.now(timezone.utc).isoformat(),
                     "primary_sources": q.get("gold_sources"), "archived_payloads": ar.files, "in_reviewed_set": qid not in excluded})
        print(f"{qid}: match={rows[-1]['auto_match']} {err or ''}", flush=True)
    (ROOT / "eval/review/gold_audit.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    n_m = sum(r["auto_match"] is True for r in rows)
    md = ["# Gold-answer primary-source audit", "",
          (f"{len(rows)} gold-check items; automatic re-derivation matches gold for {n_m}; mismatches {sum(r['auto_match'] is False for r in rows)}; "
           f"errors {sum(r['auto_match'] is None for r in rows)}. Raw payloads archived under `eval/review/gold_audit/<id>/`."),
          "Automatic matching is a machine check, not human verification; the `Verified (human)` column of the review workbook records the latter.", "",
          "| id | match | gold | audit value | evidence |", "|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['id']} | {r['auto_match']} | {json.dumps(r['gold'])[:80]} | {json.dumps(r['audit_value'])[:80]} | {r['evidence'][:200].replace('|', '/')} |")
    (ROOT / "eval/review/gold_audit.md").write_text("\n".join(md) + "\n")
    print(md[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
