"""Shared async HTTP client for every biomcp source.

Design goals
- Polite: per-host minimum interval between requests, honest User-Agent.
- Robust: bounded retries with exponential backoff on 429/5xx/transport errors,
  honouring Retry-After.
- Reproducible: every response can be recorded to / replayed from a cassette
  directory (BIOMCP_CASSETTE_MODE = off | record | replay | auto), so tests and
  eval runs can be repeated byte-for-byte without network access.
- Traceable: every call returns a Provenance record (URL, params, status,
  retrieval time, content hash) that tools attach to their output.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

from biomcp import __version__

USER_AGENT = f"biomcp/{__version__} (+https://github.com/mahtahg/rare-trials-ai)"
RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}


class SourceError(RuntimeError):
    """A data source returned an error the caller should see verbatim."""

    def __init__(self, message: str, *, status: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status = status
        self.url = url


class CassetteMiss(SourceError):
    """Replay mode was requested but no recorded response exists."""


@dataclass
class Provenance:
    source: str
    url: str
    method: str
    status: int
    retrieved_at: str
    sha256: str
    from_cassette: bool = False
    source_version: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not d["extra"]:
            d.pop("extra")
        return d


@dataclass
class Response:
    status: int
    body: Any  # parsed JSON, or text when not JSON
    text: str
    provenance: Provenance


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical_url(url: str, params: dict[str, Any] | None) -> str:
    if not params:
        return url
    clean = {k: v for k, v in sorted(params.items()) if v is not None}
    return f"{url}?{urlencode(clean, doseq=True)}"


def _cassette_key(method: str, full_url: str, json_body: Any) -> str:
    h = hashlib.sha256()
    h.update(method.upper().encode())
    h.update(b"\n")
    h.update(full_url.encode())
    if json_body is not None:
        h.update(b"\n")
        h.update(json.dumps(json_body, sort_keys=True, separators=(",", ":")).encode())
    return h.hexdigest()[:24]


class HttpClient:
    """One shared client per process; sources call `get_json` / `post_json`."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        max_retries: int = 4,
        min_interval: dict[str, float] | None = None,
        cassette_dir: str | os.PathLike[str] | None = None,
        cassette_mode: str | None = None,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        # seconds between requests to the same host (conservative defaults)
        self._min_interval = {
            "clinicaltrials.gov": 0.35,
            "api.platform.opentargets.org": 0.2,
            "www.ebi.ac.uk": 0.2,
            "api.fda.gov": 0.3,  # 240 req/min without a key
            "api.orphadata.com": 0.3,
        } | (min_interval or {})
        self._last_call: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._client: httpx.AsyncClient | None = None
        self.cassette_mode = (cassette_mode or os.getenv("BIOMCP_CASSETTE_MODE", "off")).lower()
        if self.cassette_mode not in {"off", "record", "replay", "auto"}:
            raise ValueError(f"bad BIOMCP_CASSETTE_MODE: {self.cassette_mode}")
        self.cassette_dir = Path(cassette_dir or os.getenv("BIOMCP_CASSETTE_DIR", "tests/cassettes"))

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                follow_redirects=True,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _throttle(self, host: str) -> None:
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            gap = self._min_interval.get(host, 0.1)
            wait = self._last_call.get(host, 0.0) + gap - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call[host] = time.monotonic()

    # ---------------------------------------------------------------- cassettes
    def _cassette_path(self, source: str, key: str) -> Path:
        return self.cassette_dir / source / f"{key}.json"

    def _load_cassette(self, source: str, key: str) -> dict[str, Any] | None:
        p = self._cassette_path(source, key)
        if p.exists():
            return json.loads(p.read_text())
        return None

    def _save_cassette(self, source: str, key: str, record: dict[str, Any]) -> None:
        p = self._cassette_path(source, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False))

    # ------------------------------------------------------------------ request
    async def request(
        self,
        source: str,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        ok_statuses: frozenset[int] = frozenset({200}),
    ) -> Response:
        full_url = _canonical_url(url, params)
        key = _cassette_key(method, full_url, json_body)

        if self.cassette_mode in {"replay", "auto"}:
            rec = self._load_cassette(source, key)
            if rec is not None:
                return self._from_record(source, rec, from_cassette=True)
            if self.cassette_mode == "replay":
                raise CassetteMiss(f"no cassette for {method} {full_url}", url=full_url)

        status, text = await self._fetch(method, url, params, json_body, headers)
        rec = {
            "method": method.upper(),
            "url": full_url,
            "json_body": json_body,
            "status": status,
            "retrieved_at": _now(),
            "text": text,
        }
        if self.cassette_mode in {"record", "auto"} and status in ok_statuses | {404}:
            self._save_cassette(source, key, rec)
        resp = self._from_record(source, rec, from_cassette=False)
        if status not in ok_statuses:
            msg = text[:500] if isinstance(text, str) else str(text)[:500]
            raise SourceError(f"{source} HTTP {status}: {msg}", status=status, url=full_url)
        return resp

    def _from_record(self, source: str, rec: dict[str, Any], *, from_cassette: bool) -> Response:
        text = rec["text"]
        try:
            body: Any = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            body = text
        prov = Provenance(
            source=source,
            url=rec["url"],
            method=rec["method"],
            status=rec["status"],
            retrieved_at=rec["retrieved_at"],
            sha256=hashlib.sha256(text.encode()).hexdigest()[:16],
            from_cassette=from_cassette,
        )
        if from_cassette and rec["status"] != 200:
            raise SourceError(f"{source} HTTP {rec['status']} (recorded)", status=rec["status"], url=rec["url"])
        return Response(status=rec["status"], body=body, text=text, provenance=prov)

    async def _fetch(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        json_body: Any,
        headers: dict[str, str] | None,
    ) -> tuple[int, str]:
        client = await self._get_client()
        host = urlparse(url).hostname or ""
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            await self._throttle(host)
            try:
                r = await client.request(method, url, params=clean_params, json=json_body, headers=headers)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                await asyncio.sleep(min(30, (2**attempt) + random.random()))
                continue
            if r.status_code in RETRY_STATUS and attempt < self._max_retries:
                ra = r.headers.get("Retry-After")
                delay = float(ra) if ra and ra.isdigit() else (2**attempt) + random.random()
                await asyncio.sleep(min(60, delay))
                continue
            return r.status_code, r.text
        raise SourceError(f"transport failure after retries: {last_exc!r}", url=url)

    async def get_json(self, source: str, url: str, params: dict[str, Any] | None = None, **kw: Any) -> Response:
        return await self.request(source, "GET", url, params=params, **kw)

    async def post_json(self, source: str, url: str, json_body: Any, **kw: Any) -> Response:
        return await self.request(source, "POST", url, json_body=json_body, **kw)


_shared: HttpClient | None = None


def shared_client() -> HttpClient:
    global _shared
    if _shared is None:
        _shared = HttpClient()
    return _shared


def set_shared_client(client: HttpClient | None) -> None:
    global _shared
    _shared = client
