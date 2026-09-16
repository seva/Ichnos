"""Manual smoke test: real stdio transport handshake + live get_context call.

Not part of the test suite (hits the real GitHub API via the gh-CLI token ladder).
Usage: .venv/Scripts/python scripts/smoke_stdio.py
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "cce_server"],
        env={
            **os.environ,
            "CCE_CONSUMER": "opencode",
            "CCE_CONFIG": os.path.join(repo, "cce.example.json"),
        },
    )
    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        tools = await session.list_tools()
        print("tools:", [t.name for t in tools.tools])
        result = await session.call_tool("get_context", {})
        data = (
            result.structuredContent
            if result.structuredContent
            else json.loads(result.content[0].text)
        )
        print("consumer:", data["consumer"])
        print("channels:", json.dumps(data["channels"], indent=2)[:2000])


if __name__ == "__main__":
    asyncio.run(main())
