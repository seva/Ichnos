"""Memory toolset adapter: search/store/delete/recall over the memory MCP service.

Transport-thin by design — the adapter takes a ``caller(name, args) -> str`` callable
(the real one wraps an MCP ClientSession against ``http://127.0.0.1:8000/mcp``; tests
inject fakes). Provenance is injected on every write: the store always records which
consumer wrote what. Service failures surface as MemoryServiceError — the channel
layer converts them into explicit unavailable states."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

ToolCaller = Callable[[str, dict[str, Any]], Awaitable[str]]

PROVENANCE_KEY = "client"


class MemoryServiceError(Exception):
    """The memory service failed or answered unintelligibly — never a silent empty."""


def _parse(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise MemoryServiceError(f"malformed response from memory service: {exc}") from exc
    if not isinstance(parsed, dict):
        raise MemoryServiceError("malformed response from memory service: expected a JSON object")
    return parsed


def _brief(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": entry.get("content"),
        "tags": entry.get("tags", []),
        "metadata": entry.get("metadata", {}),
        "created_at": entry.get("created_at"),
        "hash": entry.get("content_hash"),
        "similarity": entry.get("similarity_score"),
    }


class MemoryAdapter:
    def __init__(self, caller: ToolCaller) -> None:
        self._caller = caller

    async def _call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            raw = await self._caller(name, args)
        except MemoryServiceError:
            raise
        except Exception as exc:
            raise MemoryServiceError(f"memory service failure: {exc}") from exc
        return _parse(raw)

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        parsed = await self._call("memory_retrieve_memory", {"query": query, "limit": limit})
        return [_brief(e) for e in parsed.get("results", [])]

    async def recall(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        parsed = await self._call("memory_recall_memory", {"query": query, "n_results": n_results})
        return [_brief(e) for e in parsed.get("results", [])]

    async def store(
        self,
        content: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        provenance: str = "gemini",
    ) -> str:
        meta = dict(metadata or {})
        meta[PROVENANCE_KEY] = provenance  # injected last: provenance is not client-forgeable
        parsed = await self._call(
            "memory_store_memory",
            {"content": content, "tags": tags or [], "metadata": meta},
        )
        return parsed.get("content_hash", "")

    async def delete(self, content_hash: str) -> bool:
        parsed = await self._call("memory_delete_memory", {"content_hash": content_hash})
        return bool(parsed.get("success", False))
