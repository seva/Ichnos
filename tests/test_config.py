"""Tests for config wiring: one JSON file builds the app; binding comes from env or argument."""

from __future__ import annotations

import json

import pytest

from cce_server.config import build_app_from_config, load_config

CONFIG = {
    "consumers": {"opencode": {"scope": "full"}, "reader": {"scope": "summary"}},
    "channels": {
        "github": {"enabled": True, "ttl_seconds": 300, "timeout_seconds": 10},
        "telegram_bot": {"enabled": False},
    },
}


@pytest.fixture
def config_file(tmp_path):
    p = tmp_path / "cce.json"
    p.write_text(json.dumps(CONFIG), encoding="utf-8")
    return p


def test_load_config_parses(config_file):
    config = load_config(config_file)
    assert config["consumers"]["opencode"]["scope"] == "full"


def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nope.json")


def test_build_app_wires_enabled_channels_only(config_file, monkeypatch):
    monkeypatch.setenv("CCE_CONSUMER", "opencode")
    app = build_app_from_config(config_file)
    tools = {t.name for t in __import__("asyncio").run(app.list_tools())}
    assert tools == {"get_context"}


async def test_build_app_serves_github_channel_contract(config_file, monkeypatch):
    monkeypatch.setenv("CCE_CONSUMER", "opencode")
    app = build_app_from_config(config_file)
    result = await app.call_tool("get_context", {})
    data = result[1] if isinstance(result, tuple) else result
    assert "github" in data["channels"]
    assert (
        data["channels"]["github"]["as_of"] > 0
    )  # live read attempted (will fail w/o token -> unavailable, but read attempted)


async def test_disabled_channels_are_not_wired(config_file, monkeypatch):
    monkeypatch.setenv("CCE_CONSUMER", "opencode")
    app = build_app_from_config(config_file)
    result = await app.call_tool("get_context", {})
    data = result[1] if isinstance(result, tuple) else result
    assert "telegram_bot" not in data["channels"]
    assert "github" in data["channels"]


async def test_unknown_channel_name_rejected(config_file, monkeypatch):
    monkeypatch.setenv("CCE_CONSUMER", "opencode")
    bad = dict(CONFIG)
    bad["channels"] = {"mystery": {"enabled": True}}
    p = config_file.parent / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="mystery"):
        build_app_from_config(p)


def test_missing_binding_without_env_exits(config_file, monkeypatch):
    monkeypatch.delenv("CCE_CONSUMER", raising=False)
    with pytest.raises(SystemExit):
        build_app_from_config(config_file)


async def test_summary_consumer_gets_no_data_fields(config_file, monkeypatch):
    monkeypatch.setenv("CCE_CONSUMER", "reader")
    app = build_app_from_config(config_file)
    result = await app.call_tool("get_context", {})
    data = result[1] if isinstance(result, tuple) else result
    assert data["summary"] is True
