"""Consumer registry: scope model from registration config; identity never client-supplied."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class UnregisteredConsumer(Exception):
    """Raised for a consumer absent from the registration config — it receives no context data."""


@dataclass(frozen=True)
class ConsumerScope:
    consumer: str
    level: str  # "full" | "channels" | "summary"
    channels: list[str] | None = None

    @property
    def summary(self) -> bool:
        return self.level == "summary"

    def allowed_channels(self, requested: list[str]) -> list[str]:
        if self.level == "channels":
            allowed = set(self.channels or [])
            return [c for c in requested if c in allowed]
        return list(requested)


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
            )
        return cls(consumers=consumers)

    def resolve(self, consumer: str) -> ConsumerScope:
        scope = self.consumers.get(consumer)
        if scope is None:
            raise UnregisteredConsumer(consumer)
        return scope
