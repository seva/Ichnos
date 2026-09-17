"""Provenance ledger: append-only engine-side record of who wrote which memory.

The memory service does not return client_hostname/metadata on retrieve, so the
engine keeps its own ledger (hash -> consumer) and enriches briefs with it.
Covers the read-path provenance requirement: without this, the identity split
is engine-complete but consumer-invisible."""

from __future__ import annotations

import json

from cce_server.adapters.memory import ProvenanceLedger, enrich_briefs


def test_store_appends_ledger_entry(tmp_path):
    ledger_path = tmp_path / "provenance.jsonl"
    ledger = ProvenanceLedger(ledger_path)
    ledger.record("abc123", "grok")
    entries = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert entries[0]["hash"] == "abc123"
    assert entries[0]["consumer"] == "grok"
    assert "timestamp" in entries[0]


def test_lookup_returns_consumer_for_hash(tmp_path):
    ledger = ProvenanceLedger(tmp_path / "provenance.jsonl")
    ledger.record("abc123", "grok")
    ledger.record("def456", "gemini")
    assert ledger.lookup("abc123") == "grok"
    assert ledger.lookup("def456") == "gemini"
    assert ledger.lookup("unknown") is None


def test_ledger_survives_reopen(tmp_path):
    ledger_path = tmp_path / "provenance.jsonl"
    ProvenanceLedger(ledger_path).record("abc123", "grok")
    reopened = ProvenanceLedger(ledger_path)
    assert reopened.lookup("abc123") == "grok"


def test_last_write_wins_for_same_hash(tmp_path):
    ledger = ProvenanceLedger(tmp_path / "provenance.jsonl")
    ledger.record("abc123", "gemini")
    ledger.record("abc123", "grok")  # re-store overwrites the consumer attribution
    assert ledger.lookup("abc123") == "grok"


def test_enrich_briefs_adds_client_from_ledger(tmp_path):
    ledger = ProvenanceLedger(tmp_path / "provenance.jsonl")
    ledger.record("abc123", "grok")
    briefs = [{"content": "x", "hash": "abc123"}, {"content": "y", "hash": "unknown-hash"}]
    enriched = enrich_briefs(briefs, ledger)
    assert enriched[0]["client"] == "grok"
    assert enriched[1]["client"] == "pre-ledger"  # sealed-epoch marker, never fabricated


def test_enrich_preserves_explicit_metadata_client(tmp_path):
    """When the service returns metadata.client, it wins over the ledger."""
    ledger = ProvenanceLedger(tmp_path / "provenance.jsonl")
    ledger.record("abc123", "grok")
    briefs = [{"content": "x", "hash": "abc123", "metadata": {"client": "claude"}}]
    enriched = enrich_briefs(briefs, ledger)
    assert enriched[0]["client"] == "claude"
