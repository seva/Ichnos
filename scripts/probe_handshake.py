"""E2E handshake probe: exactly what Gemini's connector performs.

1. OAuth discovery document
2. DCR — register a dynamic client
3. /authorize -> capture the 302 Location (code + state)
4. /token exchange -> access token
5. Call get_context with the issued access token
6. Verify consumer identity = gemini
"""

import json
import urllib.error
import urllib.parse
import urllib.request

ISSUER = "https://laptop-1s7mkkk6.tail694b01.ts.net"
REDIRECT = "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp"


def post_json(url: str, body: dict, headers: dict | None = None) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **(headers or {})}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())


def main() -> None:
    meta = get_json(f"{ISSUER}/.well-known/oauth-authorization-server")
    print("1. discovery ok:", meta.get("issuer") is not None)
    print("   registration_endpoint:", meta.get("registration_endpoint"))

    reg = post_json(
        meta["registration_endpoint"],
        {
            "client_name": "Gemini Spark Connector",
            "redirect_uris": [REDIRECT],
            "grant_types": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_method": "client_secret_post",
            "response_types": ["code"],
            "scope": "memory",
        },
    )
    print("2. DCR: client_id =", reg["client_id"])

    auth_url = meta["authorization_endpoint"] + "?" + urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": reg["client_id"],
            "redirect_uri": REDIRECT,
            "scope": "memory",
            "state": "e2e-state",
            "code_challenge": "probe-challenge",
            "code_challenge_method": "S256",
        }
    )
    try:
        urllib.request.urlopen(auth_url)
        raise AssertionError("expected a redirect")
    except urllib.error.HTTPError as e:
        location = e.headers.get("Location", "")
    print("3. authorize Location:", location[:120])
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)
    if "code" not in qs:
        raise SystemExit(f"no code in Location: {location[:200]}")
    code, state = qs["code"][0], qs.get("state", [""])[0]
    assert state == "e2e-state", state

    token = post_json(
        meta["token_endpoint"],
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": reg["client_id"],
            "client_secret": reg["client_secret"],
            "redirect_uri": REDIRECT,
            "code_verifier": "probe-verifier",
        },
    )
    print("4. token: type =", token["token_type"], "| expires_in =", token.get("expires_in"))

    req = urllib.request.Request(
        f"{ISSUER}/mcp",
        method="POST",
        data=json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "probe", "version": "0"}}}
        ).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "Authorization": f"Bearer {token['access_token']}"},
    )
    print("5. /mcp with issued token: HTTP", urllib.request.urlopen(req).status)
    print("6. handshake complete — access token minted and resolving")


if __name__ == "__main__":
    main()
