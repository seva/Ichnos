# Consumer Registration — Interface Notes (Phase 0)

**Status: registration pattern CONFIRMED (proven in live operation with `grok-research-mcp`); scoping model and trigger semantics PROPOSED — ratified here as the Phase 0 design the Phase 1 tool contract implements.**

_Last verified: 2026-09-15_

---

## Registration pattern

Two consumers classes exist today; both registration paths are proven:

| Path | Mechanism | Evidence |
|---|---|---|
| Claude-compatible runners (`claude`, opencode) | `claude mcp add-json <name> '<json>'` — full server config as JSON, including env vars; registered at user scope in `~/.claude.json` | `grok-research-mcp` runs live in Claude/opencode sessions via this path; the memory MCP service (`mcp-memory-service`, sqlite_vec backend) likewise |
| OpenClaw gateway | `openclaw mcp set` (gateway-native MCP registration) | Handoff asset: OpenClaw gateway is the first consumer; `grok-research-mcp` is registered through the gateway path |

Practical notes (recorded from prior feedback, in force):
- `claude mcp add-json` is the correct form for servers that need env vars; `claude mcp add -e` mishandles the server name.
- MCP startup cost is real: the grok-research-mcp subprocess adds ~7s to client startup. CCE must keep startup lazy/cheap — heavy imports deferred until first tool call.
- Registration is the **sanction record**: a consumer exists for the engine only when it is registered. There is no anonymous access path to design or defend.

## Per-consumer scoping model

Consumer identity = the registration name (plus a per-registration scope grant). Scoping is enforced in the MCP server at request time, not by the client.

| Scope level | Serves | Use |
|---|---|---|
| `full` | all registered channels, live reads | the operator's own coding agents (OpenClaw, local agents) |
| `channels:[...]` | only the named channels | narrow consumers (a web surface that needs calendar, not mail) |
| `summary` | reduced payload (no raw transcript/message bodies) | surfaces where payload size or sensitivity is a concern |

Rules:
- Scope is granted at registration and changed only by the Owner (sanction class, recorded on the relevant issue).
- An unregistered consumer receives nothing — not an error payload, nothing (terminal bound, `docs/scope.md`).
- The server never trusts client-declared identity; identity comes from the transport's registration binding.

## "On prompt" trigger semantics (the tool contract)

The engine exposes one primary tool (draft name `get_context`) plus per-channel explicit reads. Semantics the Phase 1 contract must implement:

- **Freshness is per channel.** Each channel carries a TTL parameter (values set by `docs/channel-matrix.md`). A prompt-time read serves from cache within TTL; past TTL it re-reads live.
- **Live-read default on prompt.** The default call re-reads stale channels and serves fresh ones from cache — the prompt always gets the freshest state the fast-path allows without blocking on slow channels (slow reads return the cached value marked stale, then refresh in the background).
- **Staleness is explicit, never silent.** Every payload marks per-channel `{as_of, stale}`. A failed channel read yields `stale` with the last-known value and the failure reason — never an omitted channel, never fabricated content.
- **No standing subscriptions in L2.** "On prompt" means reads happen at prompt time; push/webhook delivery is out of scope until a consumer needs it (revisit at L4+).

## Deferred

- Per-channel TTL values and the channel inventory — `docs/channel-matrix.md` (this doc's parameters reference it; it does not duplicate it).
- Web-surface consumer identity (what identity means when the consumer is a browser page) — `IMPLEMENTATION.md` Open Question 3, resolved before L5.
- OpenClaw-side trigger surface (how the gateway decides to call `get_context`) — Phase 1 integration task, not a Phase 0 output.
