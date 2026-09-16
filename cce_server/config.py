"""Server configuration wiring: one JSON config file builds the whole app."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cce_server.adapters.github import GitHubAdapter
from cce_server.channels import Channel, ChannelConfig
from cce_server.registry import Registry
from cce_server.server import build_server

DEFAULT_CONFIG_PATH = "~/.config/ichnos/cce.json"

CHANNEL_ADAPTERS: dict[str, type] = {
    "github": GitHubAdapter,
}


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
    return build_server(registry=registry, channels=channels, binding=binding)
