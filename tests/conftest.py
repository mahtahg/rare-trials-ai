import os
from pathlib import Path

import pytest

from biomcp.core.http import HttpClient, set_shared_client
from biomcp.sources import chembl, opentargets

CASSETTES = Path(__file__).parent / "cassettes"


@pytest.fixture(autouse=True)
async def client():
    """Live tests record in CI (BIOMCP_CASSETTE_MODE=record) and replay offline (default)."""
    mode = os.getenv("BIOMCP_CASSETTE_MODE", "replay")
    c = HttpClient(cassette_dir=CASSETTES, cassette_mode=mode)
    set_shared_client(c)
    # module-level release caches must not leak between modes
    opentargets._release_cache = None
    chembl._db_version = None
    yield c
    await c.aclose()
    set_shared_client(None)
