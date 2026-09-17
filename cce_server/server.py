"""MCP server: identity from the registration binding (stdio) or the bearer token
(HTTP, resolved per request). One tool surface; capability scoping enforced at
call time from the registry."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from pydantic import AnyHttpUrl

from cce_server.adapters.memory import MemoryAdapter
from cce_server.auth import StaticOAuthProvider
from cce_server.channels import Channel
from cce_server.registry import Registry

Resolver = Callable[[Any], str]  # ctx -> consumer name; raises PermissionError when unregistered


def _consumer_from_token(ctx: Context | None, tokens: dict[str, str]) -> str:
    req = ctx.request_context.request if ctx is not None else None
    auth = req.headers.get("authorization", "") if req is not None else ""
    consumer = tokens.get(auth.removeprefix("Bearer ").strip())
    if consumer is None:
        raise PermissionError("unregistered consumer")
    return consumer


def _snip(text: Any, n: int | None) -> Any:
    if n and isinstance(text, str) and len(text) > n:
        return text[:n] + "…"
    return text


def _register_tools(
    app: FastMCP,
    registry: Registry,
    channels: list[Channel],
    memory_adapter: MemoryAdapter | None,
    resolve: Resolver,
) -> None:
    def current_scope(ctx: Context | None):
        return registry.resolve(resolve(ctx))

    @app.tool()
    async def get_context(
        channels_requested: list[str] | None = None,
        query: str | None = None,
        ctx: Context = None,
    ) -> dict[str, Any]:
        """Retrieve the operator's cross-channel context, scoped to this registration."""
        scope = current_scope(ctx)
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
            reading = await channel.get(query=query)
            payload = reading.to_payload(include_data=not scope.summary)
            if scope.snippet_length and isinstance(payload.get("data"), list):
                for item in payload["data"]:
                    if isinstance(item, dict):
                        item["content"] = _snip(item.get("content"), scope.snippet_length)
            readings[name] = payload
        return {
            "consumer": scope.consumer,
            "summary": scope.summary,
            "generated_at": time.time(),
            "channels": readings,
        }

    if memory_adapter is None:
        return

    @app.tool()
    async def memory_search(query: str, limit: int = 5, ctx: Context = None) -> dict[str, Any]:
        """Search the operator's memory store; returns the top-k relevant briefs."""
        scope = current_scope(ctx)
        if not scope.allowed_channels(["memory"]):
            raise PermissionError("memory is not in this consumer's scope")
        briefs = await memory_adapter.search(query, limit=limit)
        for b in briefs:
            b["content"] = _snip(b["content"], scope.snippet_length)
        return {"briefs": briefs}

    @app.tool()
    async def memory_recall(query: str, n_results: int = 5, ctx: Context = None) -> dict[str, Any]:
        """Recall memories by time-anchored query."""
        scope = current_scope(ctx)
        if not scope.allowed_channels(["memory"]):
            raise PermissionError("memory is not in this consumer's scope")
        briefs = await memory_adapter.recall(query, n_results=n_results)
        for b in briefs:
            b["content"] = _snip(b["content"], scope.snippet_length)
        return {"briefs": briefs}

    @app.tool()
    async def memory_store(
        content: str, tags: list[str] | None = None, ctx: Context = None
    ) -> dict[str, Any]:
        """Store a memory. Provenance (which consumer wrote it) is injected server-side."""
        scope = current_scope(ctx)
        if not scope.can_write("memory"):
            raise PermissionError("no write grant on memory for this consumer")
        h = await memory_adapter.store(content, tags=tags, provenance=scope.consumer)
        return {"hash": h, "provenance": scope.consumer}

    @app.tool()
    async def memory_delete(content_hash: str, ctx: Context = None) -> dict[str, Any]:
        """Delete a memory by content hash. Requires an explicit write grant."""
        scope = current_scope(ctx)
        if not scope.can_write("memory"):
            raise PermissionError("no write grant on memory for this consumer")
        return {"deleted": await memory_adapter.delete(content_hash)}


def build_server(
    *,
    registry: Registry,
    channels: list[Channel],
    binding: str,
    memory_adapter: MemoryAdapter | None = None,
    allowed_hosts: list[str] | None = None,
) -> FastMCP:
    """stdio mode: one process, one consumer — identity from the registration binding."""
    registry.resolve(binding)  # UnregisteredConsumer -> refuses to build
    from mcp.server.transport_security import TransportSecuritySettings

    app: FastMCP = FastMCP(
        "ichnos-cce",
        transport_security=(
            TransportSecuritySettings(
                enable_dns_rebinding_protection=True, allowed_hosts=allowed_hosts
            )
            if allowed_hosts
            else None
        ),
    )
    _register_tools(app, registry, channels, memory_adapter, resolve=lambda ctx: binding)
    return app


def build_http_server(
    *,
    registry: Registry,
    channels: list[Channel],
    tokens: dict[str, str],
    memory_adapter: MemoryAdapter | None = None,
    allowed_hosts: list[str] | None = None,
    host: str = "127.0.0.1",
    port: int = 8001,
    public_url: str | None = None,
) -> FastMCP:
    """HTTP mode: many consumers, one endpoint — identity resolved per request
    from the Authorization bearer token against the registration's token map.

    public_url: when set (the Funnel deployment), the engine presents a full
    OAuth 2.1 authorization-server surface — Gemini registers as a dynamic
    client (DCR) or uses static credentials, authorizes against the operator's
    consent flow, and every issued access token mints into the consumer model.
    Config-registered static tokens verify as preauthorized grants."""
    from mcp.server.auth.routes import ClientRegistrationOptions
    from mcp.server.fastmcp.server import AuthSettings
    from mcp.server.transport_security import TransportSecuritySettings

    auth_kwargs: dict[str, Any] = {}
    if public_url:
        provider = StaticOAuthProvider(preauthorized=tokens, runtime_tokens=tokens)
        auth_kwargs = {
            "auth_server_provider": provider,
            "auth": AuthSettings(
                issuer_url=AnyHttpUrl(public_url),
                resource_server_url=AnyHttpUrl(public_url),
                client_registration_options=ClientRegistrationOptions(enabled=True),
            ),
        }

    app: FastMCP = FastMCP(
        "ichnos-cce",
        host=host,
        port=port,
        transport_security=(
            TransportSecuritySettings(
                enable_dns_rebinding_protection=True, allowed_hosts=allowed_hosts
            )
            if allowed_hosts
            else None
        ),
        **auth_kwargs,
    )
    _register_tools(
        app,
        registry,
        channels,
        memory_adapter,
        resolve=lambda ctx: _consumer_from_token(ctx, tokens),
    )
    return app
