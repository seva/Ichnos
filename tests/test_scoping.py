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
