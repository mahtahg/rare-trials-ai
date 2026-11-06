"""MCP server definitions. Each module exposes `register(server)` and `main()`."""

from __future__ import annotations

import argparse
import functools

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from raremcp import __version__

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)

COMMON_INSTRUCTIONS = (
    "Every result is an envelope {data, total?, next_page_token?, notes?, provenance[]}. "
    "Cite identifiers (NCT, CHEMBL, EFO/MONDO, ORPHA, PMID) exactly as returned; never invent them. "
    "If data is null, the entity was not found: say so rather than guessing. "
    "Read 'notes' for caveats about proxies and truncation."
)


def tool(server: MCPServer):
    """Like @server.tool, but turns input/source errors into ToolErrors whose message reaches the model."""

    def deco(fn):
        @functools.wraps(fn)
        async def wrapped(*args, **kwargs):
            from raremcp.core.http import SourceError

            try:
                return await fn(*args, **kwargs)
            except (ValueError, SourceError) as exc:
                raise ToolError(f"{type(exc).__name__}: {exc}") from exc

        return server.tool(annotations=READ_ONLY)(wrapped)

    return deco


def make_server(name: str, instructions: str) -> MCPServer:
    return MCPServer(name=name, version=__version__, instructions=f"{instructions}\n\n{COMMON_INSTRUCTIONS}")


def run(server: MCPServer) -> None:
    ap = argparse.ArgumentParser(description=f"{server.name} MCP server")
    ap.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    if a.transport == "stdio":
        server.run("stdio")
    else:
        server.run("streamable-http", host=a.host, port=a.port)
