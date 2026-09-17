"""Config wiring tests: one JSON config builds the full app (stdio and HTTP paths)."""

from __future__ import annotations

import json

import pytest

from cce_server.adapters.memory import MemoryAdapter
from cce_server.config import build_channels, load_config
from cce_server.registry import Registry
from cce_server.server import build_http_server, build_server

CONFIG = {
    "consumers": {
        "opencode": {"scope": "full"},
        "gemini": {
            "scope": "channels",
            "channels": ["memory"],
            "writable": ["memory"],
            "snippet_length": 200,
        },
    },
    "tokens": {"tok-opencode": "opencode", "tok-gemini": "gemini"},
    "allowed_hosts": ["127.0.0.1:*", "localhost:*"],
    "public_url": "https://test.tailnet.ts.net",
    "oauth_clients": {
        "gemini-spark": {
            "client_secret": "s3cret",
            "redirect_uri": "https://oauth-redirect.googleusercontent.com/r/probe",
            "consumer": "gemini",
        }
    },
    "channels": {
        "github": {"enabled": True, "ttl_seconds": 300, "timeout_seconds": 10},
        "memory": {
            "enabled": True,
            "ttl_seconds": 900,
            "timeout_seconds": 10,
            "url": "http://127.0.0.1:8000/mcp",
            "limit": 5,
        },
    },
}


@pytest.fixture
def config_file(tmp_path):
    p = tmp_path / "cce.json"
    p.write_text(json.dumps(CONFIG), encoding="utf-8")
    return p


def test_load_config_parses(config_file):
    config = load_config(config_file)
    assert config["public_url"] == "https://test.tailnet.ts.net"
    assert "gemini-spark" in config["oauth_clients"]


def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.json")


def test_build_channels_wires_memory_as_query_driven():
    channels = build_channels(CONFIG["channels"])
    by_name = {c.config.name: c for c in channels}
    assert by_name["memory"].config.query_driven is True
    assert by_name["github"].config.query_driven is False


def test_disabled_channels_not_wired():
    channels = build_channels({"github": {"enabled": False}})
    assert len(channels) == 0


def test_unknown_channel_name_rejected():
    with pytest.raises(ValueError, match="mystery"):
        build_channels({"mystery": {"enabled": True}})


def test_build_http_server_with_oauth_and_memory(config_file):
    """build_http_server returns FastMCP with the full toolset when memory_adapter is passed."""
    registry = Registry.from_config(CONFIG)
    channels = build_channels(CONFIG["channels"])
    adapter = MemoryAdapter(caller=lambda name, args: json.dumps({"results": [], "success": True}))
    app = build_http_server(
        registry=registry,
        channels=channels,
        tokens=CONFIG["tokens"],
        memory_adapter=adapter,
        allowed_hosts=CONFIG["allowed_hosts"],
        public_url=CONFIG["public_url"],
        oauth_clients=CONFIG["oauth_clients"],
    )
    tools = {t.name for t in __import__("asyncio").run(app.list_tools())}
    assert tools == {
        "get_context",
        "memory_search",
        "memory_recall",
        "memory_store",
        "memory_delete",
    }


def test_build_http_server_without_public_url(config_file):
    """No public_url → no OAuth surface — local-only, but still serves."""
    registry = Registry.from_config(CONFIG)
    channels = build_channels(CONFIG["channels"])
    app = build_http_server(registry=registry, channels=channels, tokens=CONFIG["tokens"])
    tools = {t.name for t in __import__("asyncio").run(app.list_tools())}
    assert "get_context" in tools


def test_build_server_stdio_returns_fastmcp():
    registry = Registry.from_config(CONFIG)
    channels = build_channels(CONFIG["channels"])
    app = build_server(registry=registry, channels=channels, binding="opencode")
    tools = {t.name for t in __import__("asyncio").run(app.list_tools())}
    assert "get_context" in tools


def test_no_tokens_rejects_http_build(tmp_path):
    """build_http_app_from_config without tokens → SystemExit (the HTTP surface requires auth)."""
    from cce_server.config import build_http_app_from_config

    cfg = {k: v for k, v in CONFIG.items() if k != "tokens"}
    p = tmp_path / "notokens.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(SystemExit):
        build_http_app_from_config(p)
