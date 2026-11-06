from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from raremcp.servers import make_server, run, tool
from raremcp.sources import ctgov

Status = Literal[
    "ACTIVE_NOT_RECRUITING", "COMPLETED", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING", "RECRUITING",
    "SUSPENDED", "TERMINATED", "WITHDRAWN", "UNKNOWN",
]
Phase = Literal["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"]
SponsorClass = Literal["NIH", "FED", "OTHER_GOV", "INDIV", "INDUSTRY", "NETWORK", "OTHER", "UNKNOWN"]

INSTRUCTIONS = (
    "ClinicalTrials.gov registry (API v2). Use ctgov_search_trials to find trials by condition, intervention, "
    "status, phase, sponsor class and start-date window; use ctgov_get_trial for one NCT record including "
    "eligibility criteria, why_stopped, enrolment (ACTUAL vs ESTIMATED), site count and links to uploaded "
    "protocol/SAP PDFs. Sponsor class OTHER usually means academic/investigator-led."
)


def register(server) -> None:
    @tool(server)
    async def ctgov_search_trials(
        condition: Annotated[str | None, Field(description="Disease/condition text, e.g. 'Duchenne muscular dystrophy'")] = None,
        intervention: Annotated[str | None, Field(description="Drug or intervention name, e.g. 'sirolimus'")] = None,
        term: Annotated[str | None, Field(description="Extra ClinicalTrials.gov query (Essie syntax allowed)")] = None,
        sponsor: Annotated[str | None, Field(description="Sponsor/collaborator name")] = None,
        statuses: Annotated[list[Status] | None, Field(description="Overall statuses to include")] = None,
        phases: Annotated[list[Phase] | None, Field(description="Phases to include (OR)")] = None,
        sponsor_class: Annotated[SponsorClass | None, Field(description="Lead sponsor class")] = None,
        study_type: Annotated[Literal["INTERVENTIONAL", "OBSERVATIONAL", "EXPANDED_ACCESS"] | None, Field()] = None,
        start_from: Annotated[str | None, Field(description="Earliest start date YYYY-MM-DD")] = None,
        start_to: Annotated[str | None, Field(description="Latest start date YYYY-MM-DD")] = None,
        has_sap: Annotated[bool | None, Field(description="Only trials with an uploaded statistical analysis plan")] = None,
        page_size: Annotated[int, Field(ge=1, le=100)] = 20,
        page_token: Annotated[str | None, Field(description="next_page_token from a previous call")] = None,
    ) -> dict:
        """Search ClinicalTrials.gov. Returns compact trial summaries plus total count and a page token."""
        return await ctgov.search_trials(
            condition=condition, intervention=intervention, term=term, sponsor=sponsor, statuses=statuses,
            phases=phases, sponsor_class=sponsor_class, study_type=study_type, start_from=start_from,
            start_to=start_to, has_sap=has_sap, page_size=page_size, page_token=page_token,
        )

    @tool(server)
    async def ctgov_get_trial(
        nct_id: Annotated[str, Field(description="NCT identifier, e.g. NCT01908426")],
        include_eligibility: bool = True,
    ) -> dict:
        """Full summary of one registered trial, including eligibility text and protocol/SAP document links."""
        return await ctgov.get_trial(nct_id, include_eligibility=include_eligibility)

    @tool(server)
    async def ctgov_data_version() -> dict:
        """ClinicalTrials.gov API version and data timestamp (cite this when reporting counts)."""
        return await ctgov.version()


server = make_server("raremcp-ctgov", INSTRUCTIONS)
register(server)


def main() -> None:
    run(server)


if __name__ == "__main__":
    main()
