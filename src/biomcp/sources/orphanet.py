"""Orphanet via the Orphadata API (https://api.orphadata.com, CC-BY-4.0).

Adds a transparent 'rare under the EU definition' judgement (point prevalence
<= 5 per 10,000) derived from Orphanet's validated prevalence classes.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from biomcp.core.envelope import clip, envelope
from biomcp.core.http import HttpClient, SourceError, shared_client

SOURCE = "orphadata"
BASE = "https://api.orphadata.com"

# Orphanet prevalence classes, ordered, with upper bound per 10,000
CLASS_UPPER_PER_10K = {
    "<1 / 1 000 000": 0.01,
    "1-9 / 1 000 000": 0.09,
    "1-9 / 100 000": 0.9,
    "1-5 / 10 000": 5.0,
    "6-9 / 10 000": 9.0,
    ">1 / 1000": float("inf"),
}
GEO_PREFERENCE = ["Worldwide", "Europe"]


async def _get(path: str, client: HttpClient | None):
    c = client or shared_client()
    try:
        r = await c.get_json(SOURCE, f"{BASE}/{path}", {"lang": "en"})
    except SourceError as e:
        if e.status == 404:
            return None
        raise
    res = (r.body.get("data") or {}).get("results")
    if isinstance(res, dict):
        r.provenance.source_version = res.get("Date")
    return r


def _disorder(res: dict[str, Any]) -> dict[str, Any]:
    xrefs: dict[str, list[dict[str, str]]] = {}
    for e in res.get("ExternalReference") or []:
        xrefs.setdefault(e.get("Source"), []).append({
            "id": e.get("Reference"),
            "relation": (e.get("DisorderMappingRelation") or "").split(" (")[0],  # E, NTBT, BTNT, ...
            "validated": e.get("DisorderMappingValidationStatus") == "Validated",
        })
    summ = res.get("SummaryInformation") or []
    definition = summ[0].get("Definition") if summ and isinstance(summ[0], dict) else None
    code = res.get("ORPHAcode")
    return {
        "orpha_code": code,
        "orpha_id": f"ORPHA:{code}" if code else None,
        "name": res.get("Preferred term"),
        "synonyms": res.get("Synonym") or [],
        "group": res.get("DisorderGroup"),
        "typology": res.get("Typology"),
        "definition": clip(definition, 1200),
        "xrefs": xrefs,
        "url": f"https://www.orpha.net/en/disease/detail/{code}" if code else None,
    }


async def lookup(query: str, client: HttpClient | None = None) -> dict[str, Any]:
    """Look up by ORPHA code ('98896', 'ORPHA:98896') or exact preferred name."""
    q = query.strip()
    code = q.upper().removeprefix("ORPHA:").removeprefix("ORPHANET_").strip()
    if code.isdigit():
        r = await _get(f"rd-cross-referencing/orphacodes/{code}", client)
    else:
        r = await _get(f"rd-cross-referencing/orphacodes/names/{quote(q)}", client)
    if r is None or not (r.body.get("data") or {}).get("results"):
        return {"data": None, "notes": [(f"'{q}' not found in Orphanet (name lookups must match the preferred term exactly; "
                                          "resolve names via opentargets_search and use the Orphanet/ORPHA id)")], "provenance": []}
    return envelope(_disorder(r.body["data"]["results"]), r.provenance)


def classify_rarity(prevalences: list[dict[str, Any]]) -> dict[str, Any]:
    """EU rarity (<= 5/10,000) from validated point-prevalence classes; transparent rule, returned with its basis."""
    pts = [p for p in prevalences if p.get("PrevalenceType") == "Point prevalence" and p.get("PrevalenceClass") in CLASS_UPPER_PER_10K]
    validated = [p for p in pts if p.get("PrevalenceValidationStatus") == "Validated"] or pts
    chosen = None
    for geo in GEO_PREFERENCE:
        cand = [p for p in validated if p.get("PrevalenceGeographic") == geo]
        if cand:
            chosen = max(cand, key=lambda p: CLASS_UPPER_PER_10K[p["PrevalenceClass"]])
            break
    if chosen is None and validated:
        chosen = max(validated, key=lambda p: CLASS_UPPER_PER_10K[p["PrevalenceClass"]])  # conservative: highest
    if chosen is None:
        # No point prevalence: Orphanet lists the entity, so it is presumed rare but flagged.
        return {"rare_eu": True, "basis": "no point-prevalence class; listed in Orphanet (presumed rare)", "confidence": "low"}
    rare = CLASS_UPPER_PER_10K[chosen["PrevalenceClass"]] <= 5.0
    return {
        "rare_eu": rare,
        "basis": f"point prevalence {chosen['PrevalenceClass']} ({chosen.get('PrevalenceGeographic')}, {chosen.get('PrevalenceValidationStatus')})",
        "confidence": "high" if chosen.get("PrevalenceGeographic") in GEO_PREFERENCE else "medium",
    }


async def prevalence(orpha_code: str, client: HttpClient | None = None) -> dict[str, Any]:
    code = orpha_code.strip().upper().removeprefix("ORPHA:").removeprefix("ORPHANET_")
    if not code.isdigit():
        raise ValueError("orpha_code must be numeric, e.g. 98896 or ORPHA:98896")
    r = await _get(f"rd-epidemiology/orphacodes/{code}", client)
    if r is None or not (r.body.get("data") or {}).get("results"):
        return {"data": None, "notes": [f"no epidemiology record for ORPHA:{code}"], "provenance": []}
    res = r.body["data"]["results"]
    prevs = res.get("Prevalence") or []
    rows = [
        {
            "type": p.get("PrevalenceType"),
            "class": p.get("PrevalenceClass"),
            "mean_value": p.get("ValMoy"),
            "geography": p.get("PrevalenceGeographic"),
            "qualification": p.get("PrevalenceQualification"),
            "validated": p.get("PrevalenceValidationStatus") == "Validated",
            "source": p.get("Source"),
        }
        for p in prevs
    ]
    data = {"orpha_code": int(code), "name": res.get("Preferred term"), "prevalence": rows, "eu_rarity": classify_rarity(prevs)}
    return envelope(data, r.provenance, notes=[(
        "eu_rarity applies the EU definition (<=5 per 10,000) to the highest validated point-prevalence class, "
        "preferring Worldwide then Europe estimates. Values for case/family counts are not prevalence."
    )])
