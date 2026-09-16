"""Contract semantics for a context channel: TTL, timeout, explicit staleness."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChannelConfig:
    name: str
    ttl_seconds: float
    timeout_seconds: float


@dataclass(frozen=True)
class ChannelReading:
    as_of: float
    stale: bool
    data: dict[str, Any] | None = None
    reason: str | None = None
    last_as_of: float | None = None
    unavailable: bool = False

    def to_payload(self, *, include_data: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "as_of": self.as_of,
            "stale": self.stale,
        }
        if self.unavailable:
            payload["unavailable"] = True
        if self.reason is not None:
            payload["reason"] = self.reason
        if self.last_as_of is not None:
            payload["last_as_of"] = self.last_as_of
        if include_data and self.data is not None:
            payload["data"] = self.data
        return payload


Adapter = Callable[[], Awaitable[dict[str, Any]]]


@dataclass
class Channel:
    config: ChannelConfig
    adapter: Adapter | None = None
    _cached_reading: ChannelReading | None = field(default=None, repr=False)

    async def get(self, now: float | None = None) -> ChannelReading:
        now = time.monotonic() if now is None else now
        cached = self._cached_reading
        if (
            cached is not None
            and not cached.unavailable
            and now - cached.as_of < self.config.ttl_seconds
        ):
            return cached
        if self.adapter is None:
            return self._unavailable(now, "not-configured", None)
        try:
            data = await asyncio.wait_for(self.adapter(), timeout=self.config.timeout_seconds)
        except TimeoutError:
            return self._unavailable(now, "timeout", now if cached else None)
        except Exception as exc:  # noqa: BLE001 — adapter failures are channel states, not crashes
            return self._unavailable(now, f"read-failed: {exc}", now if cached else None)
        reading = ChannelReading(as_of=now, stale=False, data=data)
        self._cached_reading = reading
        return reading

    def _unavailable(self, now: float, reason: str, last_as_of: float | None) -> ChannelReading:
        last = self._cached_reading.as_of if self._cached_reading else last_as_of
        has_data = self._cached_reading is not None and self._cached_reading.data is not None
        reading = ChannelReading(
            as_of=now,
            stale=True,
            data=self._cached_reading.data if has_data else None,
            reason=reason,
            last_as_of=last,
            unavailable=True,
        )
        if has_data:
            self._cached_reading = ChannelReading(
                as_of=self._cached_reading.as_of,
                stale=True,
                data=self._cached_reading.data,
            )
        return reading
