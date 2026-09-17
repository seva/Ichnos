"""Verify the Gemini-ui store write landed with provenance, and clean the smoke entries."""

import asyncio
import json
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

_cfg = json.load(open(os.path.expanduser("~/.config/ichnos/cce.json"), encoding="utf-8"))
GEMINI_TOKEN = next(t for t, c in _cfg["tokens"].items() if c == "gemini")
URL = "https://laptop-1s7mkkk6.tail694b01.ts.net/mcp"


async def main() -> None:
    async with streamablehttp_client(URL, headers={"Authorization": f"Bearer {GEMINI_TOKEN}"}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("memory_search", {"query": "gemini live link verified", "limit": 5})
            briefs = (res.structuredContent or {}).get("briefs", [])
            print("entries found:", len(briefs))
            for b in briefs:
                meta = b.get("metadata") or {}
                print("-", (b.get("content") or "")[:50])
                print("  hash:", (b.get("hash") or "")[:16])
                print("  metadata:", json.dumps(meta)[:160])


if __name__ == "__main__":
    asyncio.run(main())
