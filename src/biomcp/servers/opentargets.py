from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from biomcp.servers import READ_ONLY, make_server, run
from biomcp.sources import opentargets as ot

INSTRUCTIONS = (
    "Open Targets Platform. Resolve names to IDs with opentargets_search first (diseases use EFO/MONDO/Orphanet "
    "IDs such as MONDO_0010679; drugs use ChEMBL IDs; targets use Ensembl IDs). Then use "
    "opentargets_disease_targets (ranked target-disease association evidence), opentargets_disease_drugs "
    "(drugs with clinical evidence for the disease) and opentargets_drug (approval status, mechanisms, all "
    "indications). Results are stamped with the Platform release."
)


def register(server) -> None:
    @server.tool(annotations=READ_ONLY)
    async def opentargets_search(
        query: Annotated[str, Field(description="Name or synonym, e.g. 'Fabry disease', 'sirolimus', 'GLA'")],
        entity: Annotated[Literal["disease", "drug", "target"] | None, Field()] = None,
        size: Annotated[int, Field(ge=1, le=50)] = 10,
    ) -> dict:
        """Resolve a disease, drug or target name to Open Targets identifiers."""
        return await ot.search(query, entity, size)

    @server.tool(annotations=READ_ONLY)
    async def opentargets_disease_targets(
        disease_id: Annotated[str, Field(description="EFO/MONDO/Orphanet ID, e.g. MONDO_0010679 or Orphanet_98896")],
        size: Annotated[int, Field(ge=1, le=100)] = 25,
        page: Annotated[int, Field(ge=0)] = 0,
    ) -> dict:
        """Targets associated with a disease, ranked by overall association score, with per-datatype scores."""
        return await ot.disease_targets(disease_id, size, page)

    @server.tool(annotations=READ_ONLY)
    async def opentargets_disease_drugs(
        disease_id: Annotated[str, Field(description="EFO/MONDO/Orphanet disease ID")],
        size: Annotated[int, Field(ge=1, le=200)] = 50,
    ) -> dict:
        """Drugs with clinical-stage evidence for this disease (phase, trial status, mechanism, NCT IDs)."""
        return await ot.disease_drugs(disease_id, size)

    @server.tool(annotations=READ_ONLY)
    async def opentargets_drug(chembl_id: Annotated[str, Field(description="ChEMBL ID, e.g. CHEMBL1431")]) -> dict:
        """Drug profile: approval, first approval year, withdrawn flag, mechanisms with targets, all indications."""
        return await ot.drug(chembl_id)


server = make_server("biomcp-opentargets", INSTRUCTIONS)
register(server)


def main() -> None:
    run(server)


if __name__ == "__main__":
    main()
