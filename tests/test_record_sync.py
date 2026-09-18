"""Record-sync enforcer (Revision escalation, fired 2026-09-15).

The record-staleness class recurred twice (ARCHITECTURE.md stale at d9e17df;
AGENTS.md/scope.md stale at 258886e). Per CYCLE.md step 5, the response to a
recurrence is an executing enforcer, not another local repair. These tests run
on every suite execution: a commit that advances the project's state without
syncing the constitutional records fails here.

Pin discipline: when a state change makes a rule below stale, updating the rule
is part of the same commit as the state change — the test failing red is the
gate that forces the sync.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_scope_position_matches_reached_state():
    """AGENTS.md must state the current reached rung; no superseded framing."""
    agents = read("AGENTS.md")
    assert (
        "L3 reached (multi-channel: github + memory live; second consumer openclaw proven)"
        in agents
    )
    assert "next rung is L4" in agents
    assert "against OpenClaw" not in agents


def test_scope_md_carries_the_opencode_ruling_everywhere():
    """scope.md must not retain the superseded OpenClaw-first framing in any band."""
    scope = read("docs/scope.md")
    assert "First: OpenClaw gateway" not in scope
    assert "OpenClaw consumes it" not in scope
    assert "opencode consumes it live" in scope
    assert "First live consumer: **opencode**" in scope


def test_substrate_options_include_headless_first():
    """The display-isolation question set carries the headless-first question."""
    scope = read("docs/scope.md")
    assert "headless-on-host vs WSLg vs Hyper-V vs Docker+VNC" in scope


def test_deferred_debt_pointers_name_their_issue():
    """Debt pointers must name issue numbers — name-only references are unverifiable."""
    impl = read("IMPLEMENTATION.md")
    assert "WhatsApp integration deferred to its own tentative future decision (issue #3)" in impl


def test_whatsapp_row_marks_structural_arguments():
    """channel-matrix convention: argument claims are marked structural, not probed."""
    matrix = read("docs/channel-matrix.md")
    row = [line for line in matrix.splitlines() if "| WhatsApp |" in line]
    assert len(row) == 1
    assert "structural" in row[0]
    assert "issue #3" in row[0]


def test_architecture_md_auth_row_carries_persistence():
    """ARCHITECTURE.md auth row must reflect the current design — persistence supersedes volatile state."""
    arch = read("ARCHITECTURE.md")
    assert "oauth_tokens.json" in arch
    assert "persist_path" in arch


def test_architecture_md_components_cover_all_modules():
    """ARCHITECTURE.md must list every public module: server, config, auth, memory adapter, channels, registry, github."""
    arch = read("ARCHITECTURE.md")
    for module in (
        "cce_server.config",
        "cce_server.auth",
        "cce_server.channels",
        "cce_server.registry",
        "cce_server.adapters.github",
        "cce_server.adapters.memory",
    ):
        assert module in arch, f"missing module: {module}"
    assert "ProvenanceLedger" in arch
    assert "enrich_briefs" in arch


def test_consumer_registration_carries_current_state():
    """consumer-registration.md must not retain stale UNPROVEN or rejected-at-transport claims."""
    reg = read("docs/consumer-registration.md")
    assert "UNPROVEN" not in reg
    assert "rejected at the transport layer" not in reg
    assert "web" in reg  # the DCR-default web consumer
