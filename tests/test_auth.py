"""StaticOAuthProvider: DCR, authorize/exchange, refresh, preauthorized verification, persistence."""

from __future__ import annotations

import json
import os

import pytest
from mcp.shared.auth import OAuthClientInformationFull

from cce_server.auth import StaticOAuthProvider


def make_provider(tokens: dict[str, str] | None = None) -> StaticOAuthProvider:
    tokens = tokens if tokens is not None else {}
    return StaticOAuthProvider(preauthorized={"config-token": "openclaw"}, runtime_tokens=tokens)


def make_client(client_id: str = "gemini-app") -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_secret="s3cret",
        redirect_uris=["https://example.com/callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="client_secret_post",
        client_name="Gemini",
    )


class FakeParams:
    def __init__(self):
        self.redirect_uri = "https://example.com/callback"
        self.scopes = ["memory"]
        self.code_challenge = "test-challenge"
        self.state = "client-state-123"


def provider_fully_registered(tokens: dict[str, str] | None = None):
    provider = make_provider(tokens)
    client = make_client()
    provider.approve_client(client.client_id)
    return provider, client


async def test_dcr_register_and_get_client():
    provider = make_provider()
    client = make_client()
    await provider.register_client(client)
    got = await provider.get_client(client.client_id)
    assert got is client


async def test_dcr_new_client_is_pending():
    provider = make_provider()
    client = make_client()
    await provider.register_client(client)
    assert provider._client_status_for(client.client_id) == "pending"


async def test_approved_client_can_authorize():
    provider, client = provider_fully_registered()
    redirect = await provider.authorize(client, FakeParams())
    assert redirect.startswith("https://example.com/callback?code=")
    assert "state=" in redirect


async def test_pending_client_cannot_authorize():
    provider = make_provider()
    client = make_client()
    await provider.register_client(client)
    with pytest.raises(PermissionError, match="pending approval"):
        await provider.authorize(client, FakeParams())


async def test_owner_can_approve_pending_client():
    provider = make_provider()
    client = make_client()
    await provider.register_client(client)
    assert provider._client_status_for(client.client_id) == "pending"
    provider.approve_client(client.client_id)
    assert provider._client_status_for(client.client_id) == "approved"


async def test_load_authorization_code_rejects_foreign_client():
    provider, client = provider_fully_registered()
    await provider.register_client(client)
    await provider.authorize(client, FakeParams())
    code = next(iter(provider._codes))
    intruder = make_client("intruder-app")
    await provider.register_client(intruder)
    assert await provider.load_authorization_code(intruder, code) is None


async def test_exchange_twice_fails_single_use_code():
    provider, client = provider_fully_registered()
    await provider.register_client(client)
    await provider.authorize(client, FakeParams())
    code = await provider.load_authorization_code(client, next(iter(provider._codes)))
    await provider.exchange_authorization_code(client, code)
    with pytest.raises(ValueError):
        await provider.exchange_authorization_code(client, code)


async def test_preauthorized_tokens_verify_as_config_grants():
    provider = make_provider()
    access = await provider.load_access_token("config-token")
    assert access is not None
    assert access.client_id == "openclaw"
    assert await provider.load_access_token("unknown-token") is None


async def test_refresh_flow_rotates_access_token():
    tokens: dict[str, str] = {}
    provider, client = provider_fully_registered(tokens)
    await provider.register_client(client)
    await provider.authorize(client, FakeParams())
    token = await provider.exchange_authorization_code(
        client, await provider.load_authorization_code(client, next(iter(provider._codes)))
    )
    rotated = await provider.exchange_refresh_token(client, token.refresh_token, None)
    assert rotated.access_token != token.access_token
    assert tokens[rotated.access_token] == "web"


async def test_access_token_resolves_after_mint_for_tool_identity():
    tokens: dict[str, str] = {}
    provider, client = provider_fully_registered(tokens)
    await provider.register_client(client)
    await provider.authorize(client, FakeParams())
    token = await provider.exchange_authorization_code(
        client, await provider.load_authorization_code(client, next(iter(provider._codes)))
    )
    assert tokens.get(token.access_token) == "web"


async def test_persistence_round_trip(tmp_path):
    """OAuth-issued tokens survive engine restarts: persist on mint, load on reopen."""
    persist_path = str(tmp_path / "oauth_tokens.json")
    tokens: dict[str, str] = {}
    provider, client = provider_fully_registered(tokens)
    provider._persist_path = persist_path
    await provider.register_client(client)
    await provider.authorize(client, FakeParams())
    token = await provider.exchange_authorization_code(
        client, await provider.load_authorization_code(client, next(iter(provider._codes)))
    )
    assert os.path.exists(persist_path)
    reopened = StaticOAuthProvider(
        preauthorized={"config-token": "openclaw"},
        runtime_tokens=tokens,
        persist_path=persist_path,
    )
    access = await reopened.load_access_token(token.access_token)
    assert access is not None
    assert access.client_id == client.client_id


async def test_persistence_excludes_config_tokens(tmp_path):
    """Only OAuth-minted tokens are persisted - config-registered static tokens must not appear."""
    persist_path = str(tmp_path / "oauth_tokens.json")
    tokens: dict[str, str] = {"config-token": "openclaw"}
    provider = StaticOAuthProvider(
        preauthorized=tokens, runtime_tokens=tokens, persist_path=persist_path
    )
    client = make_client()
    provider.approve_client(client.client_id)
    await provider.register_client(client)
    await provider.authorize(client, FakeParams())
    token = await provider.exchange_authorization_code(
        client, await provider.load_authorization_code(client, next(iter(provider._codes)))
    )
    persisted = json.loads(open(persist_path, encoding="utf-8").read())  # noqa: ASYNC230, SIM115
    assert token.access_token in persisted["tokens"]
    assert "config-token" not in persisted["tokens"]  # config token NOT duplicated


async def test_load_refresh_token_returns_issued(tmp_path):
    tokens: dict[str, str] = {}
    provider, client = provider_fully_registered(tokens)
    await provider.register_client(client)
    await provider.authorize(client, FakeParams())
    token = await provider.exchange_authorization_code(
        client, await provider.load_authorization_code(client, next(iter(provider._codes)))
    )
    refresh = await provider.load_refresh_token(token.refresh_token)
    assert refresh is not None
    assert refresh.client_id == client.client_id


def make_client_with_redirect(
    client_id: str, redirect_uri: str, client_name: str
) -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        redirect_uris=[redirect_uri],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="none",
        client_name=client_name,
    )


async def test_grok_dcr_auto_approved_by_redirect_uri():
    """Grok's connector redirect_uri (grok.com) → auto-approved, consumer=grok."""
    tokens: dict[str, str] = {}
    provider = StaticOAuthProvider(preauthorized={}, runtime_tokens=tokens)
    client = make_client_with_redirect(
        "grok-dcr-1",
        "https://grok.com/connectors-oauth-exchange-code/",
        "Grok",
    )
    await provider.register_client(client)
    assert provider._client_status_for(client.client_id) == "approved"
    # token mints as grok
    provider.approve_client(client.client_id)  # no-op if already approved
    await provider.authorize(client, FakeParams())
    token = await provider.exchange_authorization_code(
        client, await provider.load_authorization_code(client, next(iter(provider._codes)))
    )
    assert tokens[token.access_token] == "grok"


async def test_gemini_dcr_auto_approved_by_redirect_host():
    tokens: dict[str, str] = {}
    provider = StaticOAuthProvider(preauthorized={}, runtime_tokens=tokens)
    client = make_client_with_redirect(
        "gemini-dcr-1",
        "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-123",
        "Google",
    )
    await provider.register_client(client)
    assert provider._client_status_for(client.client_id) == "approved"
    assert (
        tokens.get(f"__dcr__{client.client_id}") == "gemini"
        or provider._dcr_consumers.get(client.client_id) == "gemini"
    )


async def test_claude_dcr_auto_approved():
    tokens: dict[str, str] = {}
    provider = StaticOAuthProvider(preauthorized={}, runtime_tokens=tokens)
    client = make_client_with_redirect(
        "claude-dcr-1",
        "https://claude.ai/api/mcp/auth_callback",
        "Claude",
    )
    await provider.register_client(client)
    assert provider._client_status_for(client.client_id) == "approved"


async def test_unknown_redirect_uri_stays_pending():
    """Unknown redirect_uri → pending → authorize refused (the Owner gate holds)."""
    provider = make_provider()
    client = make_client_with_redirect(
        "evil-1",
        "https://evil.com/callback",
        "Not A Platform",
    )
    await provider.register_client(client)
    assert provider._client_status_for(client.client_id) == "pending"
    with pytest.raises(PermissionError, match="pending approval"):
        await provider.authorize(client, FakeParams())
