"""MCP server: identity from the registration binding (stdio) or the bearer token
(HTTP, resolved per request). One tool surface; capability scoping enforced at
call time from the registry."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.auth.routes import ClientRegistrationOptions
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.server import AuthSettings
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyHttpUrl

from cce_server.adapters.memory import MemoryAdapter, ProvenanceLedger, enrich_briefs
from cce_server.auth import StaticOAuthProvider
from cce_server.channels import Channel
from cce_server.registry import Registry

Resolver = Callable[[Any], str]  # ctx -> consumer name; raises PermissionError when unregistered


def _consumer_from_token(ctx: Context | None, tokens: dict[str, str]) -> str:
    req = ctx.request_context.request if ctx is not None else None
    auth_header = req.headers.get("authorization", "") if req is not None else ""
    token = auth_header.removeprefix("Bearer ").strip()
    consumer = tokens.get(token)
    if consumer is None:
        # Some MCP clients (xAI rmcp) complete OAuth but do not attach the
        # bearer token to MCP requests. These default to the "web" consumer —
        # declared tradeoff: the funnel URL is the access gate.
        import logging

        logging.getLogger("ichnos.auth").info(
            "no consumer resolved from auth header — defaulting to web"
        )
        return "web"
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
    ledger: ProvenanceLedger | None = None,
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
        briefs = enrich_briefs(await memory_adapter.search(query, limit=limit), ledger)
        for b in briefs:
            b["content"] = _snip(b["content"], scope.snippet_length)
        return {"briefs": briefs}

    @app.tool()
    async def memory_recall(query: str, n_results: int = 5, ctx: Context = None) -> dict[str, Any]:
        """Recall memories by time-anchored query."""
        scope = current_scope(ctx)
        if not scope.allowed_channels(["memory"]):
            raise PermissionError("memory is not in this consumer's scope")
        briefs = enrich_briefs(await memory_adapter.recall(query, n_results=n_results), ledger)
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
        if ledger is not None and h:
            ledger.record(h, scope.consumer)
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
    ledger: ProvenanceLedger | None = None,
) -> FastMCP:
    """stdio mode: one process, one consumer — identity from the registration binding."""
    registry.resolve(binding)  # UnregisteredConsumer -> refuses to build
    from mcp.server.transport_security import TransportSecuritySettings

    app: FastMCP = FastMCP(
        "ichnos",
        transport_security=(
            TransportSecuritySettings(
                enable_dns_rebinding_protection=True, allowed_hosts=allowed_hosts
            )
            if allowed_hosts
            else None
        ),
    )
    _register_tools(
        app, registry, channels, memory_adapter, resolve=lambda ctx: binding, ledger=ledger
    )
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
    oauth_clients: dict[str, dict[str, Any]] | None = None,
    ledger: ProvenanceLedger | None = None,
) -> FastMCP:
    """HTTP mode: many consumers, one endpoint — identity resolved per request
    from the Authorization bearer token against the registration's token map.

    public_url: when set (the Funnel deployment), the engine presents a full
    OAuth 2.1 authorization-server surface — Gemini registers as a dynamic
    client (DCR) or uses static credentials, authorizes against the operator's
    consent flow, and every issued access token mints into the consumer model.
    Config-registered static tokens verify as preauthorized grants."""
    from mcp.server.transport_security import TransportSecuritySettings

    pre_approved = {cid for cid, spec in (oauth_clients or {}).items()}
    provider = StaticOAuthProvider(
        preauthorized=tokens,
        runtime_tokens=tokens,
        static_clients={
            client_id: {**spec, "consumer": spec.get("consumer", "gemini")}
            for client_id, spec in (oauth_clients or {}).items()
        }
        if public_url
        else {},
        persist_path=str(
            Path(
                os.environ.get(
                    "CCE_OAUTH_STATE", Path.home() / ".config" / "ichnos" / "oauth_tokens.json"
                )
            )
        ),
        pre_approved_clients=pre_approved,
    )
    for client_id, spec in (oauth_clients or {}).items():
        provider._clients[client_id] = OAuthClientInformationFull(
            client_id=client_id,
            client_secret=spec["client_secret"],
            redirect_uris=[spec["redirect_uri"]],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="client_secret_post",
            client_name="Gemini Spark (static)",
        )

    # OAuth 2.1 auth integration: the BearerAuthMiddleware validates tokens on
    # every request to /mcp. DCR-registered clients go through the pending-
    # approval gate (no code issued until Owner approves). Static clients from
    # config are pre-approved. This is the correct auth architecture per the
    # MCP 2026-07-28 spec — the earlier stripping was wrong.
    auth_kwargs: dict[str, Any] = {}
    if public_url:
        auth_kwargs = {
            "auth_server_provider": provider,
            "auth": AuthSettings(
                issuer_url=AnyHttpUrl(public_url),
                resource_server_url=AnyHttpUrl(public_url),
                client_registration_options=ClientRegistrationOptions(
                    enabled=True, valid_scopes=["memory"]
                ),
            ),
        }

    app: FastMCP = FastMCP(
        "ichnos",
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
        ledger=ledger,
    )
    app._oauth_provider = provider  # deployment wrapper reads this for OAuth routes
    return app


def build_http_asgi(
    **kwargs: Any,
):
    """Deployment wrapper: build_http_server (with OAuth middleware) + discovery aliases + health/diag.

    Returns the ASGI Starlette app for uvicorn/deployment. The FastMCP auth
    integration creates both the auth routes AND the BearerAuthMiddleware —
    the correct architecture per the MCP 2026-07-28 spec. The earlier stripping
    was the wrong response to the rmcp handshake failure."""
    return build_http_asgi_inner(**kwargs)


def build_http_asgi_inner(**kwargs: Any):
    app = build_http_server(**kwargs)
    provider = getattr(app, "_oauth_provider", None)
    return _with_discovery_aliases(app, kwargs.get("public_url"), provider)


def _with_discovery_aliases(
    app: FastMCP, public_url: str | None, provider: StaticOAuthProvider | None = None
):
    """Wrap the streamable-HTTP Starlette app with discovery paths, health and diag routes.

    The OAuth routes AND the BearerAuthMiddleware are created by FastMCP's auth
    integration (auth_server_provider + auth settings) — the correct architecture
    per the MCP 2026-07-28 spec. This function adds only the alias paths the SDK
    doesn't serve: OpenID discovery alias, path-scoped PRM, health, diag."""
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    http_app = app.streamable_http_app()

    if not public_url:
        return http_app

    issuer = public_url.rstrip("/")

    async def openid_config(request):
        return JSONResponse(
            {
                "issuer": issuer + "/",
                "authorization_endpoint": issuer + "/authorize",
                "token_endpoint": issuer + "/token",
                "registration_endpoint": issuer + "/register",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": [
                    "client_secret_post",
                    "client_secret_basic",
                ],
            }
        )

    async def protected_resource_mcp(request):
        return JSONResponse(
            {
                "resource": issuer + "/mcp",
                "authorization_servers": [issuer + "/"],
                "bearer_methods_supported": ["header"],
            }
        )

    async def health(request):
        return JSONResponse({"status": "ok"})

    async def diag(request):
        return JSONResponse(
            {
                "remote_addr": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "host": request.headers.get("host"),
                "method": request.method,
                "path": request.url.path,
            }
        )

    http_app.routes.extend(
        [
            Route("/.well-known/openid-configuration", openid_config, methods=["GET"]),
            Route(
                "/.well-known/oauth-protected-resource/mcp",
                protected_resource_mcp,
                methods=["GET"],
            ),
            Route("/health", health, methods=["GET"]),
            Route("/diag", diag, methods=["GET"]),
        ]
    )
    return http_app
