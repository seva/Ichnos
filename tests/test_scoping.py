"""Consumer scoping: full / channels-filter / summary; unregistered rejected with no context data."""

from __future__ import annotations

import pytest

from cce_server.registry import Registry, UnregisteredConsumer


def make_registry() -> Registry:
    return Registry.from_config(
        {
            "consumers": {
                "openclaw": {"scope": "full"},
                "web-cald": {"scope": "channels", "channels": ["github"]},
                "reader": {"scope": "summary"},
            }
        }
    )


def test_full_scope_resolves_all():
    scope = make_registry().resolve("openclaw")
    assert scope.level == "full"
    assert scope.channels is None
    assert scope.summary is False


def test_channels_scope_intersects():
    scope = make_registry().resolve("web-cald")
    assert scope.allowed_channels(["github", "telegram", "email"]) == ["github"]
    assert scope.allowed_channels(["email"]) == []


def test_unknown_consumer_gets_rejection():
    with pytest.raises(UnregisteredConsumer):
        make_registry().resolve("intruder")


def test_summary_scope_flagged():
    scope = make_registry().resolve("reader")
    assert scope.summary is True


def test_scope_changes_are_config_only():
    """Scope comes from registration config only — nothing client-supplied can widen it."""
    scope = make_registry().resolve("web-cald")
    assert scope.allowed_channels(["github", "telegram"]) == ["github"]


def test_unknown_scope_level_in_config_is_rejected():
    with pytest.raises(ValueError):
        Registry.from_config({"consumers": {"bad": {"scope": "everything"}}})


def make_capability_registry() -> Registry:
    return Registry.from_config(
        {
            "consumers": {
                "gemini": {"scope": "channels", "channels": ["memory"], "writable": ["memory"]},
                "openclaw": {"scope": "full"},
            }
        }
    )


def test_writable_defaults_to_read_only():
    """Least privilege: a consumer with no 'writable' list gets read-only on everything."""
    scope = make_capability_registry().resolve("openclaw")
    assert scope.can_write("memory") is False
    assert scope.can_write("github") is False


def test_writable_channels_explicitly_granted():
    scope = make_capability_registry().resolve("gemini")
    assert scope.can_write("memory") is True
    assert scope.can_write("github") is False  # write grant does not widen read visibility


def test_write_grant_does_not_widen_read_visibility():
    scope = make_capability_registry().resolve("gemini")
    assert scope.allowed_channels(["memory", "github"]) == ["memory"]


def make_split_registry() -> Registry:
    """The post-split consumer set: grok and claude as distinct identities."""
    return Registry.from_config(
        {
            "consumers": {
                "gemini": {
                    "scope": "channels",
                    "channels": ["memory"],
                    "writable": ["memory"],
                    "snippet_length": 200,
                },
                "grok": {
                    "scope": "channels",
                    "channels": ["memory"],
                    "writable": ["memory"],
                    "snippet_length": 200,
                },
                "claude": {
                    "scope": "channels",
                    "channels": ["memory"],
                    "writable": ["memory"],
                    "snippet_length": 200,
                },
                "web": {
                    "scope": "channels",
                    "channels": ["memory"],
                    "writable": ["memory"],
                    "snippet_length": 200,
                },
            }
        }
    )


def test_grok_consumer_resolves_with_parity():
    scope = make_split_registry().resolve("grok")
    assert scope.allowed_channels(["memory"]) == ["memory"]
    assert scope.can_write("memory") is True
    assert scope.snippet_length == 200


def test_claude_consumer_resolves_with_parity():
    scope = make_split_registry().resolve("claude")
    assert scope.allowed_channels(["memory"]) == ["memory"]
    assert scope.can_write("memory") is True


def test_identity_split_resolves_per_consumer():
    """Distinct consumers, same store: resolution is per-consumer, never shared."""
    reg = make_split_registry()
    assert reg.resolve("grok").consumer == "grok"
    assert reg.resolve("claude").consumer == "claude"
    assert reg.resolve("gemini").consumer == "gemini"
    with pytest.raises(UnregisteredConsumer):
        reg.resolve("gemini-spark")  # the OAuth client_id is not a consumer
