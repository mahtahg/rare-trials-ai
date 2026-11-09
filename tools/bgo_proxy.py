"""Pass-through stdio proxy for the BioMCP comparator.

With the current Claude Code client, `biomcp serve` (biomcp-cli 0.9.3) exits cleanly about 4-7 s after each
connection; Claude Code reconnects, but any tool call in flight fails with "Connection closed"
(eval/results/bgo-debug/mcp_logs). Driven by the Python MCP client, the same server stays up
(eval/review/bgo_diag). This proxy is a Python MCP server that holds one Python-client session to
`biomcp serve` and forwards tools/list and tools/call unchanged: same tool names, descriptions, schemas and
results. If the upstream session is lost, it reconnects once and retries the call.

    command: python tools/bgo_proxy.py        (BIOMCP_BIN overrides the biomcp executable)
"""

from __future__ import annotations

import os
import shutil
import sys
from contextlib import AsyncExitStack, asynccontextmanager

import anyio
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

BIN = os.environ.get("BIOMCP_BIN") or shutil.which("biomcp") or "biomcp"


class Upstream:
    def __init__(self) -> None:
        self.stack: AsyncExitStack | None = None
        self.session: ClientSession | None = None
        self.reconnects = 0

    async def connect(self) -> ClientSession:
        self.stack = AsyncExitStack()
        r, w = await self.stack.enter_async_context(
            stdio_client(StdioServerParameters(command=BIN, args=["serve"], env=dict(os.environ)), errlog=sys.stderr))
        self.session = await self.stack.enter_async_context(ClientSession(r, w))
        await self.session.initialize()
        return self.session

    async def close(self) -> None:
        if self.stack:
            try:
                await self.stack.aclose()
            except Exception as e:  # noqa: BLE001
                print(f"bgo_proxy: close error ignored ({type(e).__name__})", file=sys.stderr, flush=True)
        self.stack = self.session = None

    async def call(self, fn):
        if self.session is None:
            await self.connect()
        try:
            return await fn(self.session)
        except (anyio.ClosedResourceError, anyio.BrokenResourceError, anyio.EndOfStream, OSError, RuntimeError) as e:
            print(f"bgo_proxy: upstream lost ({type(e).__name__}: {e}); reconnecting", file=sys.stderr, flush=True)
            self.reconnects += 1
            await self.close()
            await self.connect()
            return await fn(self.session)


UP = Upstream()


@asynccontextmanager
async def lifespan(_server):
    await UP.connect()
    try:
        yield {}
    finally:
        print(f"bgo_proxy: upstream reconnects={UP.reconnects}", file=sys.stderr, flush=True)
        await UP.close()


async def list_tools(_ctx, _params) -> types.ListToolsResult:
    return await UP.call(lambda s: s.list_tools())


async def call_tool(_ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
    return await UP.call(lambda s: s.call_tool(params.name, params.arguments or {}))


server = Server("biomcp", version="0.9.3-proxied", lifespan=lifespan, on_list_tools=list_tools, on_call_tool=call_tool)


async def main() -> None:
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
