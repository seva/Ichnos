"""Manual smoke test: real MCP client over the PUBLIC Funnel URL.

Exercises the exact production path: TLS -> Tailscale Funnel relay -> engine
HTTP transport -> bearer-token identity -> memory channel -> live store.
Usage: $env:PYTHONIOENCODING="utf-8"; .venv/Scripts/python scripts/smoke_funnel.py
"""

import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

FUNNEL_URL = "https://laptop-1s7mkkk6.tail694b01.ts.net/mcp"


async def main() -> None:
    config_path = os.path.expanduser("~/.config/ichnos/cce.json")
    cfg = json.load(open(config_path, encoding="utf-8"))
    gemini_token = next(t for t, c in cfg["tokens"].items() if c == "gemini")

    async with streamablehttp_client(
        FUNNEL_URL, headers={"Authorization": f"Bearer {gemini_token}"}
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", sorted(t.name for t in tools.tools))

            ctx = await session.call_tool("get_context", {"query": "openclaw"})
            data = ctx.structuredContent or json.loads(ctx.content[0].text)
            mem = data["channels"].get("memory", {})
            print("consumer:", data.get("consumer"), "| stale:", mem.get("stale"))
            briefs = mem.get("data", [])
            for b in briefs[:3]:
                print("brief:", (b.get("content") or "")[:70].encode("ascii", "replace").decode())

            store = await session.call_tool(
                "memory_store",
                {"content": "ichnos funnel smoke test - safe to delete", "tags": ["smoke"]},
            )
            sdata = store.structuredContent or json.loads(store.content[0].text)
            print("store hash:", sdata.get("hash", "")[:16])

            search = await session.call_tool("memory_search", {"query": "funnel smoke test"})
            found = (search.structuredContent or {}).get("briefs", [])
            print("search found:", len(found))

            if sdata.get("hash"):
                delete = await session.call_tool("memory_delete", {"content_hash": sdata["hash"]})
                print("delete:", (delete.structuredContent or {}).get("deleted"))


if __name__ == "__main__":
    asyncio.run(main())
