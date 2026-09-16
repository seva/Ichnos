"""HTTP transport: the engine serves the toolset per consumer capability over real MCP-over-HTTP.

Integration tests — the real streamable-HTTP server app is exercised through a real
MCP client via ASGI transport (no seams: identity flows through actual Authorization
headers, exactly as the Funnel-exposed deployment will carry them)."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

import httpx
from asgi_lifespan import LifespanManager
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from cce_server.adapters.memory import MemoryAdapter
from cce_server.channels import Channel, ChannelConfig
from cce_server.registry import Registry
from cce_server.server import build_http_server

TOKENS = {"gemini-token": "gemini", "openclaw-token": "openclaw", "bogus-token": "intruder"}

FAKE_SEARCH = json.dumps(
    {
        "results": [
            {
                "content": "memory brief from the store",
                "tags": ["test"],
                "metadata": {},
                "created_at": "2026-09-16T00:00:00",
                "content_hash": "h1",
                "similarity_score": 0.9,
            }
        ]
    }
)


def make_registry() -> Registry:
    return Registry.from_config(
        {
            "consumers": {
                "gemini": {
                    "scope": "channels",
                    "channels": ["memory"],
                    "writable": ["memory"],
                    "snippet_length": 10,
                },
                "openclaw": {"scope": "full", "writable": []},
            }
        }
    )


def make_channels() -> list[Channel]:
    return [
        Channel(config=ChannelConfig(name="github", ttl_seconds=300, timeout_seconds=10)),
        Channel(config=ChannelConfig(name="memory", ttl_seconds=900, timeout_seconds=5)),
    ]


class FakeMemoryCaller:
    """Captures tool calls; answers name-aware (search/recall -> briefs, store -> hash, delete -> ok)."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def __call__(self, name: str, args: dict) -> str:
        self.calls.append((name, args))
        if name == "store_memory":
            return json.dumps({"success": True, "content_hash": "h1"})
        if name == "delete_memory":
            return json.dumps({"success": True})
        return FAKE_SEARCH


def payload(result):
    if isinstance(result, tuple) and isinstance(result[1], dict):
        return result[1]
    return json.loads(result.content[0].text)


def build_app(caller: FakeMemoryCaller | None = None):
    caller = caller or FakeMemoryCaller()
    app = build_http_server(
        registry=make_registry(),
        channels=make_channels(),
        tokens=TOKENS,
        memory_adapter=MemoryAdapter(caller=caller),
    )
    http_app = (
        app.streamable_http_app()
    )  # ONE instance: lifespan and requests must hit the same app
    return http_app, caller


def client_factory(http_app, token: str | None = None):
    def factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=http_app),
            base_url="http://127.0.0.1:8001",  # Host must match the engine's allowed_hosts (localhost)
            headers=headers,
        )

    return factory


@asynccontextmanager
async def open_session(http_app, token: str | None = None):
    from contextlib import asynccontextmanager as acm

    @acm
    async def stack():
        async with (
            LifespanManager(http_app),
            streamablehttp_client(
                "http://127.0.0.1:8001/mcp",
                headers={"Authorization": f"Bearer {token}"} if token else {},
                httpx_client_factory=client_factory(http_app, token),
            ) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            yield session

    async with stack() as session:
        yield session


async def test_invalid_token_receives_no_context_data():
    http_app, _ = build_app()
    async with open_session(http_app, token="bogus-token") as session:
        await session.initialize()
        result = await session.call_tool("get_context", {})
        assert result.isError  # explicit failure — never context data
        assert "unregistered" in result.content[0].text.lower()


async def test_no_token_receives_no_context_data():
    http_app, _ = build_app()
    async with open_session(http_app, token=None) as session:
        await session.initialize()
        result = await session.call_tool("get_context", {})
        assert result.isError


async def test_gemini_token_sees_memory_channel_only():
    http_app, _ = build_app()
    async with open_session(http_app, token="gemini-token") as session:
        await session.initialize()
        result = await session.call_tool("get_context", {"query": "openclaw"})
        data = payload(result)
        assert data["consumer"] == "gemini"
        assert set(data["channels"].keys()) == {"memory"}


async def test_openclaw_token_sees_full_matrix():
    http_app, _ = build_app()
    async with open_session(http_app, token="openclaw-token") as session:
        await session.initialize()
        result = await session.call_tool("get_context", {})
        data = payload(result)
        assert set(data["channels"].keys()) == {"github", "memory"}


async def test_gemini_memory_search_returns_briefs():
    caller = FakeMemoryCaller()
    http_app, _ = build_app(caller)
    async with open_session(http_app, token="gemini-token") as session:
        await session.initialize()
        result = await session.call_tool("memory_search", {"query": "model chain", "limit": 5})
        data = payload(result)
        assert data["briefs"][0]["content"] == "memory bri…"  # snippet_length=10 enforced
        assert caller.calls[0][0] == "retrieve_memory"


async def test_gemini_memory_store_injects_provenance():
    caller = FakeMemoryCaller()
    http_app, _ = build_app(caller)
    async with open_session(http_app, token="gemini-token") as session:
        await session.initialize()
        result = await session.call_tool(
            "memory_store", {"content": "note from gemini", "tags": ["test"]}
        )
        data = payload(result)
        assert data["hash"] == "h1"
        name, args = caller.calls[0]
        assert name == "store_memory"
        assert args["metadata"]["client"] == "gemini"


async def test_read_only_consumer_cannot_store():
    http_app, _ = build_app(FakeMemoryCaller())
    async with open_session(http_app, token="openclaw-token") as session:
        await session.initialize()
        result = await session.call_tool("memory_store", {"content": "should not land", "tags": []})
        assert result.isError
        assert "write" in result.content[0].text.lower()


async def test_memory_tools_absent_without_adapter():
    app = build_http_server(
        registry=make_registry(), channels=make_channels(), tokens=TOKENS, memory_adapter=None
    )
    tools = await app.list_tools()
    names = {t.name for t in tools}
    assert "get_context" in names
    assert not any(n.startswith("memory_") for n in names)
