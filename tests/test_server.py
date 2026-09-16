"""Server construction: registration binding required, tool exposed and callable through the real path."""

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


def payload_from(result):
    if isinstance(result, tuple) and isinstance(result[1], dict):
        return result[1]
    import json

    return json.loads(result[0][0].text)


def test_unregistered_binding_refuses_to_build():
    with pytest.raises(UnregisteredConsumer):
        build_server(registry=make_registry(), channels=make_channels(), binding="intruder")


async def test_registered_binding_exposes_get_context_tool():
    app = build_server(registry=make_registry(), channels=make_channels(), binding="openclaw")
    tools = await app.list_tools()
    assert "get_context" in {t.name for t in tools}


async def test_tool_call_through_real_path_returns_contract_payload():
    app = build_server(registry=make_registry(), channels=make_channels(), binding="openclaw")
    data = payload_from(await app.call_tool("get_context", {}))
    assert data["consumer"] == "openclaw"
    assert "generated_at" in data
    gh = data["channels"]["github"]
    assert gh["unavailable"] is True
    assert gh["reason"] == "not-configured"


async def test_empty_channel_set_returns_valid_contract_payload():
    app = build_server(registry=make_registry(), channels=[], binding="openclaw")
    data = payload_from(await app.call_tool("get_context", {}))
    assert data["channels"] == {}


async def test_unknown_requested_channel_is_skipped():
    app = build_server(registry=make_registry(), channels=make_channels(), binding="openclaw")
    data = payload_from(
        await app.call_tool("get_context", {"channels_requested": ["github", "nope"]})
    )
    assert "nope" not in data["channels"]
    assert "github" in data["channels"]
