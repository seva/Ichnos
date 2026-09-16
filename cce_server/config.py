"""Server configuration wiring: one JSON config file builds the whole app."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cce_server.adapters.github import GitHubAdapter
from cce_server.channels import Channel, ChannelConfig
from cce_server.registry import Registry

DEFAULT_CONFIG_PATH = "~/.config/ichnos/cce.json"

CHANNEL_ADAPTERS: dict[str, type] = {
    "github": GitHubAdapter,
}


class McpMemoryCaller:
    """Real tool-caller: per-call MCP client session to the memory service (localhost)."""

    def __init__(self, url: str) -> None:
        self._url = url

    async def __call__(self, name: str, args: dict[str, Any]) -> str:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with (
            streamablehttp_client(self._url) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.call_tool(name, args)
        if result.isError:
            raise RuntimeError(f"memory service tool error: {result.content[0].text}")
        return result.content[0].text


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(os.path.expanduser(str(path)))
    if not config_path.exists():
        raise FileNotFoundError(f"CCE config not found: {config_path}")
    return json.loads(config_path.read_text(encoding="utf-8"))


def build_channels(channels_config: dict[str, Any]) -> list[Channel]:
    channels: list[Channel] = []
    for name, spec in channels_config.items():
        if not spec.get("enabled", True):
            continue
        if name == "memory":
            from functools import partial

            from cce_server.adapters.memory import MemoryAdapter

            caller = McpMemoryCaller(spec.get("url", "http://127.0.0.1:8000/mcp"))
            adapter = MemoryAdapter(caller=caller)
            channels.append(
                Channel(
                    config=ChannelConfig(
                        name=name,
                        ttl_seconds=spec.get("ttl_seconds", 900),
                        timeout_seconds=spec.get("timeout_seconds", 10),
                        query_driven=True,  # retrieval against the prompt — no TTL cache
                    ),
                    adapter=partial(adapter.search, limit=spec.get("limit", 5)),
                )
            )
            continue
        adapter_cls = CHANNEL_ADAPTERS.get(name)
        if adapter_cls is None:
            raise ValueError(f"channel {name}: no adapter registered")
        channels.append(
            Channel(
                config=ChannelConfig(
                    name=name,
                    ttl_seconds=spec.get("ttl_seconds", 300),
                    timeout_seconds=spec.get("timeout_seconds", 10),
                ),
                adapter=adapter_cls().read,
            )
        )
    return channels


def build_app_from_config(config_path: str | Path, binding: str | None = None):
    config = load_config(config_path)
    binding = binding or os.environ.get("CCE_CONSUMER")
    if not binding:
        raise SystemExit(
            "CCE_CONSUMER not set — consumer identity comes from the registration binding"
        )
    registry = Registry.from_config(config)
    channels = build_channels(config.get("channels") or {})
    from cce_server.server import build_server

    return build_server(registry=registry, channels=channels, binding=binding)


def build_http_app_from_config(config_path: str | Path):
    from cce_server.server import build_http_server

    config = load_config(config_path)
    tokens = config.get("tokens") or {}
    if not tokens:
        raise SystemExit("no tokens configured — the HTTP surface serves registered consumers only")
    registry = Registry.from_config(config)
    channels = build_channels(config.get("channels") or {})
    return build_http_server(registry=registry, channels=channels, tokens=tokens)
