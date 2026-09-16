"""GitHub fast-path adapter: authenticated read of the operator's developer context."""

from __future__ import annotations

import httpx
import pytest
import respx

from cce_server.adapters.github import BASE_URL, GitHubAdapter, TokenUnavailable

TOKEN = {"value": "test-token-123"}


def mock_github(respx_mock: respx.Router) -> None:
    respx_mock.get(f"{BASE_URL}/user").mock(
        return_value=httpx.Response(
            200, json={"login": "seva", "html_url": "https://github.com/seva"}
        )
    )
    respx_mock.get(f"{BASE_URL}/issues").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "number": 2,
                    "title": "Phase 0 — CCE discovery",
                    "html_url": "https://github.com/seva/Ichnos/issues/2",
                    "repository_url": "https://api.github.com/repos/seva/Ichnos",
                    "updated_at": "2026-09-15T00:00:00Z",
                }
            ],
        )
    )
    respx_mock.get(f"{BASE_URL}/search/issues").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "number": 10,
                        "title": "Add seeding",
                        "html_url": "https://github.com/seva/hearth-interface/pull/10",
                        "repository_url": "https://api.github.com/repos/seva/hearth-interface",
                        "updated_at": "2026-09-14T00:00:00Z",
                    }
                ]
            },
        )
    )


@respx.mock
async def test_read_returns_context_shape():
    mock_github(respx)
    adapter = GitHubAdapter(token=TOKEN["value"])
    ctx = await adapter.read()
    assert ctx["user"] == "seva"
    assert ctx["assigned_issues"][0]["repo"] == "seva/Ichnos"
    assert ctx["assigned_issues"][0]["number"] == 2
    assert ctx["assigned_issues"][0]["title"] == "Phase 0 — CCE discovery"
    assert ctx["review_requested_prs"][0]["repo"] == "seva/hearth-interface"


@respx.mock
async def test_token_is_sent_as_bearer():
    mock_github(respx)
    adapter = GitHubAdapter(token=TOKEN["value"])
    await adapter.read()
    for route in respx.routes:
        if route.called:
            assert route.calls.last.request.headers["Authorization"] == f"Bearer {TOKEN['value']}"


@respx.mock
async def test_empty_results_are_not_errors():
    respx.get(f"{BASE_URL}/user").mock(return_value=httpx.Response(200, json={"login": "seva"}))
    respx.get(f"{BASE_URL}/issues").mock(return_value=httpx.Response(200, json=[]))
    respx.get(f"{BASE_URL}/search/issues").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    adapter = GitHubAdapter(token="t")
    ctx = await adapter.read()
    assert ctx["assigned_issues"] == []
    assert ctx["review_requested_prs"] == []


@respx.mock
async def test_http_error_propagates_to_channel_layer():
    respx.get(f"{BASE_URL}/user").mock(
        return_value=httpx.Response(401, json={"message": "Bad credentials"})
    )
    respx.get(f"{BASE_URL}/issues").mock(return_value=httpx.Response(200, json=[]))
    respx.get(f"{BASE_URL}/search/issues").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    adapter = GitHubAdapter(token="bad")
    with pytest.raises(httpx.HTTPStatusError):
        await adapter.read()


async def test_missing_token_raises_before_any_call(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr("cce_server.adapters.github._GH_LOCATIONS", ())
    adapter = GitHubAdapter()
    with pytest.raises(TokenUnavailable):
        await adapter.read()


@respx.mock
async def test_gh_cli_token_fallback(monkeypatch):
    class FakeCompleted:
        stdout = "cli-token\n"

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "gh" if name == "gh" else None)
    monkeypatch.setattr(
        "subprocess.run",
        lambda *a, **k: FakeCompleted(),
    )
    mock_github(respx)
    adapter = GitHubAdapter()
    ctx = await adapter.read()
    assert ctx["user"] == "seva"
    assert respx.routes[0].calls.last.request.headers["Authorization"] == "Bearer cli-token"


async def test_gh_cli_failure_raises_token_unavailable(monkeypatch):
    import subprocess

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "gh" if name == "gh" else None)

    def boom(*a, **k):
        raise subprocess.SubprocessError("gh not found")

    monkeypatch.setattr("subprocess.run", boom)
    adapter = GitHubAdapter()
    with pytest.raises(TokenUnavailable, match="gh CLI token resolution failed"):
        await adapter.read()


@respx.mock
async def test_gh_subprocess_never_inherits_transport_stdin(monkeypatch):
    """Property (terminal-bound adjacent): the token subprocess must never see the MCP pipe."""
    import subprocess

    captured = {}

    class FakeCompleted:
        stdout = "tok\n"

    def fake_run(cmd, **kwargs):
        captured.update(kwargs)
        return FakeCompleted()

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "gh" if name == "gh" else None)
    monkeypatch.setattr("subprocess.run", fake_run)
    mock_github(respx)
    adapter = GitHubAdapter()
    await adapter.read()
    assert captured["stdin"] == subprocess.DEVNULL


def test_gh_location_fallback_is_deterministic(monkeypatch, tmp_path):
    """which() misses, but a standard install location exists -> used; otherwise TokenUnavailable."""
    from cce_server.adapters.github import _gh_command

    fake = tmp_path / "gh.exe"
    fake.write_bytes(b"")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr("cce_server.adapters.github._GH_LOCATIONS", (str(fake),))
    assert _gh_command() == [str(fake)]
    monkeypatch.setattr("cce_server.adapters.github._GH_LOCATIONS", ())
    with pytest.raises(TokenUnavailable, match="not found on PATH"):
        _gh_command()


@respx.mock
async def test_env_token_used_without_gh(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    mock_github(respx)
    adapter = GitHubAdapter()
    ctx = await adapter.read()
    assert ctx["user"] == "seva"
    assert respx.routes[0].calls.last.request.headers["Authorization"] == "Bearer env-token"


async def test_gh_cli_empty_output_raises_token_unavailable(monkeypatch, tmp_path):
    class FakeCompleted:
        stdout = "  \n"

    fake = tmp_path / "gh.exe"
    fake.write_bytes(b"")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr("cce_server.adapters.github._GH_LOCATIONS", (str(fake),))
    monkeypatch.setattr("subprocess.run", lambda *a, **k: FakeCompleted())
    adapter = GitHubAdapter()
    with pytest.raises(TokenUnavailable, match="empty output"):
        await adapter.read()
