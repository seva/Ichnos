"""Memory toolset adapter: search/store/delete/recall over the memory MCP service.

Transport-thin by design — the adapter takes a ``caller(name, args) -> str`` callable
(the real one wraps a stateless JSON-RPC POST loop against the memory service; tests
inject fakes). Provenance is injected on every write: the store always records which
consumer wrote what. Service failures surface as MemoryServiceError — the channel
layer converts them into explicit unavailable states.

The service does not return provenance fields on retrieve, so the engine keeps an
append-only provenance ledger (ProvenanceLedger): every engine-mediated store logs
{timestamp, hash, consumer}, and search/recall briefs are enriched with the client
label from that ledger. Entries written before the ledger existed (or by surfaces
bypassing the engine) enrich as "pre-ledger" — the sealed epoch, never fabricated."""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ToolCaller = Callable[[str, dict[str, Any]], Awaitable[str]]

PROVENANCE_KEY = "client"


class MemoryServiceError(Exception):
    """The memory service failed or answered unintelligibly — never a silent empty."""


@dataclass
class ProvenanceLedger:
    """Append-only {timestamp, hash, consumer} record; last write wins per hash."""

    path: Path
    _index: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)
                self._index[entry["hash"]] = entry["consumer"]

    def record(self, content_hash: str, consumer: str) -> None:
        entry = {"timestamp": time.time(), "hash": content_hash, "consumer": consumer}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        self._index[content_hash] = consumer

    def lookup(self, content_hash: str) -> str | None:
        return self._index.get(content_hash)


def enrich_briefs(
    briefs: list[dict[str, Any]], ledger: ProvenanceLedger | None
) -> list[dict[str, Any]]:
    """Add the client label to briefs: explicit service metadata wins, then the
    ledger, then the sealed-epoch marker (pre-ledger or out-of-engine writes)."""
    for brief in briefs:
        meta = brief.get("metadata") or {}
        client = meta.get(PROVENANCE_KEY)
        if client is None and ledger is not None:
            client = ledger.lookup(brief.get("hash") or "")
        brief["client"] = client or "pre-ledger"
    return briefs


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
        parsed = await self._call("retrieve_memory", {"query": query, "limit": limit})
        return [_brief(e) for e in parsed.get("results", [])]

    async def recall(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        parsed = await self._call("recall_memory", {"query": query, "n_results": n_results})
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
            "store_memory",
            {
                "content": content,
                "tags": tags or [],
                "metadata": meta,
                "client_hostname": provenance,  # the service's native provenance field
            },
        )
        return parsed.get("content_hash", "")

    async def delete(self, content_hash: str) -> bool:
        parsed = await self._call("delete_memory", {"content_hash": content_hash})
        return bool(parsed.get("success", False))
