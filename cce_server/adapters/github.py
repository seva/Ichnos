"""GitHub fast-path adapter: the operator's developer context via the REST API.

Token resolution order: explicit constructor argument, then GITHUB_TOKEN env, then the
authenticated `gh` CLI. The token is used for Authorization headers only — never logged,
never surfaced in payloads (terminal bound)."""

from __future__ import annotations

import os
from typing import Any

import httpx

BASE_URL = "https://api.github.com"


class TokenUnavailable(Exception):
    """No GitHub token resolvable — the adapter refuses to call the API."""


_GH_LOCATIONS = (r"C:\Program Files\GitHub CLI\gh.exe",)


def _gh_command() -> list[str]:
    import shutil

    exe = shutil.which("gh")
    if exe:
        return [exe]
    for path in _GH_LOCATIONS:
        if os.path.exists(path):
            return [path]
    raise TokenUnavailable("gh CLI not found on PATH or standard install locations")


def _repo(repository_url: str) -> str:
    return repository_url.removeprefix(f"{BASE_URL}/repos/")


def _issue_brief(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo": _repo(item.get("repository_url", "")),
        "number": item.get("number"),
        "title": item.get("title"),
        "url": item.get("html_url"),
        "updated_at": item.get("updated_at"),
    }


class GitHubAdapter:
    def __init__(self, token: str | None = None) -> None:
        self._token = token

    def _resolve_token(self) -> str:
        if self._token:
            return self._token
        env = os.environ.get("GITHUB_TOKEN")
        if env:
            return env
        import subprocess

        try:
            result = subprocess.run(
                [*_gh_command(), "auth", "token"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
                stdin=subprocess.DEVNULL,  # never inherit the MCP stdio pipe
            )
        except (subprocess.SubprocessError, OSError) as exc:
            raise TokenUnavailable(f"gh CLI token resolution failed: {exc}") from exc
        token = result.stdout.strip()
        if not token:
            raise TokenUnavailable("gh auth token returned empty output")
        return token

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {self._resolve_token()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10.0,
        )

    async def read(self) -> dict[str, Any]:
        async with self._client() as client:
            user_resp = await client.get("/user")
            issues_resp = await client.get(
                "/issues", params={"filter": "assigned", "state": "open"}
            )
            prs_resp = await client.get(
                "/search/issues",
                params={
                    "q": f"review-requested:{user_resp.raise_for_status().json()['login']} is:pr is:open"
                },
            )
            user = user_resp.raise_for_status().json()
            issues = issues_resp.raise_for_status().json()
            prs = prs_resp.raise_for_status().json()
        return {
            "user": user["login"],
            "assigned_issues": [_issue_brief(i) for i in issues],
            "review_requested_prs": [_issue_brief(p) for p in prs.get("items", [])],
        }
