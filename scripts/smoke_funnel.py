"""Manual smoke test: real MCP client over the PUBLIC Funnel URL.

Exercises the exact production path: TLS -> Tailscale Funnel relay -> engine
HTTP transport -> bearer-token identity -> memory channel -> live store.
Usage: $env:PYTHONIOENCODING="utf-8"; .venv/Scripts/python scripts/smoke_funnel.py
"""

import asyncio
import json
import os
import time as _time

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

FUNNEL_URL = "https://laptop-1s7mkkk6.tail694b01.ts.net/mcp"

with open(os.path.expanduser("~/.config/ichnos/cce.json"), encoding="utf-8") as _f:
    _cfg = json.load(_f)
GEMINI_TOKEN = next(t for t, c in _cfg["tokens"].items() if c == "gemini")


def show(text: str, width: int = 70) -> str:
    return (text or "")[:width].encode("ascii", "replace").decode()


async def main() -> None:
    async with (
        streamablehttp_client(FUNNEL_URL, headers={"Authorization": f"Bearer {GEMINI_TOKEN}"}) as (
            read,
            write,
            _,
        ),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        print("tools:", sorted(t.name for t in tools.tools))

        ctx = await session.call_tool("get_context", {"query": "openclaw"})
        data = ctx.structuredContent or json.loads(ctx.content[0].text)
        mem = data["channels"].get("memory", {})
        print("consumer:", data.get("consumer"), "| stale:", mem.get("stale"))
        for b in mem.get("data", [])[:3]:
            print("brief:", show(b.get("content")))

        store = await session.call_tool(
            "memory_store",
            {
                "content": f"ichnos funnel smoke test {int(_time.time())} - safe to delete",
                "tags": ["smoke"],
            },
        )
        sdata = store.structuredContent or json.loads(store.content[0].text)
        h = sdata.get("hash") or ""
        print("store hash:", show(h, 16) if h else "none")

        search = await session.call_tool("memory_search", {"query": "funnel smoke test"})
        found = (search.structuredContent or {}).get("briefs", [])
        print("search found:", len(found))

        if h:
            delete = await session.call_tool("memory_delete", {"content_hash": h})
            print("delete:", (delete.structuredContent or {}).get("deleted"))


if __name__ == "__main__":
    asyncio.run(main())
