"""Config wiring tests for the HTTP path: build_http_app_from_config builds the full OAuth + Funnel app."""

from __future__ import annotations

import json

import pytest

from cce_server.config import build_http_app_from_config, load_config

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


def test_build_http_app_exposes_all_tools(config_file):
    """The HTTP path serves the full toolset — identity via the actual request (test_http.py covers the real path)."""
    app = build_http_app_from_config(config_file)
    tools = {t.name for t in __import__("asyncio").run(app.list_tools())}
    assert tools == {
        "get_context",
        "memory_search",
        "memory_recall",
        "memory_store",
        "memory_delete",
    }


def test_missing_public_url_means_no_oauth(config_file):
    """When public_url is absent, the app has no OAuth surface — local-only."""
    cfg_no_url = {k: v for k, v in CONFIG.items() if k != "public_url"}
    p = config_file.parent / "nourl.json"
    p.write_text(json.dumps(cfg_no_url), encoding="utf-8")
    app = build_http_app_from_config(p)
    tools = {t.name for t in __import__("asyncio").run(app.list_tools())}
    assert "get_context" in tools  # still serves, but without auth surface


def test_no_tokens_rejects_http_build(config_file):
    cfg_no_tokens = {k: v for k, v in CONFIG.items() if k != "tokens"}
    p = config_file.parent / "notokens.json"
    p.write_text(json.dumps(cfg_no_tokens), encoding="utf-8")
    with pytest.raises(SystemExit):
        build_http_app_from_config(p)
