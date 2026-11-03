from __future__ import annotations

from typing import Annotated

from pydantic import Field

from biomcp.servers import make_server, run, tool
from biomcp.sources import fda

INSTRUCTIONS = (
    "US FDA via openFDA. fda_generic_availability tells you whether a medicine is generically available in the "
    "US (marketed ANDA), the usual practical test for 'off-patent' in repurposing; it is a proxy, see notes. "
    "fda_label returns the current label sections (indications, boxed warning, contraindications, pediatric use). "
    "Query by active ingredient (generic) name, e.g. 'sirolimus', 'metformin hydrochloride'."
)


def register(server) -> None:
    @tool(server)
    async def fda_generic_availability(ingredient: Annotated[str, Field(description="Active ingredient / generic name")]) -> dict:
        """Counts of NDA/ANDA/BLA applications and whether a marketed generic (ANDA) exists in the US."""
        return await fda.generic_availability(ingredient)

    @tool(server)
    async def fda_label(ingredient: Annotated[str, Field(description="Active ingredient / generic name")]) -> dict:
        """Newest FDA label (SPL): indications, boxed warning, contraindications, pregnancy, pediatric use."""
        return await fda.label(ingredient)


server = make_server("biomcp-fda", INSTRUCTIONS)
register(server)


def main() -> None:
    run(server)


if __name__ == "__main__":
    main()
