"""Channel contract semantics: TTL freshness, timeout, explicit staleness, cold start."""

from __future__ import annotations

from cce_server.channels import Channel, ChannelConfig, ChannelReading


def make_channel(adapter=None, ttl=100.0, timeout=5.0) -> Channel:
    return Channel(
        config=ChannelConfig(name="test", ttl_seconds=ttl, timeout_seconds=timeout), adapter=adapter
    )


async def test_fresh_within_ttl_serves_cache_without_live_read():
    calls = []

    async def adapter():
        calls.append(1)
        return {"k": "v1"}

    ch = make_channel(adapter)
    r1 = await ch.get(now=1000.0)
    assert r1.stale is False and r1.data == {"k": "v1"}
    r2 = await ch.get(now=1000.0 + 99.9)
    assert r2.stale is False and r2.data == {"k": "v1"}
    assert len(calls) == 1  # no second live read within TTL


async def test_past_ttl_triggers_live_read():
    calls = []

    async def adapter():
        calls.append(1)
        return {"k": f"v{len(calls)}"}

    ch = make_channel(adapter)
    await ch.get(now=1000.0)
    r2 = await ch.get(now=1000.0 + 100.0)
    assert r2.stale is False and r2.data == {"k": "v2"}
    assert len(calls) == 2


async def test_live_failure_keeps_last_value_with_reason():
    state = {"calls": 0}

    async def adapter():
        state["calls"] += 1
        if state["calls"] == 1:
            return {"k": "v1"}
        raise RuntimeError("api down")

    ch = make_channel(adapter)
    await ch.get(now=1000.0)
    r = await ch.get(now=2000.0)
    assert r.unavailable is True
    assert r.stale is True
    assert r.data == {"k": "v1"}  # last-known value served
    assert "api down" in r.reason
    assert r.last_as_of == 1000.0
    # and the cached value is marked stale for subsequent reads
    again = await ch.get(now=2001.0)
    assert again.stale is True


async def test_timeout_marks_unavailable():
    import asyncio

    async def hanging():
        await asyncio.sleep(10)

    ch = make_channel(hanging, timeout=0.01)
    r = await ch.get(now=1000.0)
    assert r.unavailable is True
    assert r.reason == "timeout"
    assert r.data is None  # cold start: nothing to serve


async def test_cold_start_failure_is_unavailable_with_no_data():
    async def adapter():
        raise RuntimeError("boom")

    ch = make_channel(adapter)
    r = await ch.get(now=1000.0)
    assert r.unavailable is True
    assert r.data is None
    assert r.last_as_of is None
    assert "boom" in r.reason


async def test_not_configured_channel_is_unavailable():
    ch = make_channel(adapter=None)
    r = await ch.get(now=1000.0)
    assert r.unavailable is True
    assert r.reason == "not-configured"


async def test_payload_omits_data_when_summary():
    reading = ChannelReading(as_of=1.0, stale=False, data={"body": "x"})
    p = reading.to_payload(include_data=False)
    assert "data" not in p
    assert p["as_of"] == 1.0
