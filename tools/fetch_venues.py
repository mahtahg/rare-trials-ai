"""Fetch public venue pages (calls for papers, author instructions) as plain text for planning submissions.
Output: venues_out/<slug>.txt (uploaded as a workflow artifact, not committed)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx

URLS = [l.strip() for l in Path(sys.argv[1]).read_text().splitlines() if l.strip() and not l.startswith("#")]
out = Path("venues_out")
out.mkdir(exist_ok=True)
c = httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (venue planning; +github.com/mahtahg/rare-trials-ai)"})
for u in URLS:
    slug = re.sub(r"[^a-z0-9]+", "_", u.lower())[8:90]
    try:
        r = c.get(u)
        t = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", r.text)
        t = re.sub(r"(?s)<[^>]+>", " ", t)
        t = re.sub(r"&nbsp;|&#160;", " ", t)
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\n\s*\n+", "\n", t)
        (out / f"{slug}.txt").write_text(f"URL: {u}\nFINAL: {r.url}\nSTATUS: {r.status_code}\n\n{t[:60000]}")
        print(r.status_code, u)
    except Exception as e:  # noqa: BLE001
        print("ERR", u, e)
