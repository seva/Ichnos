"""Minimal OAuth 2.1 authorization-server provider for the engine's HTTP surface.

Implements the SDK's OAuthAuthorizationServerProvider over in-memory state:
- DCR (dynamic client registration) is supported — Gemini registers itself; a
  static client also works via the Advanced path.
- /authorize auto-approves the registered resource owner: this endpoint serves a
  single operator, and redirect URIs are pinned per client, so the consent
  surface is the registration itself. Auto-approval is a declared v1 tradeoff.
- Issued access tokens are minted into the engine's runtime token map, so tool
  identity resolution treats them exactly like config-registered tokens.
Volatile state: an engine restart requires Gemini to re-authenticate. Declared
tradeoff — persistence is a hardening step, not a correctness gap."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    OAuthAuthorizationServerProvider,
    OAuthToken,
)
from mcp.shared.auth import OAuthClientInformationFull

CODE_TTL = 600  # seconds
TOKEN_TTL = 3600 * 24 * 30  # 30 days


@dataclass
class IssuedCode:
    code: str
    client_id: str
    redirect_uri: str
    scopes: list[str]
    expires_at: float
    code_challenge: str | None = None


@dataclass
class IssuedToken:
    token: str
    client_id: str
    scopes: list[str]
    expires_at: float
    refresh: str | None = field(default=None)


class StaticOAuthProvider(OAuthAuthorizationServerProvider):
    """OAuth provider over in-memory state.

    preauthorized: config-registered static bearer tokens (token -> consumer) —
    they verify at the transport edge exactly like OAuth-issued tokens.
    runtime_tokens: shared reference to the engine's token map — issued access
    tokens are minted into it so tool identity resolution treats them exactly
    like config-registered tokens."""

    def __init__(
        self,
        preauthorized: dict[str, str],
        runtime_tokens: dict[str, str],
        static_clients: dict[str, Any] | None = None,
    ):
        self._preauthorized = preauthorized
        self._runtime_tokens = runtime_tokens
        self._static_clients = static_clients or {}
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._codes: dict[str, IssuedCode] = {}
        self._tokens: dict[str, IssuedToken] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info

    async def authorize(self, client: OAuthClientInformationFull, params: Any) -> str:
        code = secrets.token_urlsafe(32)
        self._codes[code] = IssuedCode(
            code=code,
            client_id=client.client_id,
            redirect_uri=str(params.redirect_uri),
            scopes=params.scopes or [],
            expires_at=time.time() + CODE_TTL,
            code_challenge=params.code_challenge,
        )
        return params.redirect_uri

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        issued = self._codes.get(authorization_code)
        if (
            issued is None
            or issued.expires_at < time.time()
            or issued.client_id != client.client_id
        ):
            return None
        return AuthorizationCode(
            code=issued.code,
            client_id=issued.client_id,
            redirect_uri=issued.redirect_uri,
            redirect_uri_provided_explicitly=True,
            code_challenge=issued.code_challenge,
            scopes=issued.scopes,
            expires_at=issued.expires_at,
        )

    def _mint(self, client_id: str, scopes: list[str]) -> OAuthToken:
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        expires_in = TOKEN_TTL
        self._tokens[access] = IssuedToken(
            token=access, client_id=client_id, scopes=scopes, expires_at=time.time() + expires_in
        )
        self._tokens[refresh] = IssuedToken(
            token=refresh,
            client_id=client_id,
            scopes=scopes,
            expires_at=time.time() + expires_in * 2,
        )
        # mint into the engine's runtime token map so tool identity resolution
        # treats the issued token exactly like a config-registered bearer token;
        # static_clients pin a client to a consumer, DCR clients default to gemini
        consumer = self._static_clients.get(client_id, "gemini")
        self._runtime_tokens[access] = consumer
        self._runtime_tokens[refresh] = consumer
        return OAuthToken(
            access_token=access, token_type="Bearer", expires_in=expires_in, refresh_token=refresh
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        if authorization_code is None:
            raise ValueError("invalid authorization code")
        issued = self._codes.pop(authorization_code.code, None)
        if (
            issued is None
            or issued.expires_at < time.time()
            or issued.client_id != client.client_id
        ):
            raise ValueError("invalid authorization code")
        return self._mint(client.client_id, authorization_code.scopes)

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
        scopes: list[str] | None,
    ) -> OAuthToken:
        issued = self._tokens.get(refresh_token)
        if (
            issued is None
            or issued.expires_at < time.time()
            or issued.client_id != client.client_id
        ):
            raise ValueError("invalid refresh token")
        return self._mint(client.client_id, scopes or issued.scopes)

    async def load_access_token(self, token: str) -> AccessToken | None:
        # config-registered static tokens verify as preauthorized grants
        pre = self._preauthorized.get(token)
        if pre is not None:
            return AccessToken(token=token, client_id=pre, scopes=[], expires_at=None)
        issued = self._tokens.get(token)
        if issued is None or issued.expires_at < time.time():
            return None
        return AccessToken(
            token=token,
            client_id=issued.client_id,
            scopes=issued.scopes,
            expires_at=issued.expires_at,
        )

    async def load_refresh_token(self, refresh_token: str):
        issued = self._tokens.get(refresh_token)
        if issued is None or issued.expires_at < time.time():
            return None
        return issued

    async def revoke_token(self, token: AccessToken | str) -> None:
        t = token.token if hasattr(token, "token") else token
        self._tokens.pop(t, None)
