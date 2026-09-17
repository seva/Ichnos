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

import json
import os
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
        persist_path: str | None = None,
    ):
        self._preauthorized = preauthorized
        self._runtime_tokens = runtime_tokens
        # static_clients pins OAuth client_id -> consumer (issued tokens mint to that consumer)
        self._static_clients = static_clients or {}
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._codes: dict[str, IssuedCode] = {}
        self._tokens: dict[str, IssuedToken] = {}
        self._persist_path = persist_path
        if persist_path:
            self._load_persisted()

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
        # the returned string IS the Location: the authorization code and the
        # client's state must ride back as query parameters — a bare redirect
        # URI leaves Google's relay with nothing to relay ("A URI fragment or
        # query string must be set")
        separator = "&" if "?" in str(params.redirect_uri) else "?"
        location = f"{params.redirect_uri}{separator}code={code}"
        if params.state:
            location += f"&state={params.state}"
        return location

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
        consumer = (
            self._static_clients.get(client_id, {}).get("consumer", "gemini")
            if isinstance(self._static_clients.get(client_id), dict)
            else self._static_clients.get(client_id, "gemini")
        )
        self._runtime_tokens[access] = consumer
        self._runtime_tokens[refresh] = consumer
        self._persist()
        return OAuthToken(
            access_token=access, token_type="Bearer", expires_in=expires_in, refresh_token=refresh
        )

    def _persist(self) -> None:
        """Save issued tokens to disk so they survive engine restarts."""
        if not self._persist_path:
            return
        data = {
            t: {"client_id": i.client_id, "scopes": i.scopes, "expires_at": i.expires_at}
            for t, i in self._tokens.items()
        }
        consumers = dict(self._runtime_tokens)
        with open(self._persist_path, "w", encoding="utf-8") as f:
            json.dump({"tokens": data, "consumers": consumers}, f)

    def _load_persisted(self) -> None:
        """Load issued tokens from disk (called at startup — tokens survive restarts)."""
        if not self._persist_path or not os.path.exists(self._persist_path):
            return
        with open(self._persist_path, encoding="utf-8") as f:
            data = json.load(f)
        for t, info in data.get("tokens", {}).items():
            self._tokens[t] = IssuedToken(
                token=t,
                client_id=info["client_id"],
                scopes=info.get("scopes", []),
                expires_at=info["expires_at"],
            )
        for t, consumer in data.get("consumers", {}).items():
            self._runtime_tokens[t] = consumer

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
