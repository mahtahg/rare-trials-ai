"""Open Targets Platform GraphQL API (https://platform-docs.opentargets.org/data-access/graphql-api).

Every response carries the Platform data release (e.g. 25.09) so results are
pinned to a release and can be time-sliced.
"""

from __future__ import annotations

from typing import Any

from biomcp.core.envelope import clip, envelope
from biomcp.core.http import HttpClient, SourceError, shared_client

SOURCE = "opentargets"
URL = "https://api.platform.opentargets.org/api/v4/graphql"

_release_cache: str | None = None


async def _gql(query: str, variables: dict[str, Any], client: HttpClient | None):
    c = client or shared_client()
    r = await c.post_json(SOURCE, URL, {"query": query, "variables": variables})
    if isinstance(r.body, dict) and r.body.get("errors"):
        raise SourceError(f"Open Targets GraphQL error: {r.body['errors'][0].get('message')}", url=URL)
    return r


async def release(client: HttpClient | None = None) -> str:
    global _release_cache
    if _release_cache is None:
        r = await _gql("{ meta { dataVersion { year month iteration } apiVersion { x y z } } }", {}, client)
        dv = r.body["data"]["meta"]["dataVersion"]
        _release_cache = f"{dv['year']}.{dv['month']}" + (f".{dv['iteration']}" if dv.get("iteration") else "")
    return _release_cache


async def _stamp(r, client):
    r.provenance.source_version = await release(client)
    return r.provenance


SEARCH_Q = """
query Search($q: String!, $entities: [String!], $size: Int!) {
  search(queryString: $q, entityNames: $entities, page: {index: 0, size: $size}) {
    total
    hits { id entity name description }
  }
}"""


async def search(query: str, entity: str | None = None, size: int = 10, client: HttpClient | None = None):
    entities = [entity] if entity else ["disease", "drug", "target"]
    for e in entities:
        if e not in {"disease", "drug", "target"}:
            raise ValueError("entity must be disease, drug or target")
    r = await _gql(SEARCH_Q, {"q": query, "entities": entities, "size": max(1, min(size, 50))}, client)
    s = r.body["data"]["search"]
    hits = [
        {"id": h["id"], "entity": h["entity"], "name": h["name"], "description": clip(h.get("description"), 300)}
        for h in s["hits"]
    ]
    return envelope(hits, await _stamp(r, client), total=s["total"])


DISEASE_TARGETS_Q = """
query DT($id: String!, $index: Int!, $size: Int!) {
  disease(efoId: $id) {
    id name
    associatedTargets(page: {index: $index, size: $size}) {
      count
      rows {
        score
        datatypeScores { id score }
        target { id approvedSymbol approvedName biotype }
      }
    }
  }
}"""


async def disease_targets(disease_id: str, size: int = 25, page: int = 0, client: HttpClient | None = None):
    r = await _gql(DISEASE_TARGETS_Q, {"id": disease_id, "index": page, "size": max(1, min(size, 100))}, client)
    d = r.body["data"]["disease"]
    if d is None:
        return {"data": None, "notes": [f"no disease with id {disease_id} in Open Targets"], "provenance": [(await _stamp(r, client)).to_dict()]}
    at = d["associatedTargets"]
    rows = [
        {
            "target_id": row["target"]["id"],
            "symbol": row["target"]["approvedSymbol"],
            "name": row["target"]["approvedName"],
            "overall_score": round(row["score"], 4),
            "datatype_scores": {x["id"]: round(x["score"], 4) for x in row.get("datatypeScores", [])},
        }
        for row in at["rows"]
    ]
    return envelope({"disease_id": d["id"], "disease_name": d["name"], "targets": rows}, await _stamp(r, client), total=at["count"])


DRUG_Q = """
query Drug($id: String!) {
  drug(chemblId: $id) {
    id name drugType maximumClinicalTrialPhase isApproved yearOfFirstApproval hasBeenWithdrawn
    synonyms tradeNames
    mechanismsOfAction { rows { mechanismOfAction actionType targets { id approvedSymbol } } }
    indications { count rows { maxPhaseForIndication disease { id name } } }
  }
}"""


async def drug(chembl_id: str, client: HttpClient | None = None):
    chembl_id = chembl_id.strip().upper()
    r = await _gql(DRUG_Q, {"id": chembl_id}, client)
    d = r.body["data"]["drug"]
    if d is None:
        return {"data": None, "notes": [f"no drug {chembl_id} in Open Targets"], "provenance": [(await _stamp(r, client)).to_dict()]}
    out = {
        "chembl_id": d["id"],
        "name": d["name"],
        "drug_type": d.get("drugType"),
        "max_phase": d.get("maximumClinicalTrialPhase"),
        "is_approved": d.get("isApproved"),
        "year_first_approval": d.get("yearOfFirstApproval"),
        "withdrawn": d.get("hasBeenWithdrawn"),
        "synonyms": (d.get("synonyms") or [])[:15],
        "trade_names": (d.get("tradeNames") or [])[:15],
        "mechanisms": [
            {
                "mechanism": m["mechanismOfAction"],
                "action_type": m.get("actionType"),
                "targets": [{"id": t["id"], "symbol": t["approvedSymbol"]} for t in m.get("targets") or []],
            }
            for m in (d.get("mechanismsOfAction") or {}).get("rows", [])
        ],
        "indications": sorted(
            (
                {"disease_id": i["disease"]["id"], "disease": i["disease"]["name"], "max_phase": i.get("maxPhaseForIndication")}
                for i in (d.get("indications") or {}).get("rows", [])
            ),
            key=lambda x: -(x["max_phase"] or 0),
        ),
    }
    return envelope(out, await _stamp(r, client), total=(d.get("indications") or {}).get("count"))


KNOWN_DRUGS_Q = """
query KD($id: String!, $size: Int!) {
  disease(efoId: $id) {
    id name
    knownDrugs(size: $size) {
      uniqueDrugs count
      rows { drug { id name isApproved } phase status mechanismOfAction ctIds targetId }
    }
  }
}"""


async def disease_drugs(disease_id: str, size: int = 50, client: HttpClient | None = None):
    """Drugs with clinical evidence for this disease (Open Targets 'known drugs' / ChEMBL evidence)."""
    r = await _gql(KNOWN_DRUGS_Q, {"id": disease_id, "size": max(1, min(size, 200))}, client)
    d = r.body["data"]["disease"]
    if d is None:
        return {"data": None, "notes": [f"no disease with id {disease_id}"], "provenance": [(await _stamp(r, client)).to_dict()]}
    kd = d.get("knownDrugs") or {}
    rows = [
        {
            "chembl_id": x["drug"]["id"],
            "drug": x["drug"]["name"],
            "drug_approved": x["drug"].get("isApproved"),
            "phase": x.get("phase"),
            "trial_status": x.get("status"),
            "mechanism": x.get("mechanismOfAction"),
            "target_id": x.get("targetId"),
            "nct_ids": x.get("ctIds") or [],
        }
        for x in kd.get("rows", [])
    ]
    return envelope(
        {"disease_id": d["id"], "disease_name": d["name"], "unique_drugs": kd.get("uniqueDrugs"), "rows": rows},
        await _stamp(r, client),
        total=kd.get("count"),
    )
