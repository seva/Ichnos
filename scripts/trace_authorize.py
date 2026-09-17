"""Fix validation: valid_scopes on ClientRegistrationOptions must include memory."""

import json
import urllib.error
import urllib.parse
import urllib.request

ISSUER = "https://laptop-1s7mkkk6.tail694b01.ts.net"
REDIRECT = "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post_json(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


reg = post_json(
    f"{ISSUER}/register",
    {
        "client_name": "trace",
        "redirect_uris": [REDIRECT],
        "grant_types": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_method": "client_secret_post",
        "response_types": ["code"],
        "scope": "memory",
    },
)
cid = reg["client_id"]
url = f"{ISSUER}/authorize?" + urllib.parse.urlencode(
    {
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": REDIRECT,
        "scope": "memory",
        "state": "s1",
        "code_challenge": "c",
        "code_challenge_method": "S256",
    }
)

opener = urllib.request.build_opener(NoRedirect)
try:
    resp = opener.open(url)
    print("unexpected direct 200")
except urllib.error.HTTPError as e:
    loc = e.headers.get("Location", "NONE")
    print("status:", e.code, "| Location:", loc[:200])
    if "code=" in loc:
        print(">>> CODE PRESENT — full handshake works")
