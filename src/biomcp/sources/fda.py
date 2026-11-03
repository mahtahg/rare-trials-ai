"""openFDA (Drugs@FDA + SPL labels) and the derived 'generic availability' signal.

Off-patent proxy (US): a drug is treated as generically available when at least
one ANDA for the same active ingredient has a currently marketed product
(marketing_status Prescription / Over-the-counter). This is a transparent,
reproducible proxy, not a patent search; tool output says so.
"""

from __future__ import annotations

import re
from typing import Any

from biomcp.core.envelope import clip, envelope
from biomcp.core.http import HttpClient, SourceError, shared_client

SOURCE = "openfda"
BASE = "https://api.fda.gov/drug"
MARKETED = {"Prescription", "Over-the-counter"}


def _q(field: str, value: str) -> str:
    v = value.replace('"', "").strip()
    return f'{field}:"{v}"'


async def _search(endpoint: str, search: str, limit: int, skip: int, client: HttpClient | None):
    c = client or shared_client()
    try:
        r = await c.get_json(SOURCE, f"{BASE}/{endpoint}.json", {"search": search, "limit": limit, "skip": skip or None})
    except SourceError as e:
        if e.status == 404:  # openFDA returns 404 for zero matches
            return None
        raise
    r.provenance.source_version = (r.body.get("meta") or {}).get("last_updated")
    return r


async def applications(ingredient: str, *, max_records: int = 300, client: HttpClient | None = None):
    """All Drugs@FDA applications whose openFDA generic_name matches the ingredient."""
    search = _q("openfda.generic_name", ingredient)
    rows, provs, skip, total = [], [], 0, None
    while True:
        r = await _search("drugsfda", search, 100, skip, client)
        if r is None:
            break
        provs.append(r.provenance)
        total = (r.body.get("meta") or {}).get("results", {}).get("total")
        for a in r.body.get("results", []):
            prods = a.get("products") or []
            rows.append({
                "application_number": a.get("application_number"),
                "kind": re.match(r"[A-Z]*", a.get("application_number") or "").group(),
                "sponsor": a.get("sponsor_name"),
                "products": [
                    {
                        "brand_name": p.get("brand_name"),
                        "dosage_form": p.get("dosage_form"),
                        "route": p.get("route"),
                        "marketing_status": p.get("marketing_status"),
                        "te_code": p.get("te_code"),
                        "active_ingredients": [f"{i.get('name')} {i.get('strength')}" for i in p.get("active_ingredients") or []],
                    }
                    for p in prods
                ],
                "first_approval": min(
                    (s.get("submission_status_date") for s in a.get("submissions") or [] if s.get("submission_type") == "ORIG" and s.get("submission_status") == "AP"),
                    default=None,
                ),
            })
        skip += 100
        if total is None or skip >= min(total, max_records):
            break
    return rows, provs, total


async def generic_availability(ingredient: str, client: HttpClient | None = None) -> dict[str, Any]:
    rows, provs, total = await applications(ingredient, client=client)
    if not rows:
        return {"data": None, "notes": [f"no Drugs@FDA applications match generic_name '{ingredient}'"], "provenance": [p.to_dict() for p in provs]}
    def marketed(a):
        return any(p["marketing_status"] in MARKETED for p in a["products"])
    andas = [a for a in rows if a["kind"] == "ANDA"]
    ndas = [a for a in rows if a["kind"] == "NDA"]
    blas = [a for a in rows if a["kind"] == "BLA"]
    data = {
        "ingredient_query": ingredient,
        "n_applications": len(rows),
        "n_nda": len(ndas),
        "n_anda": len(andas),
        "n_bla": len(blas),
        "n_anda_marketed": sum(marketed(a) for a in andas),
        "generic_available_us": any(marketed(a) for a in andas),
        "earliest_nda_approval": min((a["first_approval"] for a in ndas if a["first_approval"]), default=None),
        "anda_sponsors_marketed": sorted({a["sponsor"] for a in andas if marketed(a)})[:25],
    }
    notes = [
        (
            "generic_available_us = at least one ANDA with a currently marketed product (Drugs@FDA). "
            "Proxy for off-patent status in the US; does not check patents/exclusivity directly or other jurisdictions."
        ),
    ]
    if total and total > len(rows):
        notes.append(f"only first {len(rows)} of {total} applications inspected")
    return envelope(data, provs, notes=notes)


async def label(ingredient: str, client: HttpClient | None = None) -> dict[str, Any]:
    """Most recent SPL label for the ingredient: indications, boxed warning, contraindications."""
    r = await _search("label", _q("openfda.generic_name", ingredient), 5, 0, client)
    if r is None:
        return {"data": None, "notes": [f"no SPL label for generic_name '{ingredient}'"], "provenance": []}
    results = sorted(r.body.get("results", []), key=lambda x: x.get("effective_time", ""), reverse=True)
    lab = results[0]
    of = lab.get("openfda") or {}

    def sec(k: str, n: int = 2500):
        v = lab.get(k)
        return clip(" ".join(v) if isinstance(v, list) else v, n)

    data = {
        "set_id": lab.get("set_id"),
        "effective_time": lab.get("effective_time"),
        "brand_name": of.get("brand_name"),
        "generic_name": of.get("generic_name"),
        "manufacturer": of.get("manufacturer_name"),
        "rxcui": of.get("rxcui"),
        "indications_and_usage": sec("indications_and_usage", 6000),
        "boxed_warning": sec("boxed_warning", 1500),
        "contraindications": sec("contraindications", 1500),
        "pregnancy": sec("pregnancy", 800) or sec("pregnancy_or_breast_feeding", 800),
        "pediatric_use": sec("pediatric_use", 1000),
        "dailymed_url": f"https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid={lab.get('set_id')}" if lab.get("set_id") else None,
    }
    return envelope(data, r.provenance, notes=[f"{len(results)} label(s) matched; newest shown"])
