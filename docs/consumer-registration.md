# Consumer Registration — Interface Notes (Phase 0)

**Status: claude-compatible registration path CONFIRMED (grok-research-mcp runs live via `claude mcp add-json`); OpenClaw gateway path MECHANISM EXISTS, UNPROVEN — `openclaw mcp set` is a real command, but no grok-research registration is observable in `openclaw.json` (mcp.servers contains only `memory`; the "grok" entries are an agent definition). Proving the gateway path is the L2 rung itself, a Phase 1 integration task. Scoping model and trigger semantics PROPOSED — the Phase 0 design Phase 1 implements; per-channel TTL values belong to `docs/channel-matrix.md` (next Phase 0 task, not yet written).**

_Last verified: 2026-09-15_

---

## Registration pattern

Two consumer classes exist today; one registration path is proven, one unproven:

| Path | Mechanism | Evidence |
|---|---|---|
| Claude-compatible runners (`claude`, opencode) | `claude mcp add-json <name> '<json>'` — full server config as JSON, including env vars; registered at user scope in `~/.claude.json` | **CONFIRMED** — `grok-research-mcp` runs live in Claude/opencode sessions via this path; the memory MCP service (`mcp-memory-service`, sqlite_vec backend) likewise |
| OpenClaw gateway | `openclaw mcp set` (gateway-native MCP registration; command verified to exist) | **UNPROVEN** — no MCP registration of grok-research observable in `openclaw.json`; proof is a Phase 1 integration task (the L2 rung) |

Practical notes:
- `claude mcp add-json` is the correct form for servers that need env vars; `claude mcp add -e` mishandles the server name.
- MCP subprocess init measurably slows client startup (observed ~7s in an April 2026 opencode cliBackend measurement — prior substrate, **UNMEASURED here**; treat as a shape warning, not a number). CCE must keep startup lazy/cheap — heavy imports deferred until first tool call.
- Registration is the **sanction record**: a consumer exists for the engine only when it is registered.

## Per-consumer scoping model

Consumer identity = the registration name (plus a per-registration scope grant). Scoping is enforced in the MCP server at request time, not by the client.

| Scope level | Serves | Use |
|---|---|---|
| `full` | all registered channels, live reads | the operator's own coding agents (OpenClaw, local agents) |
| `channels:[...]` | only the named channels | narrow consumers (a web surface that needs calendar, not mail) |
| `summary` | reduced payload (no raw transcript/message bodies) | surfaces where payload size or sensitivity is a concern |

Rules:
- Scope is granted at registration and changed only by the Owner (sanction class, recorded on the relevant issue).
- An unregistered or unauthenticated connection is rejected at the transport layer (MCP auth failure / unknown tool) — it receives no context data under any scope level (terminal bound, `docs/scope.md`).
- The server never trusts client-declared identity; identity comes from the transport's registration binding.

## "On prompt" trigger semantics (the tool contract)

The engine exposes one primary tool (draft name `get_context`) plus per-channel explicit reads. Semantics the Phase 1 contract must implement:

- **Freshness is per channel.** Each channel carries a TTL parameter (values set by `docs/channel-matrix.md`). A prompt-time read serves from cache within TTL; past TTL it re-reads live.
- **Prompt-time reads only at L2.** No background refresh, no standing processes — the server's lifetime is the client session (stdio), and all work happens inside the prompt-time call. A stale channel is re-read synchronously at prompt time, bounded by a per-channel timeout (values from `docs/channel-matrix.md`). (Background refresh is an L4+ option; introducing it requires re-opening this contract — it changes failure observability.)
- **Cold cache.** On first read of a channel (no cached value), the read is live-or-timeout like any stale read. There is no "serve cached" case — the channel result is either a live value or an explicit unavailable marker.
- **Staleness and failure are explicit, never silent.** Every payload marks per-channel `{as_of, stale}`. A timed-out or failed read yields that channel marked unavailable, with `{reason, last_as_of}` — the last-known value if one exists, an empty payload if none. Never an omitted channel, never fabricated content. A failure is observable at the next read even though the failure itself happened server-side.
- **Read cost.** The calling consumer's prompt pays for the freshness it requests: live re-reads happen synchronously in the call, bounded by the per-channel timeout. There is no unbounded server-side work — the timeout caps what any single prompt can spend per channel. (Open Question 5 resolved: the consumer pays, at prompt time, up to the timeout.)
- **No standing subscriptions in L2.** "On prompt" means reads happen at prompt time; push/webhook delivery is out of scope until a consumer needs it (revisit at L4+).

## Deferred

- Per-channel TTL values and the channel inventory — `docs/channel-matrix.md` (this doc's parameters reference it; it does not duplicate it).
- Web-surface consumer identity (what identity means when the consumer is a browser page) — `IMPLEMENTATION.md` Open Question 3, resolved before L5.
- OpenClaw-side trigger surface (how the gateway decides to call `get_context`) — Phase 1 integration task, not a Phase 0 output.
