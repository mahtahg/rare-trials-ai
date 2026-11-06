"""Europe PMC REST API (https://europepmc.org/RestfulWebService)."""

from __future__ import annotations

import re

from raremcp.core.envelope import clip, envelope
from raremcp.core.http import HttpClient, shared_client

SOURCE = "europepmc"
BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def _rec(x: dict, abstract_chars: int) -> dict:
    pmid = x.get("pmid")
    pmcid = x.get("pmcid")
    return {
        "id": x.get("id"),
        "source": x.get("source"),
        "pmid": pmid,
        "pmcid": pmcid,
        "doi": x.get("doi"),
        "title": clip(x.get("title"), 400),
        "authors": clip(x.get("authorString"), 200),
        "journal": (x.get("journalInfo") or {}).get("journal", {}).get("title") or x.get("journalTitle"),
        "year": x.get("pubYear"),
        "publication_types": ((x.get("pubTypeList") or {}).get("pubType") or [])[:5],
        "is_open_access": x.get("isOpenAccess") == "Y",
        "cited_by": x.get("citedByCount"),
        "abstract": clip(x.get("abstractText"), abstract_chars) if abstract_chars else None,
        "url": f"https://europepmc.org/article/{x.get('source')}/{x.get('id')}",
    }


async def search(
    query: str,
    *,
    page_size: int = 10,
    cursor: str | None = None,
    abstract_chars: int = 600,
    from_year: int | None = None,
    to_year: int | None = None,
    client: HttpClient | None = None,
):
    q = query
    if from_year or to_year:
        q = f"({q}) AND PUB_YEAR:[{from_year or 1800} TO {to_year or 3000}]"
    c = client or shared_client()
    r = await c.get_json(
        SOURCE,
        f"{BASE}/search",
        {"query": q, "format": "json", "resultType": "core", "pageSize": max(1, min(page_size, 100)), "cursorMark": cursor or "*"},
    )
    res = (r.body.get("resultList") or {}).get("result", [])
    nxt = r.body.get("nextCursorMark")
    return envelope(
        [_rec(x, abstract_chars) for x in res],
        r.provenance,
        total=r.body.get("hitCount"),
        next_page_token=nxt if nxt and nxt != (cursor or "*") and res else None,
    )


async def get_article(identifier: str, client: HttpClient | None = None):
    ident = identifier.strip()
    if re.fullmatch(r"\d+", ident):
        q = f"EXT_ID:{ident} AND SRC:MED"
    elif re.fullmatch(r"PMC\d+", ident, re.IGNORECASE):
        q = f"PMCID:{ident.upper()}"
    elif ident.lower().startswith("10."):
        q = f'DOI:"{ident}"'
    else:
        raise ValueError("identifier must be a PMID, PMCID or DOI")
    out = await search(q, page_size=1, abstract_chars=6000, client=client)
    if not out["data"]:
        out["data"] = None
        out["notes"] = [f"{ident} not found in Europe PMC"]
    else:
        out["data"] = out["data"][0]
    out.pop("next_page_token", None)
    return out
