"""Manual smoke test: the HTTP engine path against the REAL memory service.

Builds the HTTP app from the live config, connects a real MCP client over ASGI
with the gemini token, and runs a live query-driven memory retrieval + a real
store/delete round-trip. Not part of the test suite (hits the live memory store).
Usage: .venv/Scripts/python scripts/smoke_http.py
"""

import asyncio
import json
import os

import httpx
from asgi_lifespan import LifespanManager
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from cce_server.config import build_http_app_from_config


async def main() -> None:
    cfg = json.load(open(os.path.expanduser("~/.config/ichnos/cce.json"), encoding="utf-8"))  # noqa: ASYNC230, SIM115
    gemini_token = next(t for t, c in cfg["tokens"].items() if c == "gemini")

    app = build_http_app_from_config(
        os.path.expanduser("~/.config/ichnos/cce.json")
    ).streamable_http_app()
    headers = {"Authorization": f"Bearer {gemini_token}"}

    def factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1:8001",
            headers=headers,
        )

    async with (
        LifespanManager(app),
        streamablehttp_client(
            "http://127.0.0.1:8001/mcp", headers=headers, httpx_client_factory=factory
        ) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()

        tools = await session.list_tools()
        print("tools:", sorted(t.name for t in tools.tools))

        ctx = await session.call_tool("get_context", {"query": "openclaw gateway restart"})
        data = ctx.structuredContent or json.loads(ctx.content[0].text)
        mem = data["channels"].get("memory", {})
        briefs = mem.get("data", [])
        print("get_context consumer:", data["consumer"])
        print("memory channel stale:", mem.get("stale"), "| reason:", mem.get("reason"))
        print("top briefs:", [b.get("content", "")[:80] for b in briefs[:3]])

        store = await session.call_tool(
            "memory_store",
            {"content": "ichnos smoke test — safe to delete", "tags": ["smoke"]},
        )
        sdata = store.structuredContent or json.loads(store.content[0].text)
        print("store:", sdata)

        search = await session.call_tool("memory_search", {"query": "ichnos smoke test"})
        srch = search.structuredContent or json.loads(search.content[0].text)
        print("search found:", len(srch.get("briefs", [])), "brief(s)")

        h = sdata.get("hash")
        if h:
            delete = await session.call_tool("memory_delete", {"content_hash": h})
            ddata = delete.structuredContent or json.loads(delete.content[0].text)
            print("delete:", ddata)


if __name__ == "__main__":
    asyncio.run(main())
