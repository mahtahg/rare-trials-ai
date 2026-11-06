"""Uniform tool output: data + provenance + notes.

Every tool returns the same envelope so a model (or a human auditor) can always
trace a claim back to the exact request that produced it.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from raremcp.core.http import Provenance

MAX_TEXT = 1500  # characters kept from any free-text field by default


def clip(text: str | None, limit: int = MAX_TEXT) -> str | None:
    if text is None:
        return None
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def envelope(
    data: Any,
    provenance: Provenance | Iterable[Provenance],
    *,
    notes: list[str] | None = None,
    next_page_token: str | None = None,
    total: int | None = None,
) -> dict[str, Any]:
    provs = [provenance] if isinstance(provenance, Provenance) else list(provenance)
    out: dict[str, Any] = {"data": data}
    if total is not None:
        out["total"] = total
    if next_page_token:
        out["next_page_token"] = next_page_token
    if notes:
        out["notes"] = notes
    out["provenance"] = [p.to_dict() for p in provs]
    return out


def dig(obj: Any, *path: str | int, default: Any = None) -> Any:
    """Safe nested get: dig(d, 'a', 'b', 0, 'c')."""
    cur = obj
    for p in path:
        if cur is None:
            return default
        if isinstance(p, int):
            if not isinstance(cur, list) or p >= len(cur):
                return default
            cur = cur[p]
        else:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(p)
    return default if cur is None else cur
