"""MCP server definitions. Each module exposes `register(server)` and `main()`."""

from __future__ import annotations

import argparse

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from biomcp import __version__

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)

COMMON_INSTRUCTIONS = (
    "Every result is an envelope {data, total?, next_page_token?, notes?, provenance[]}. "
    "Cite identifiers (NCT, CHEMBL, EFO/MONDO, ORPHA, PMID) exactly as returned; never invent them. "
    "If data is null, the entity was not found: say so rather than guessing. "
    "Read 'notes' for caveats about proxies and truncation."
)


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
