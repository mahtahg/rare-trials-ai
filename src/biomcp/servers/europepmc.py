from __future__ import annotations

from typing import Annotated

from pydantic import Field

from biomcp.servers import READ_ONLY, make_server, run
from biomcp.sources import europepmc

INSTRUCTIONS = (
    "Europe PMC literature search (PubMed + PMC + preprints). europepmc_search accepts Europe PMC query syntax "
    "(AND/OR, quotes, fields like TITLE:, ABSTRACT:, PUB_TYPE:\"review\"). europepmc_get_article fetches one "
    "record with full abstract by PMID, PMCID or DOI. Cite PMIDs/DOIs exactly as returned."
)


def register(server) -> None:
    @server.tool(annotations=READ_ONLY)
    async def europepmc_search(
        query: Annotated[str, Field(description="Europe PMC query, e.g. 'sirolimus AND \"lymphangioleiomyomatosis\"'")],
        page_size: Annotated[int, Field(ge=1, le=100)] = 10,
        cursor: Annotated[str | None, Field(description="next_page_token from a previous call")] = None,
        from_year: int | None = None,
        to_year: int | None = None,
        abstract_chars: Annotated[int, Field(ge=0, le=6000)] = 600,
    ) -> dict:
        """Search the literature; returns titles, IDs, year, journal, citation count and abstract snippets."""
        return await europepmc.search(
            query, page_size=page_size, cursor=cursor, from_year=from_year, to_year=to_year, abstract_chars=abstract_chars
        )

    @server.tool(annotations=READ_ONLY)
    async def europepmc_get_article(identifier: Annotated[str, Field(description="PMID, PMCID or DOI")]) -> dict:
        """One article with full abstract."""
        return await europepmc.get_article(identifier)


server = make_server("biomcp-europepmc", INSTRUCTIONS)
register(server)


def main() -> None:
    run(server)


if __name__ == "__main__":
    main()
