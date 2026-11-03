"""Project 6, step 2: normalise every DRUG intervention in the cohort to ChEMBL (deterministic).

For each unique intervention name (and listed other names) we try, in order:
exact ChEMBL preferred name, exact ChEMBL synonym, then the same after stripping
dose/formulation words. Matches resolve to the parent compound. For each matched
parent we record max phase, first approval year, approved indications
(max_phase_for_ind == 4, MeSH/EFO) and US marketed-generic status (Drugs@FDA ANDA).
Unmatched names are kept with reason so the LLM/human steps can see them.

    python project6/pipeline/normalize_drugs.py
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"
FDA = "https://api.fda.gov/drug/drugsfda.json"
UA = {"User-Agent": "rare-trials-ai/project6 (+https://github.com/mahtahg/rare-trials-ai)"}
STRIP = re.compile(
    r"\b(\d+(\.\d+)?\s*(mg|mcg|µg|g|ml|iu|units?|%)(/\w+)?|tablets?|capsules?|injection|oral|iv|intravenous|"
    r"solution|suspension|cream|ointment|gel|extended[- ]release|er|xr|sr|hydrochloride|hcl|sodium|potassium|"
    r"mesylate|sulfate|acetate|maleate|tartrate|citrate|phosphate)\b|\(.*?\)|®|™", re.IGNORECASE)


class C:
    def __init__(self):
        self.c = httpx.Client(headers=UA, timeout=60, follow_redirects=True)

    def get(self, url, params=None):
        for i in range(6):
            try:
                r = self.c.get(url, params=params)
            except httpx.TransportError:
                time.sleep(2 ** i)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i)
                continue
            time.sleep(0.15)
            return r
        return None


def chembl_exact(c: C, name: str) -> dict | None:
    for params in ({"pref_name__iexact": name}, {"molecule_synonyms__molecule_synonym__iexact": name}):
        r = c.get(f"{CHEMBL}/molecule.json", {**params, "limit": 5})
        if r is None or r.status_code != 200:
            continue
        mols = r.json().get("molecules", [])
        if mols:
            m = sorted(mols, key=lambda x: -float(x.get("max_phase") or 0))[0]
            parent = (m.get("molecule_hierarchy") or {}).get("parent_chembl_id") or m["molecule_chembl_id"]
            return {"matched_on": list(params)[0].split("__")[0], "chembl_id": m["molecule_chembl_id"], "parent_chembl_id": parent}
    return None


def parent_profile(c: C, cid: str) -> dict:
    m = c.get(f"{CHEMBL}/molecule/{cid}.json")
    mj = m.json() if m is not None and m.status_code == 200 else {}
    ind = c.get(f"{CHEMBL}/drug_indication.json", {"parent_molecule_chembl_id": cid, "limit": 1000})
    rows = ind.json().get("drug_indications", []) if ind is not None and ind.status_code == 200 else []
    approved = sorted({(r.get("mesh_heading") or r.get("efo_term")) for r in rows
                       if float(r.get("max_phase_for_ind") or 0) >= 4 and (r.get("mesh_heading") or r.get("efo_term"))})
    return {"pref_name": mj.get("pref_name"), "max_phase": mj.get("max_phase"), "first_approval": mj.get("first_approval"),
            "molecule_type": mj.get("molecule_type"), "approved_indications": approved, "n_indications_any_phase": len(rows)}


def generic_us(c: C, name: str) -> bool | None:
    r = c.get(FDA, {"search": f'openfda.generic_name:"{name}"', "limit": 100})
    if r is None:
        return None
    if r.status_code == 404:
        return False
    if r.status_code != 200:
        return None
    return any(a["application_number"].startswith("ANDA") and any(p.get("marketing_status") in ("Prescription", "Over-the-counter")
                                                                   for p in a.get("products", [])) for a in r.json()["results"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default=str(ROOT / "project6/data/cohort_ctgov.jsonl.gz"))
    ap.add_argument("--out", default=str(ROOT / "project6/data/drug_map.json"))
    a = ap.parse_args()
    names = set()
    with gzip.open(a.cohort, "rt") as f:
        for line in f:
            r = json.loads(line)
            names.update(n.strip() for n in r["drugs"] + r["drug_other_names"] if n and n.strip())
    out_p = Path(a.out)
    done = json.loads(out_p.read_text()) if out_p.exists() else {"names": {}, "parents": {}}
    c = C()
    todo = sorted(n for n in names if n not in done["names"])
    print(f"{len(names)} unique names, {len(todo)} to resolve", flush=True)
    for i, n in enumerate(todo):
        hit = chembl_exact(c, n)
        if not hit:
            stripped = re.sub(r"\s+", " ", STRIP.sub(" ", n)).strip(" ,;-")
            if stripped and stripped.lower() != n.lower() and len(stripped) > 2:
                hit = chembl_exact(c, stripped)
                if hit:
                    hit["matched_on"] += "_after_strip"
                    hit["stripped"] = stripped
        done["names"][n] = hit or {"unmatched": True}
        if hit and hit["parent_chembl_id"] not in done["parents"]:
            prof = parent_profile(c, hit["parent_chembl_id"])
            prof["generic_available_us"] = generic_us(c, (prof.get("pref_name") or n).lower()) if prof.get("pref_name") else None
            done["parents"][hit["parent_chembl_id"]] = prof
        if i % 200 == 0:
            out_p.write_text(json.dumps(done))
            print(f"{i}/{len(todo)}", flush=True)
    out_p.write_text(json.dumps(done))
    matched = sum(1 for v in done["names"].values() if not v.get("unmatched"))
    print(f"matched {matched}/{len(done['names'])} names to {len(done['parents'])} parent compounds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
