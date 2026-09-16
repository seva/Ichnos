"""Memory toolset adapter: search/store/delete/recall over the memory MCP service.

The adapter is transport-thin: it takes a tool-caller callable (the real one wraps
an MCP ClientSession; tests inject fakes). Provenance is injected on every write
so the store always records which consumer wrote what."""

from __future__ import annotations

import json

import pytest

from cce_server.adapters.memory import MemoryAdapter, MemoryServiceError

FAKE_SEARCH_RESPONSE = json.dumps(
    {
        "results": [
            {
                "content": "VixeYult model chain: glm-5.3-flash via openrouter",
                "tags": ["openclaw", "models"],
                "metadata": {"type": "fact"},
                "created_at": "2026-09-15T00:00:00",
                "content_hash": "abc123",
                "similarity_score": 0.82,
            },
            {
                "content": "Gateway restart required after sqlite auth edits",
                "tags": ["openclaw"],
                "metadata": {},
                "created_at": "2026-09-16T00:00:00",
                "content_hash": "def456",
                "similarity_score": 0.74,
            },
        ]
    }
)


def make_adapter(caller) -> MemoryAdapter:
    return MemoryAdapter(caller=caller)


async def test_search_maps_results_to_briefs():
    captured = {}

    async def caller(name, args):
        captured["name"], captured["args"] = name, args
        return FAKE_SEARCH_RESPONSE

    adapter = make_adapter(caller)
    briefs = await adapter.search("openclaw model chain", limit=5)
    assert captured["name"] == "retrieve_memory"
    assert captured["args"]["query"] == "openclaw model chain"
    assert captured["args"]["limit"] == 5
    assert briefs[0]["content"].startswith("VixeYult model chain")
    assert briefs[0]["tags"] == ["openclaw", "models"]
    assert briefs[0]["hash"] == "abc123"
    assert briefs[0]["similarity"] == 0.82
    assert len(briefs) == 2


async def test_store_injects_gemini_provenance():
    captured = {}

    async def caller(name, args):
        captured["name"], captured["args"] = name, args
        return json.dumps({"success": True, "content_hash": "newhash"})

    adapter = make_adapter(caller)
    h = await adapter.store("operator prefers dark mode", tags=["prefs"], metadata={"topic": "ui"})
    assert h == "newhash"
    assert captured["name"] == "store_memory"
    assert captured["args"]["content"] == "operator prefers dark mode"
    assert captured["args"]["tags"] == ["prefs"]
    assert captured["args"]["metadata"]["topic"] == "ui"
    assert (
        captured["args"]["metadata"]["client"] == "gemini"
    )  # provenance injected, user metadata preserved
    assert captured["args"]["client_hostname"] == "gemini"  # the service's native provenance field


async def test_delete_calls_service_with_hash():
    captured = {}

    async def caller(name, args):
        captured["name"], captured["args"] = name, args
        return json.dumps({"success": True})

    adapter = make_adapter(caller)
    ok = await adapter.delete("abc123")
    assert ok is True
    assert captured["name"] == "delete_memory"
    assert captured["args"] == {"content_hash": "abc123"}


async def test_recall_maps_time_based_results():
    async def caller(name, args):
        assert name == "recall_memory"
        assert args == {"query": "last week", "n_results": 3}
        return FAKE_SEARCH_RESPONSE

    adapter = make_adapter(caller)
    briefs = await adapter.recall("last week", n_results=3)
    assert len(briefs) == 2


async def test_service_failure_raises_memory_service_error():
    async def caller(name, args):
        raise ConnectionError("service down")

    adapter = make_adapter(caller)
    with pytest.raises(MemoryServiceError, match="service down"):
        await adapter.search("anything")


async def test_malformed_response_raises_memory_service_error():
    async def caller(name, args):
        return "this is not json at all"

    adapter = make_adapter(caller)
    with pytest.raises(MemoryServiceError, match="malformed"):
        await adapter.search("anything")
