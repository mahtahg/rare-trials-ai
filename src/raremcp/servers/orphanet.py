from __future__ import annotations

from typing import Annotated

from pydantic import Field

from raremcp.servers import make_server, run, tool
from raremcp.sources import orphanet

INSTRUCTIONS = (
    "Orphanet (Orphadata API). orphanet_lookup gives an ORPHA entity's name, synonyms, definition and cross-references "
    "(MONDO, OMIM, MeSH, ICD-10/11, GARD). orphanet_prevalence gives prevalence estimates and an explicit judgement of "
    "whether the disease is rare under the EU definition (<=5 per 10,000), with the basis for that judgement."
)


def register(server) -> None:
    @tool(server)
    async def orphanet_lookup(
        query: Annotated[str, Field(description="ORPHA code (e.g. 98896 or ORPHA:98896) or exact Orphanet preferred name")],
    ) -> dict:
        """Orphanet entity: preferred name, synonyms, definition, cross-references to MONDO/OMIM/MeSH/ICD."""
        return await orphanet.lookup(query)

    @tool(server)
    async def orphanet_prevalence(orpha_code: Annotated[str, Field(description="ORPHA code, e.g. 98896")]) -> dict:
        """Prevalence records and EU rarity judgement (<=5/10,000) with its basis."""
        return await orphanet.prevalence(orpha_code)


server = make_server("raremcp-orphanet", INSTRUCTIONS)
register(server)


def main() -> None:
    run(server)


if __name__ == "__main__":
    main()
