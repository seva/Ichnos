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
    """Real tool-caller: stateless JSON-RPC over HTTP to the memory service.

    The memory service (mcp-memory-service 4.1.1) speaks plain JSON-RPC POSTs
    (protocol 2024-11-05, no session id, no SSE stream) — not the newer
    streamable-HTTP handshake, so this caller talks to it directly."""

    def __init__(self, url: str) -> None:
        self._url = url

    async def __call__(self, name: str, args: dict[str, Any]) -> str:
        import httpx

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ichnos-cce", "version": "0.1.0"},
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(self._url, json=init, headers=headers)
            await client.post(
                self._url,
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                headers=headers,
            )
            response = await client.post(
                self._url,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": args},
                },
                headers=headers,
            )
        body = response.json()
        if "error" in body:
            raise RuntimeError(f"memory service tool error: {body['error'].get('message')}")
        return body["result"]["content"][0]["text"]


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
    from cce_server.adapters.memory import MemoryAdapter
    from cce_server.server import build_http_server

    config = load_config(config_path)
    tokens = config.get("tokens") or {}
    if not tokens:
        raise SystemExit("no tokens configured — the HTTP surface serves registered consumers only")
    registry = Registry.from_config(config)
    channels = build_channels(config.get("channels") or {})
    mem_spec = (config.get("channels") or {}).get("memory", {})
    memory_adapter = None
    if mem_spec.get("enabled", True):
        memory_adapter = MemoryAdapter(
            caller=McpMemoryCaller(mem_spec.get("url", "http://127.0.0.1:8000/mcp"))
        )
    return build_http_server(
        registry=registry,
        channels=channels,
        tokens=tokens,
        memory_adapter=memory_adapter,
        allowed_hosts=config.get("allowed_hosts"),
        public_url=config.get("public_url"),
        host=os.environ.get("CCE_HTTP_HOST", "127.0.0.1"),
        port=int(os.environ.get("CCE_HTTP_PORT", "8001")),
    )
