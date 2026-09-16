"""Consumer registry: scope model from registration config; identity never client-supplied."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class UnregisteredConsumer(PermissionError):
    """Raised for a consumer absent from the registration config — it receives no context data."""

    def __init__(self, consumer: str):
        super().__init__(f"unregistered consumer: {consumer}")


@dataclass(frozen=True)
class ConsumerScope:
    consumer: str
    level: str  # "full" | "channels" | "summary"
    channels: list[str] | None = None
    writable: list[str] | None = (
        None  # channels where write tools are exposed; None/empty = read-only
    )
    snippet_length: int | None = None  # brief content truncated to N chars when set

    @property
    def summary(self) -> bool:
        return self.level == "summary"

    def allowed_channels(self, requested: list[str]) -> list[str]:
        if self.level == "channels":
            allowed = set(self.channels or [])
            return [c for c in requested if c in allowed]
        return list(requested)

    def can_write(self, channel: str) -> bool:
        """Least privilege: write requires an explicit per-consumer grant."""
        return channel in (self.writable or [])


@dataclass(frozen=True)
class Registry:
    consumers: dict[str, ConsumerScope]

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> Registry:
        consumers: dict[str, ConsumerScope] = {}
        for name, spec in (config.get("consumers") or {}).items():
            level = spec.get("scope", "full")
            if level not in ("full", "channels", "summary"):
                raise ValueError(f"consumer {name}: unknown scope level {level!r}")
            consumers[name] = ConsumerScope(
                consumer=name,
                level=level,
                channels=spec.get("channels") if level == "channels" else None,
                writable=spec.get("writable") or [],
                snippet_length=spec.get("snippet_length"),
            )
        return cls(consumers=consumers)

    def resolve(self, consumer: str) -> ConsumerScope:
        scope = self.consumers.get(consumer)
        if scope is None:
            raise UnregisteredConsumer(consumer)
        return scope
