"""ChEMBL REST API (https://www.ebi.ac.uk/chembl/api/data/docs)."""

from __future__ import annotations

import re
from typing import Any

from biomcp.core.envelope import dig, envelope
from biomcp.core.http import HttpClient, SourceError, shared_client

SOURCE = "chembl"
BASE = "https://www.ebi.ac.uk/chembl/api/data"
CHEMBL_RE = re.compile(r"^CHEMBL\d+$")

_db_version: str | None = None


async def db_version(client: HttpClient | None = None) -> str:
    global _db_version
    if _db_version is None:
        r = await (client or shared_client()).get_json(SOURCE, f"{BASE}/status.json")
        _db_version = r.body.get("chembl_db_version")
    return _db_version


async def _get(path: str, params: dict[str, Any] | None, client: HttpClient | None):
    c = client or shared_client()
    r = await c.get_json(SOURCE, f"{BASE}/{path}", params)
    r.provenance.source_version = await db_version(client)
    return r


def _mol_summary(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "chembl_id": m.get("molecule_chembl_id"),
        "pref_name": m.get("pref_name"),
        "max_phase": m.get("max_phase"),
        "first_approval": m.get("first_approval"),
        "molecule_type": m.get("molecule_type"),
        "oral": m.get("oral"),
        "prodrug": m.get("prodrug"),
        "black_box_warning": m.get("black_box_warning"),
        "withdrawn": m.get("withdrawn_flag"),
        "orphan": m.get("orphan"),
        "natural_product": m.get("natural_product"),
        "parent_chembl_id": dig(m, "molecule_hierarchy", "parent_chembl_id"),
        "synonyms": sorted({s.get("molecule_synonym") for s in m.get("molecule_synonyms") or [] if s.get("molecule_synonym")})[:20],
        "atc": [a for a in m.get("atc_classifications") or []],
        "url": f"https://www.ebi.ac.uk/chembl/compound_report_card/{m.get('molecule_chembl_id')}/",
    }


async def search_molecules(query: str, limit: int = 10, client: HttpClient | None = None):
    """Free-text search. Exact-name hits are ranked first."""
    r = await _get("molecule/search.json", {"q": query, "limit": max(1, min(limit, 50))}, client)
    mols = [_mol_summary(m) for m in r.body.get("molecules", [])]
    ql = query.strip().lower()
    mols.sort(key=lambda m: (0 if (m["pref_name"] or "").lower() == ql or ql in [s.lower() for s in m["synonyms"]] else 1))
    return envelope(mols, r.provenance, total=dig(r.body, "page_meta", "total_count"))


async def get_molecule(chembl_id: str, client: HttpClient | None = None):
    cid = chembl_id.strip().upper()
    if not CHEMBL_RE.match(cid):
        raise ValueError(f"not a ChEMBL id: {chembl_id!r}")
    try:
        r = await _get(f"molecule/{cid}.json", None, client)
    except SourceError as e:
        if e.status == 404:
            return {"data": None, "notes": [f"{cid} not found in ChEMBL"], "provenance": []}
        raise
    return envelope(_mol_summary(r.body), r.provenance)


async def mechanisms(chembl_id: str, client: HttpClient | None = None):
    cid = chembl_id.strip().upper()
    # ChEMBL files mechanisms against the parent compound; query by parent, fall back to the exact molecule
    r = await _get("mechanism.json", {"parent_molecule_chembl_id": cid, "limit": 100}, client)
    if not r.body.get("mechanisms"):
        r = await _get("mechanism.json", {"molecule_chembl_id": cid, "limit": 100}, client)
    rows = [
        {
            "mechanism": m.get("mechanism_of_action"),
            "action_type": m.get("action_type"),
            "target_chembl_id": m.get("target_chembl_id"),
            "direct_interaction": m.get("direct_interaction"),
            "refs": [{"type": x.get("ref_type"), "id": x.get("ref_id"), "url": x.get("ref_url")} for x in m.get("mechanism_refs") or []][:5],
        }
        for m in r.body.get("mechanisms", [])
    ]
    return envelope(rows, r.provenance, total=dig(r.body, "page_meta", "total_count"))


async def indications(chembl_id: str, limit: int = 100, client: HttpClient | None = None):
    cid = chembl_id.strip().upper()
    lim = max(1, min(limit, 1000))
    r = await _get("drug_indication.json", {"parent_molecule_chembl_id": cid, "limit": lim}, client)
    if not r.body.get("drug_indications"):
        r = await _get("drug_indication.json", {"molecule_chembl_id": cid, "limit": lim}, client)
    rows = [
        {
            "mesh_id": i.get("mesh_id"),
            "mesh_heading": i.get("mesh_heading"),
            "efo_id": i.get("efo_id"),
            "efo_term": i.get("efo_term"),
            "max_phase_for_indication": i.get("max_phase_for_ind"),
            "refs": [{"type": x.get("ref_type"), "id": x.get("ref_id")} for x in i.get("indication_refs") or []][:5],
        }
        for i in r.body.get("drug_indications", [])
    ]
    rows.sort(key=lambda x: -(float(x["max_phase_for_indication"] or 0)))
    return envelope(rows, r.provenance, total=dig(r.body, "page_meta", "total_count"))
