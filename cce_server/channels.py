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
    _cached_at: float | None = field(default=None, repr=False)  # monotonic; TTL clock only

    async def get(self, now: float | None = None) -> ChannelReading:
        now = time.monotonic() if now is None else now
        cached, cached_at = self._cached_reading, self._cached_at
        if (
            cached is not None
            and not cached.unavailable
            and cached_at is not None
            and now - cached_at < self.config.ttl_seconds
        ):
            return cached
        if self.adapter is None:
            return self._unavailable(now, "not-configured")
        wall = time.time()
        try:
            data = await asyncio.wait_for(self.adapter(), timeout=self.config.timeout_seconds)
        except TimeoutError:
            return self._unavailable(now, "timeout")
        except Exception as exc:  # noqa: BLE001 — adapter failures are channel states, not crashes
            return self._unavailable(now, f"read-failed: {exc}")
        reading = ChannelReading(as_of=wall, stale=False, data=data)
        self._cached_reading = reading
        self._cached_at = now
        return reading

    def _unavailable(self, now: float, reason: str) -> ChannelReading:
        cached = self._cached_reading
        has_data = cached is not None and cached.data is not None
        reading = ChannelReading(
            as_of=time.time(),
            stale=True,
            data=cached.data if has_data else None,
            reason=reason,
            last_as_of=cached.as_of if has_data else None,
            unavailable=True,
        )
        if has_data:
            self._cached_reading = ChannelReading(
                as_of=cached.as_of,
                stale=True,
                data=cached.data,
            )
        return reading
