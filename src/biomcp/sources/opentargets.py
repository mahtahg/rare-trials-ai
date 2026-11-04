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
    id name drugType maximumClinicalStage synonyms { label source } tradeNames { label source } description
    drugWarnings { warningType toxicityClass country year description }
    mechanismsOfAction { rows { mechanismOfAction actionType targets { id approvedSymbol } } }
    indications { count rows { maxClinicalStage disease { id name } } }
  }
}"""

# Open Targets clinical stages, ordered (values outside this list sort first)
STAGE_ORDER = ["PRECLINICAL", "EARLY_PHASE_1", "PHASE_1", "PHASE_1_2", "PHASE_2", "PHASE_2_3", "PHASE_3", "PHASE_4", "APPROVAL"]


def stage_rank(stage: str | None) -> int:
    s = (stage or "").upper()
    return STAGE_ORDER.index(s) if s in STAGE_ORDER else -1


async def drug(chembl_id: str, client: HttpClient | None = None):
    chembl_id = chembl_id.strip().upper()
    r = await _gql(DRUG_Q, {"id": chembl_id}, client)
    d = r.body["data"]["drug"]
    if d is None:
        return {"data": None, "notes": [f"no drug {chembl_id} in Open Targets"], "provenance": [(await _stamp(r, client)).to_dict()]}
    warnings = d.get("drugWarnings") or []
    out = {
        "chembl_id": d["id"],
        "name": d["name"],
        "drug_type": d.get("drugType"),
        "max_clinical_stage": d.get("maximumClinicalStage"),
        "is_approved": (d.get("maximumClinicalStage") or "").upper() in {"APPROVAL", "PHASE_4"},
        "withdrawn_or_warned": [
            {"type": w.get("warningType"), "class": w.get("toxicityClass"), "country": w.get("country"), "year": w.get("year")}
            for w in warnings
        ][:10],
        "description": clip(d.get("description"), 600),
        "synonyms": sorted({x["label"] for x in d.get("synonyms") or [] if x.get("label")})[:15],
        "trade_names": sorted({x["label"] for x in d.get("tradeNames") or [] if x.get("label")})[:15],
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
                {"disease_id": i["disease"]["id"], "disease": i["disease"]["name"], "max_clinical_stage": i.get("maxClinicalStage")}
                for i in (d.get("indications") or {}).get("rows", [])
            ),
            key=lambda x: -stage_rank(x["max_clinical_stage"]),
        ),
    }
    return envelope(out, await _stamp(r, client), total=(d.get("indications") or {}).get("count"),
                    notes=["is_approved = maximumClinicalStage is APPROVAL or PHASE_4 (Open Targets)."])


DISEASE_DRUGS_Q = """
query DD($id: String!) {
  disease(efoId: $id) {
    id name
    drugAndClinicalCandidates {
      count
      rows {
        maxClinicalStage
        drug { id name drugType maximumClinicalStage mechanismsOfAction { rows { actionType targets { approvedSymbol } } } }
        clinicalReports { id source trialPhase trialOverallStatus trialWhyStopped trialStopReasonCategories year url }
      }
    }
  }
}"""


async def disease_drugs(disease_id: str, size: int = 50, min_stage: str | None = None, client: HttpClient | None = None):
    """Drugs and clinical candidates for a disease, with the trials (clinical reports) behind each."""
    r = await _gql(DISEASE_DRUGS_Q, {"id": disease_id}, client)
    d = r.body["data"]["disease"]
    if d is None:
        return {"data": None, "notes": [f"no disease with id {disease_id}"], "provenance": [(await _stamp(r, client)).to_dict()]}
    dc = d.get("drugAndClinicalCandidates") or {}
    rows = []
    for x in dc.get("rows", []):
        if min_stage and stage_rank(x.get("maxClinicalStage")) < stage_rank(min_stage):
            continue
        reps = x.get("clinicalReports") or []
        dr = x.get("drug") or {}
        rows.append({
            "chembl_id": dr.get("id"),
            "drug": dr.get("name"),
            "drug_type": dr.get("drugType"),
            "max_stage_for_disease": x.get("maxClinicalStage"),
            "drug_max_stage_any_indication": dr.get("maximumClinicalStage"),
            "targets": sorted({t["approvedSymbol"] for m in (dr.get("mechanismsOfAction") or {}).get("rows", [])
                               for t in m.get("targets") or []}),
            "n_reports": len(reps),
            "trials": [
                {"id": (c.get("id") or "").upper() if (c.get("id") or "").lower().startswith("nct") else c.get("id"), "source": c.get("source"), "phase": c.get("trialPhase"), "status": c.get("trialOverallStatus"),
                 "why_stopped": clip(c.get("trialWhyStopped"), 200), "stop_categories": c.get("trialStopReasonCategories"),
                 "year": c.get("year")}
                for c in reps[:8]
            ],
        })
    rows.sort(key=lambda x: (-stage_rank(x["max_stage_for_disease"]), x["drug"] or ""))
    total = len(rows)
    rows = rows[: max(1, min(size, 200))]
    notes = [f"{total} drugs after filtering" + (f" (min_stage={min_stage})" if min_stage else "") + f"; showing {len(rows)}"]
    return envelope({"disease_id": d["id"], "disease_name": d["name"], "rows": rows}, await _stamp(r, client),
                    total=dc.get("count"), notes=notes)
