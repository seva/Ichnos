"""StaticOAuthProvider: DCR, authorize/exchange, refresh, preauthorized verification."""

from __future__ import annotations

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
        self.scopes = ["memory"]


def provider_fully_registered(tokens: dict[str, str] | None = None):
    provider = make_provider(tokens)
    client = make_client()
    return provider, client


async def test_dcr_register_and_get_client():
    provider = make_provider()
    client = make_client()
    await provider.register_client(client)
    got = await provider.get_client(client.client_id)
    assert got is client


async def test_authorize_issues_code_exchange_mints_tokens_into_runtime_map():
    tokens: dict[str, str] = {}
    provider, client = provider_fully_registered(tokens)
    await provider.register_client(client)
    redirect = await provider.authorize(client, FakeParams())
    # the returned location must carry the code (and state) as query params
    assert redirect.startswith("https://example.com/callback?code=")
    assert "state=" in redirect
    code_value = redirect.split("code=")[1].split("&")[0]
    auth_code = await provider.load_authorization_code(client, code_value)
    token = await provider.exchange_authorization_code(client, auth_code)
    assert token.access_token and token.refresh_token
    assert tokens[token.access_token] == "web"  # runtime mint — DCR clients default to web
    assert tokens[token.refresh_token] == "web"


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
    # the resolver contract: an issued access token resolves to its consumer
    assert tokens.get(token.access_token) == "web"
