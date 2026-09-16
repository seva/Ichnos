"""MCP server: identity from the registration binding (never client-supplied), get_context contract."""

from __future__ import annotations

import time
from typing import Any

from mcp.server.fastmcp import FastMCP

from cce_server.channels import Channel
from cce_server.registry import Registry


def build_server(*, registry: Registry, channels: list[Channel], binding: str) -> FastMCP:
    scope = registry.resolve(binding)  # UnregisteredConsumer -> refuses to build

    app: FastMCP = FastMCP("ichnos-cce")

    async def serve_context(channels_requested: list[str] | None = None) -> dict[str, Any]:
        requested = (
            channels_requested
            if channels_requested is not None
            else [c.config.name for c in channels]
        )
        allowed = scope.allowed_channels(requested)
        by_name = {c.config.name: c for c in channels}
        readings: dict[str, Any] = {}
        for name in allowed:
            channel = by_name.get(name)
            if channel is None:
                continue
            reading = await channel.get()
            readings[name] = reading.to_payload(include_data=not scope.summary)
        return {
            "consumer": scope.consumer,
            "summary": scope.summary,
            "generated_at": time.time(),
            "channels": readings,
        }

    @app.tool()
    async def get_context(channels_requested: list[str] | None = None) -> dict[str, Any]:
        """Retrieve the operator's cross-channel context, scoped to this registration."""
        return await serve_context(channels_requested)

    return app
