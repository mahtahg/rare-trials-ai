"""Gold correction v1.1 for the Drugs@FDA-dependent templates.

The v1 gold (and the v1 RareMCP fda tools) searched Drugs@FDA by `openfda.generic_name`. Older applications
often have no openFDA block, so that search misses them (e.g. carboplatin's 1989 NDA). v1.1 takes the union of
the `openfda.generic_name` and `products.active_ingredients.name` searches, de-duplicated by application number.

Affected templates: drug_generic_us, multihop_generic_late_stage, h_late_generic_boxed, h_source_conflict.
For the two set templates the late-stage drug list is the one frozen in the v1 gold (no Open Targets refetch),
so only the Drugs@FDA step changes. Boxed-warning look-ups are unchanged (SPL labels carry openFDA fields).

Writes eval/gold_corrections_v1_1.json ({qid: {old, new, evidence}}) and archives raw payloads under
eval/review/gold_v1_1/. score.py applies the corrections with --gold-corrections.

    python eval/gold_v1_1.py
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
FDA = "https://api.fda.gov/drug"
ARCH = ROOT / "eval/review/gold_v1_1"
C = httpx.Client(timeout=60, headers={"User-Agent": "rare-trials-ai gold v1.1 (+github.com/mahtahg/rare-trials-ai)"})
_cache: dict[str, list] = {}


def get(url, params):
    for i in range(6):
        try:
            r = C.get(url, params=params)
        except httpx.TransportError:
            time.sleep(2 ** i)
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** i)
            continue
        return r
    raise RuntimeError(url)


def apps(name: str) -> list[dict]:
    key = name.lower()
    if key in _cache:
        return _cache[key]
    seen = {}
    for field in ("openfda.generic_name", "products.active_ingredients.name"):
        skip, total = 0, 1
        while skip < total and skip < 1000:
            r = get(f"{FDA}/drugsfda.json", {"search": f'{field}:"{name}"', "limit": 100, "skip": skip})
            if r.status_code == 404:
                break
            r.raise_for_status()
            b = r.json()
            for a in b["results"]:
                seen[a["application_number"]] = a
            total = b["meta"]["results"]["total"]
            skip += 100
    out = list(seen.values())
    ARCH.mkdir(parents=True, exist_ok=True)
    (ARCH / f"drugsfda_{re.sub(r'[^a-z0-9]+', '_', key)}.json").write_text(json.dumps(
        {"name": name, "retrieved_at": datetime.now(timezone.utc).isoformat(), "n": len(out),
         "applications": [{"application_number": a["application_number"], "sponsor": a.get("sponsor_name"),
                           "products": [{"brand": p.get("brand_name"), "status": p.get("marketing_status"),
                                         "ingredients": [i.get("name") for i in p.get("active_ingredients") or []]} for p in a.get("products", [])],
                           "orig_approvals": [s.get("submission_status_date") for s in a.get("submissions", [])
                                              if s.get("submission_type") == "ORIG" and s.get("submission_status") == "AP"]} for a in out]}, indent=1))
    _cache[key] = out
    return out


def marketed_anda(name: str):
    a = apps(name)
    if not a:
        return None, "no Drugs@FDA record"
    m = [x["application_number"] for x in a if x["application_number"].startswith("ANDA")
         and any(p.get("marketing_status") in ("Prescription", "Over-the-counter") for p in x.get("products", []))]
    return bool(m), f"{len(m)} marketed ANDAs" + (f" (e.g. {', '.join(m[:3])})" if m else "")


def earliest_nda(name: str):
    yrs = [(int(s["submission_status_date"][:4]), x["application_number"]) for x in apps(name) if x["application_number"].startswith("NDA")
           for s in x.get("submissions", []) if s.get("submission_type") == "ORIG" and s.get("submission_status") == "AP" and s.get("submission_status_date")]
    return min(yrs) if yrs else (None, None)


def boxed(name: str):
    r = get(f"{FDA}/label.json", {"search": f'openfda.generic_name:"{name}"', "limit": 5})
    if r.status_code == 404:
        return False
    r.raise_for_status()
    return any(x.get("boxed_warning") for x in r.json().get("results", []))


def main() -> int:
    qs = {}
    for f in ("eval/questions.jsonl", "eval/questions_hard.jsonl"):
        for line in (ROOT / f).read_text().splitlines():
            if line.strip():
                q = json.loads(line)
                qs[q["id"]] = q
    out = {}
    for qid, q in qs.items():
        t, new, ev = q["template"], None, ""
        if t == "drug_generic_us":
            name = re.search(r"Is (.+?) currently available", q["question"]).group(1)
            new, ev = marketed_anda(name)
            if new is None:
                continue
        elif t == "h_source_conflict":
            name = re.search(r"year for (.+?) \(CHEMBL", q["question"]).group(1)
            fa = q["basis"]["chembl_first_approval"]
            yr, app = earliest_nda(name)
            if yr is None:
                continue
            new, ev = fa == yr, f"ChEMBL {fa}; earliest original NDA approval {yr} ({app})"
        elif t in ("multihop_generic_late_stage", "h_late_generic_boxed"):
            base = qs.get(re.sub(r"^(repurpose|h2)-", "latedrugs-", qid))
            if not base:
                continue
            keep, parts = [], []
            for dn in base["gold"]:
                g, why = marketed_anda(dn.lower())
                if g is None:
                    parts.append(f"{dn}: {why}")
                    continue
                b = boxed(dn.lower()) if (t == "h_late_generic_boxed" and g) else None
                parts.append(f"{dn}: {why}" + (f"; boxed {b}" if b is not None else ""))
                if g and (t == "multihop_generic_late_stage" or b):
                    keep.append(dn)
            new, ev = sorted(keep), " | ".join(parts)
        else:
            continue
        old = q["gold"]
        same = (sorted(old) == sorted(new)) if isinstance(old, list) else old == new
        if not same:
            out[qid] = {"template": t, "old": old, "new": new, "evidence": ev[:1500]}
        print(f"{qid}: {'CHANGED' if not same else 'same'}", flush=True)
    (ROOT / "eval/gold_corrections_v1_1.json").write_text(json.dumps(
        {"version": "1.1", "created_at": datetime.now(timezone.utc).isoformat(),
         "rule": "Drugs@FDA applications = union of openfda.generic_name and products.active_ingredients.name searches",
         "corrections": out}, indent=1, ensure_ascii=False))
    print(f"{len(out)} gold answers corrected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
