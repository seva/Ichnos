"""Server construction: registration binding required, tool exposed, contract-shaped payload."""

from __future__ import annotations

import pytest

from cce_server.channels import Channel, ChannelConfig
from cce_server.registry import Registry, UnregisteredConsumer
from cce_server.server import build_server


def make_registry():
    return Registry.from_config({"consumers": {"openclaw": {"scope": "full"}}})


def make_channels():
    return [
        Channel(config=ChannelConfig(name="github", ttl_seconds=300, timeout_seconds=10)),
    ]


def test_unregistered_binding_refuses_to_build():
    with pytest.raises(UnregisteredConsumer):
        build_server(registry=make_registry(), channels=make_channels(), binding="intruder")


def test_registered_binding_builds_with_tool():
    app = build_server(registry=make_registry(), channels=make_channels(), binding="openclaw")
    tools = (
        {t.name for t in app._tool_manager.list_tools()} if hasattr(app, "_tool_manager") else None
    )
    if tools is None:  # fall back to public API
        tools = asyncio_tools(app)
    assert "get_context" in tools


def asyncio_tools(app):
    import asyncio

    async def _list():
        return await app.list_tools()

    return {t.name for t in asyncio.run(_list())}


async def test_empty_channel_set_returns_valid_contract_payload():
    app = build_server(registry=make_registry(), channels=[], binding="openclaw")
    payload = await app.get_context_fn()
    assert payload["consumer"] == "openclaw"
    assert payload["channels"] == {}
    assert "generated_at" in payload


async def test_not_configured_channel_is_explicitly_unavailable():
    app = build_server(registry=make_registry(), channels=make_channels(), binding="openclaw")
    payload = await app.get_context_fn()
    gh = payload["channels"]["github"]
    assert gh["unavailable"] is True
    assert gh["reason"] == "not-configured"
