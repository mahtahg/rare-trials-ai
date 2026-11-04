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
import asyncio
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
    """Async client with bounded concurrency and retries (ChEMBL/openFDA allow modest parallel use)."""

    def __init__(self, concurrency: int = 8):
        self.c = httpx.AsyncClient(headers=UA, timeout=60, follow_redirects=True)
        self.sem = asyncio.Semaphore(concurrency)

    async def get(self, url, params=None):
        async with self.sem:
            for i in range(6):
                try:
                    r = await self.c.get(url, params=params)
                except httpx.TransportError:
                    await asyncio.sleep(2 ** i)
                    continue
                if r.status_code in (429, 500, 502, 503, 504):
                    await asyncio.sleep(2 ** i)
                    continue
                return r
        return None


async def chembl_exact(c: C, name: str) -> dict | None:
    for params in ({"pref_name__iexact": name}, {"molecule_synonyms__molecule_synonym__iexact": name}):
        r = await c.get(f"{CHEMBL}/molecule.json", {**params, "limit": 5, "only": "molecule_chembl_id,max_phase,molecule_hierarchy"})
        if r is None or r.status_code != 200:
            continue
        mols = r.json().get("molecules", [])
        if mols:
            m = sorted(mols, key=lambda x: -float(x.get("max_phase") or 0))[0]
            parent = (m.get("molecule_hierarchy") or {}).get("parent_chembl_id") or m["molecule_chembl_id"]
            return {"matched_on": list(params)[0].split("__")[0], "chembl_id": m["molecule_chembl_id"], "parent_chembl_id": parent}
    return None


async def parent_profile(c: C, cid: str) -> dict:
    m, ind = await asyncio.gather(
        c.get(f"{CHEMBL}/molecule/{cid}.json"),
        c.get(f"{CHEMBL}/drug_indication.json", {"parent_molecule_chembl_id": cid, "limit": 1000}))
    mj = m.json() if m is not None and m.status_code == 200 else {}
    rows = ind.json().get("drug_indications", []) if ind is not None and ind.status_code == 200 else []
    approved = sorted({(r.get("mesh_heading") or r.get("efo_term")) for r in rows
                       if float(r.get("max_phase_for_ind") or 0) >= 4 and (r.get("mesh_heading") or r.get("efo_term"))})
    return {"pref_name": mj.get("pref_name"), "max_phase": mj.get("max_phase"), "first_approval": mj.get("first_approval"),
            "molecule_type": mj.get("molecule_type"), "approved_indications": approved, "n_indications_any_phase": len(rows)}


async def generic_us(c: C, name: str) -> bool | None:
    r = await c.get(FDA, {"search": f'openfda.generic_name:"{name}"', "limit": 100})
    if r is None:
        return None
    if r.status_code == 404:
        return False
    if r.status_code != 200:
        return None
    return any(a["application_number"].startswith("ANDA") and any(p.get("marketing_status") in ("Prescription", "Over-the-counter")
                                                                   for p in a.get("products", [])) for a in r.json()["results"])


SKIP = re.compile(r"placebo|saline|vehicle|standard (of )?care|sham|control|no intervention|best supportive", re.IGNORECASE)


async def resolve(c: C, n: str) -> dict:
    hit = await chembl_exact(c, n)
    if not hit:
        stripped = re.sub(r"\s+", " ", STRIP.sub(" ", n)).strip(" ,;-")
        if stripped and stripped.lower() != n.lower() and len(stripped) > 2:
            hit = await chembl_exact(c, stripped)
            if hit:
                hit["matched_on"] += "_after_strip"
                hit["stripped"] = stripped
    return hit or {"unmatched": True}


async def amain(a) -> int:
    names = set()
    with gzip.open(a.cohort, "rt") as f:
        for line in f:
            r = json.loads(line)
            names.update(n.strip() for n in r["drugs"] + r["drug_other_names"] if n and n.strip())
    out_p = Path(a.out)
    done = json.loads(out_p.read_text()) if out_p.exists() else {"names": {}, "parents": {}}
    c = C(a.concurrency)
    todo = sorted(n for n in names if n not in done["names"] and not SKIP.search(n))
    for n in names:
        if SKIP.search(n):
            done["names"].setdefault(n, {"unmatched": True, "reason": "non-drug comparator"})
    print(f"{len(names)} unique names, {len(todo)} to resolve", flush=True)
    t0 = asyncio.get_event_loop().time()
    for i in range(0, len(todo), 400):
        chunk = todo[i:i + 400]
        hits = await asyncio.gather(*(resolve(c, n) for n in chunk))
        new_parents = set()
        for n, h in zip(chunk, hits):
            done["names"][n] = h
            if not h.get("unmatched") and h["parent_chembl_id"] not in done["parents"]:
                new_parents.add(h["parent_chembl_id"])
        profs = await asyncio.gather(*(parent_profile(c, p) for p in new_parents))
        gens = await asyncio.gather(*(generic_us(c, (pr.get("pref_name") or "").lower()) if pr.get("pref_name") else asyncio.sleep(0)
                                      for pr in profs))
        for pid, pr, g in zip(new_parents, profs, gens):
            pr["generic_available_us"] = g
            done["parents"][pid] = pr
        out_p.write_text(json.dumps(done))
        el = asyncio.get_event_loop().time() - t0
        print(f"{i + len(chunk)}/{len(todo)} in {el:.0f}s; parents {len(done['parents'])}", flush=True)
        if a.max_minutes and el > a.max_minutes * 60:
            print("time budget reached; resume later", flush=True)
            break
    done["complete"] = all(n in done["names"] for n in names)
    out_p.write_text(json.dumps(done))
    matched = sum(1 for v in done["names"].values() if not v.get("unmatched"))
    print(f"matched {matched}/{len(done['names'])} names to {len(done['parents'])} parent compounds")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default=str(ROOT / "project6/data/cohort_ctgov.jsonl.gz"))
    ap.add_argument("--out", default=str(ROOT / "project6/data/drug_map.json"))
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-minutes", type=float, default=200)
    return asyncio.run(amain(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
