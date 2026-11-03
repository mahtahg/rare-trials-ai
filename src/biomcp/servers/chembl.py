from __future__ import annotations

from typing import Annotated

from pydantic import Field

from biomcp.servers import make_server, run, tool
from biomcp.sources import chembl

INSTRUCTIONS = (
    "ChEMBL. chembl_search_molecules resolves drug names/synonyms to ChEMBL IDs (exact matches ranked first; "
    "prefer the parent compound over salts). chembl_get_molecule gives max phase, first approval year and flags; "
    "chembl_mechanisms and chembl_indications give curated mechanism and indication evidence with references."
)


def register(server) -> None:
    @tool(server)
    async def chembl_search_molecules(
        query: Annotated[str, Field(description="Drug name or synonym")],
        limit: Annotated[int, Field(ge=1, le=50)] = 10,
    ) -> dict:
        """Find ChEMBL molecules by name/synonym."""
        return await chembl.search_molecules(query, limit)

    @tool(server)
    async def chembl_get_molecule(chembl_id: Annotated[str, Field(description="e.g. CHEMBL1431")]) -> dict:
        """Molecule card: max phase, first approval, type, oral, black-box warning, withdrawn, synonyms, ATC."""
        return await chembl.get_molecule(chembl_id)

    @tool(server)
    async def chembl_mechanisms(chembl_id: str) -> dict:
        """Curated mechanisms of action and target ChEMBL IDs for a molecule."""
        return await chembl.mechanisms(chembl_id)

    @tool(server)
    async def chembl_indications(chembl_id: str, limit: Annotated[int, Field(ge=1, le=1000)] = 100) -> dict:
        """Indications (MeSH/EFO) with the maximum phase reached for each, sorted by phase."""
        return await chembl.indications(chembl_id, limit)


server = make_server("biomcp-chembl", INSTRUCTIONS)
register(server)


def main() -> None:
    run(server)


if __name__ == "__main__":
    main()
