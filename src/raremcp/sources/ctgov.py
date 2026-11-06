"""ClinicalTrials.gov API v2 (https://clinicaltrials.gov/data-api/api).

Returns compact, analysis-ready trial records. Fields that matter for trial
feasibility and stalling (overall status, why_stopped, anticipated vs actual
enrolment, dates, sponsor class, site count, uploaded protocol/SAP documents)
are always surfaced.
"""

from __future__ import annotations

import re
from typing import Any

from raremcp.core.envelope import clip, dig, envelope
from raremcp.core.http import HttpClient, SourceError, shared_client

SOURCE = "clinicaltrials.gov"
BASE = "https://clinicaltrials.gov/api/v2"
NCT_RE = re.compile(r"^NCT\d{8}$")

STATUSES = {
    "ACTIVE_NOT_RECRUITING", "COMPLETED", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING",
    "RECRUITING", "SUSPENDED", "TERMINATED", "WITHDRAWN", "AVAILABLE", "NO_LONGER_AVAILABLE",
    "TEMPORARILY_NOT_AVAILABLE", "APPROVED_FOR_MARKETING", "WITHHELD", "UNKNOWN",
}
PHASES = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"}
SPONSOR_CLASSES = {"NIH", "FED", "OTHER_GOV", "INDIV", "INDUSTRY", "NETWORK", "AMBIG", "OTHER", "UNKNOWN"}


def _doc_url(nct: str, filename: str) -> str:
    return f"https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/{filename}"


def summarize_study(study: dict[str, Any], *, include_eligibility: bool = False) -> dict[str, Any]:
    ps = study.get("protocolSection", {})
    nct = dig(ps, "identificationModule", "nctId")
    sm = ps.get("statusModule", {})
    dm = ps.get("designModule", {})
    locs = dig(ps, "contactsLocationsModule", "locations", default=[])
    countries = sorted({loc.get("country") for loc in locs if loc.get("country")})
    docs = []
    for d in dig(study, "documentSection", "largeDocumentModule", "largeDocs", default=[]):
        fn = d.get("filename")
        docs.append({
            "type": d.get("typeAbbrev"),
            "has_protocol": d.get("hasProtocol"),
            "has_sap": d.get("hasSap"),
            "has_icf": d.get("hasIcf"),
            "date": d.get("date"),
            "url": _doc_url(nct, fn) if (nct and fn) else None,
        })
    secondary_ids = [
        {"id": s.get("id"), "type": s.get("type"), "domain": s.get("domain")}
        for s in dig(ps, "identificationModule", "secondaryIdInfos", default=[])
    ]
    out: dict[str, Any] = {
        "nct_id": nct,
        "url": f"https://clinicaltrials.gov/study/{nct}" if nct else None,
        "brief_title": dig(ps, "identificationModule", "briefTitle"),
        "acronym": dig(ps, "identificationModule", "acronym"),
        "org_study_id": dig(ps, "identificationModule", "orgStudyIdInfo", "id"),
        "secondary_ids": secondary_ids,
        "overall_status": sm.get("overallStatus"),
        "last_known_status": sm.get("lastKnownStatus"),
        "why_stopped": sm.get("whyStopped"),
        "first_submitted": sm.get("studyFirstSubmitDate"),
        "start_date": dig(sm, "startDateStruct", "date"),
        "start_date_type": dig(sm, "startDateStruct", "type"),
        "primary_completion_date": dig(sm, "primaryCompletionDateStruct", "date"),
        "primary_completion_type": dig(sm, "primaryCompletionDateStruct", "type"),
        "completion_date": dig(sm, "completionDateStruct", "date"),
        "last_update_posted": dig(sm, "lastUpdatePostDateStruct", "date"),
        "study_type": dm.get("studyType"),
        "phases": dm.get("phases", []),
        "allocation": dig(dm, "designInfo", "allocation"),
        "masking": dig(dm, "designInfo", "maskingInfo", "masking"),
        "enrollment": dig(dm, "enrollmentInfo", "count"),
        "enrollment_type": dig(dm, "enrollmentInfo", "type"),  # ACTUAL | ESTIMATED
        "lead_sponsor": dig(ps, "sponsorCollaboratorsModule", "leadSponsor", "name"),
        "lead_sponsor_class": dig(ps, "sponsorCollaboratorsModule", "leadSponsor", "class"),
        "collaborators": [c.get("name") for c in dig(ps, "sponsorCollaboratorsModule", "collaborators", default=[])],
        "conditions": dig(ps, "conditionsModule", "conditions", default=[]),
        "condition_mesh": [m.get("term") for m in dig(study, "derivedSection", "conditionBrowseModule", "meshes", default=[])],
        "interventions": [
            {"type": i.get("type"), "name": i.get("name"), "other_names": i.get("otherNames", [])}
            for i in dig(ps, "armsInterventionsModule", "interventions", default=[])
        ],
        "intervention_mesh": [m.get("term") for m in dig(study, "derivedSection", "interventionBrowseModule", "meshes", default=[])],
        "primary_outcomes": [
            {"measure": clip(o.get("measure"), 300), "time_frame": clip(o.get("timeFrame"), 200)}
            for o in dig(ps, "outcomesModule", "primaryOutcomes", default=[])
        ],
        "n_sites": len(locs),
        "countries": countries,
        "has_results": study.get("hasResults", False),
        "documents": docs,
    }
    if include_eligibility:
        em = ps.get("eligibilityModule", {})
        out["eligibility"] = {
            "criteria": clip(em.get("eligibilityCriteria"), 6000),
            "sex": em.get("sex"),
            "minimum_age": em.get("minimumAge"),
            "maximum_age": em.get("maximumAge"),
            "healthy_volunteers": em.get("healthyVolunteers"),
        }
    return out


def build_query(
    *,
    condition: str | None = None,
    intervention: str | None = None,
    term: str | None = None,
    sponsor: str | None = None,
    statuses: list[str] | None = None,
    phases: list[str] | None = None,
    sponsor_class: str | None = None,
    study_type: str | None = None,
    start_from: str | None = None,
    start_to: str | None = None,
    has_sap: bool | None = None,
) -> dict[str, Any]:
    """Translate typed filters into ClinicalTrials.gov v2 query parameters."""
    params: dict[str, Any] = {}
    if condition:
        params["query.cond"] = condition
    if intervention:
        params["query.intr"] = intervention
    if sponsor:
        params["query.spons"] = sponsor
    if statuses:
        bad = [s for s in statuses if s.upper() not in STATUSES]
        if bad:
            raise ValueError(f"unknown status {bad}; valid: {sorted(STATUSES)}")
        params["filter.overallStatus"] = ",".join(s.upper() for s in statuses)
    adv: list[str] = []
    if term:
        adv.append(f"({term})")
    if phases:
        bad = [p for p in phases if p.upper() not in PHASES]
        if bad:
            raise ValueError(f"unknown phase {bad}; valid: {sorted(PHASES)}")
        adv.append("(" + " OR ".join(f"AREA[Phase]{p.upper()}" for p in phases) + ")")
    if sponsor_class:
        if sponsor_class.upper() not in SPONSOR_CLASSES:
            raise ValueError(f"unknown sponsor_class; valid: {sorted(SPONSOR_CLASSES)}")
        adv.append(f"AREA[LeadSponsorClass]{sponsor_class.upper()}")
    if study_type:
        adv.append(f"AREA[StudyType]{study_type.upper()}")
    if start_from or start_to:
        adv.append(f"AREA[StartDate]RANGE[{start_from or 'MIN'},{start_to or 'MAX'}]")
    if has_sap is not None:
        adv.append(f"AREA[LargeDocHasSAP]{'true' if has_sap else 'false'}")
    if adv:
        params["query.term"] = " AND ".join(adv)
    if not params:
        raise ValueError("give at least one search criterion")
    return params


async def version(client: HttpClient | None = None) -> dict[str, Any]:
    c = client or shared_client()
    r = await c.get_json(SOURCE, f"{BASE}/version")
    return envelope(r.body, r.provenance)


async def search_trials(
    *,
    page_size: int = 20,
    page_token: str | None = None,
    sort: str | None = None,
    client: HttpClient | None = None,
    **filters: Any,
) -> dict[str, Any]:
    c = client or shared_client()
    params = build_query(**filters)
    params.update({
        "pageSize": max(1, min(int(page_size), 100)),
        "countTotal": "true",
        "pageToken": page_token,
        "sort": sort,
    })
    r = await c.get_json(SOURCE, f"{BASE}/studies", params)
    studies = r.body.get("studies", [])
    return envelope(
        [summarize_study(s) for s in studies],
        r.provenance,
        total=r.body.get("totalCount"),
        next_page_token=r.body.get("nextPageToken"),
        notes=[f"query: {params}"],
    )


async def get_trial(nct_id: str, *, include_eligibility: bool = True, client: HttpClient | None = None) -> dict[str, Any]:
    nct_id = nct_id.strip().upper()
    if not NCT_RE.match(nct_id):
        raise ValueError(f"not an NCT id: {nct_id!r} (expected NCT + 8 digits)")
    c = client or shared_client()
    try:
        r = await c.get_json(SOURCE, f"{BASE}/studies/{nct_id}")
    except SourceError as e:
        if e.status == 404:
            return {"data": None, "notes": [f"{nct_id} does not exist on ClinicalTrials.gov"], "provenance": []}
        raise
    return envelope(summarize_study(r.body, include_eligibility=include_eligibility), r.provenance)


async def iterate_trials(*, max_records: int = 1000, client: HttpClient | None = None, **filters: Any):
    """Async generator over all matching trials (paginated). Used by pipelines, not exposed as a tool."""
    token = None
    n = 0
    while True:
        page = await search_trials(page_size=100, page_token=token, client=client, **filters)
        for rec in page["data"]:
            yield rec
            n += 1
            if n >= max_records:
                return
        token = page.get("next_page_token")
        if not token:
            return
