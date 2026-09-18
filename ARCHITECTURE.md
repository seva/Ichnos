# Architecture

---

## Principles

**Separation of concerns** — auth, storage, transport, business logic, and interface layers are separate modules. No cross-cutting logic.

**Isolation of fragility** — unstable dependencies (external APIs, undocumented interfaces, third-party services) are contained in a single module. When they change, only that module updates. Nothing else knows about their internal shape.

**Security** — sensitive data never in plaintext on disk or in logs. Secrets never surfaced in tool or API output.

---

## Coding Hygiene

Guard clauses. Graceful degradation. No silent failures. Explicit error types.

Code as documentation — names and structure must be self-explanatory. Comments explain why, not what. Maximize semantic and cognitive ROI.

---

## Engineering Invariants

Enforced at audit (METHODOLOGY.md Post-Phase Audit, item 5). Deviations must be declared in `AGENTS.md` Conventions with rationale — undeclared violations are gaps.

**Boundary defense** — all untrusted input (HTTP parameters and bodies, queue messages, environment variables, files from other systems) passes a runtime schema parser at the ingestion boundary. Internal code trusts validated contracts and omits redundant defensive checks for guaranteed fields. Never pass unvalidated dynamic types into domain functions.

**Re-entrant mutations** — every state-altering operation (write endpoints, queue consumers, scheduled jobs) accepts an idempotency key or deterministic deduplication token, checked atomically before execution, with the result written back on completion. Financial and counter mutations never execute without an explicit transaction lock or idempotency guard.

**Non-destructive schema evolution** — migrations run Expand → dual-write → backfill → Contract, each in a distinct deployment; forward- and backward-compatible with N−1 running instances. Substrates that cannot contract (deployed smart contracts, append-only stores) substitute versioned parallel deployment; the substitution is recorded under Constraints.

**Vertical slice locality** — code grouped by domain feature, not technical layer. A feature slice co-locates its route, schema, domain rules, and queries. A single business-capability change touching more than three distinct folders is a design smell — reject or document the exception.

**Indirection cap** — at most three hops within a feature domain: handler → domain rule → persistence. Abstractions generalize only after the same logic occurs at ≥3 production call-sites (Rule of Three).

---

## Banned Patterns

| Pattern | Replacement |
|---|---|
| Generic repository abstraction over the ORM | Native ORM queries or type-safe compiled SQL directly in the slice |
| Premature microservices | Modular monolith with language-enforced visibility boundaries |
| Global DRY across bounded contexts | Context-local duplication; integrate through contracts, not shared models |
| Speculative OOP (AbstractFactory, Strategy/Visitor classes for one implementation) | Functions, guard clauses, native pattern matching |
| Unstructured logging | Structured logs with correlation/trace/tenant IDs propagated across async boundaries |
| Mock-testing internal boundaries; tautological tests asserting mock calls | Real ephemeral dependencies (Testcontainers or local instances); mocks only for external third-party APIs |

---

## System Diagram

Live data flow (github + memory channels live; gemini consumer live via Funnel; OpenClaw/opencode via stdio; fallback tier dormant).

```
REGISTERED CONSUMERS (sanctioned, scoped)               ENGINE (this project)

opencode ──────────┐                                    ┌─ fast-path adapters
OpenClaw gateway ──┤                                    │   ├─ github ── gh CLI (300s TTL)
gemini (web UI) ───┤                                    │   └─ memory ── mcp-memory service (query-driven)
local agents ──────┘    MCP / streamable-HTTP            │
                        stdio: CCE_CONSUMER binding      │
                        HTTP: bearer token → consumer    ├─ CCE MCP server
                        Tailscale Funnel (public HTTPS)  │    (OAuth 2.1: DCR + static creds)
                                                         │
                        auth checkpoints → HITL portal   └─ fallback: isolated display executor
                                                            (dormant — Phase 2, substrate unverified)
```

_Last verified: 2026-09-17_

---

## Components

| Component | Responsibility | Key interface |
|---|---|---|
| `cce_server` (MCP server) | Serves `get_context` + memory toolset over MCP; per-channel TTL/timeout/staleness contract; server-side per-consumer capability scoping; identity from the registration binding (stdio) or bearer token (HTTP), never client-supplied | `build_server(*, registry, channels, binding) -> FastMCP` (stdio); `build_http_server(*, registry, channels, tokens, public_url?) -> FastMCP` (streamable-HTTP); tools: `get_context(channels_requested?, query?)`, `memory_search(query, limit)`, `memory_recall(query, n_results)`, `memory_store(content, tags)`, `memory_delete(content_hash)` |
| `cce_server.config` (wiring) | One JSON config → running app; memory channel = first query-driven channel (retrieval against the prompt, no TTL cache); `McpMemoryCaller` = stateless JSON-RPC over HTTP to the memory service | `load_config(path) -> dict`; `build_channels(config) -> list[Channel]`; `build_app_from_config(path, binding?) -> FastMCP` (stdio); `build_http_app_from_config(path) -> FastMCP` (streamable-HTTP); `McpMemoryCaller(url)` with `async __call__(name, args) -> str` |
| `cce_server.adapters.github` (fast-path adapter) | GitHub channel: authenticated user, assigned open issues, review-requested open PRs; token ladder explicit arg → `GITHUB_TOKEN` env → gh CLI (standard-install fallback) | `GitHubAdapter(token?)` with `async read() -> {user, assigned_issues[], review_requested_prs[]}`; raises `TokenUnavailable` before any call when unresolvable |
| `cce_server.auth` (OAuth 2.1 provider) | Authorization server for the HTTP surface: DCR + static client credentials; auto-consent (single-operator, redirect URIs pinned); issues access+refresh tokens into the runtime token map; config-registered tokens verify as preauthorized grants; issued tokens persist to `~/.config/ichnos/oauth_tokens.json` (survive restarts; OAuth-minted only — config tokens not duplicated) | `StaticOAuthProvider(preauthorized, runtime_tokens, static_clients?, persist_path?)` — SDK's `OAuthAuthorizationServerProvider`; tokens persist across restarts |
| `cce_server.channels` (Channel contract) | Per-channel TTL/timeout/staleness semantics; query-driven channels (retrieval against the prompt, no TTL cache — every call is live); state channels serve cache within TTL; cold start = live-or-unavailable (never cached-serve) | `ChannelConfig(name, ttl_seconds, timeout_seconds, query_driven)`; `Channel.get(now?, query?) -> ChannelReading`; `ChannelReading.to_payload(include_data)` |
| `cce_server.registry` (consumer scoping) | Per-consumer scope: level (full/channels/summary), channel visibility, capability grants (least-privilege writes), snippet_length (server-side truncation) | `Registry.from_config(config) -> Registry`; `ConsumerScope.allowed_channels(requested) -> list[str]`; `ConsumerScope.can_write(channel) -> bool`; `ConsumerScope.snippet_length`; raises `UnregisteredConsumer` |
| `cce_server.adapters.memory` (memory toolset) | Memory channel: semantic search (query → top-k briefs), store (provenance-injected: `client_hostname` + `metadata.client`), delete (by hash), recall (time-anchored); **ProvenanceLedger**: append-only `{timestamp, hash, consumer}` record enriching briefs with the client label at read time (the service doesn't return provenance on retrieve); service failures → `MemoryServiceError`, converted by the channel layer | `MemoryAdapter(caller)` with `async search/recall/store/delete`; `ProvenanceLedger(path)` with `record(hash, consumer)` / `lookup(hash)`; `enrich_briefs(briefs, ledger)` adds `client` label; raises `MemoryServiceError` |
| `cce_server.auth` (OAuth 2.1 provider) | Authorization server for the HTTP surface: DCR + static client credentials; auto-consent (single-operator, redirect URIs pinned); issues access+refresh tokens into the runtime token map; config-registered tokens verify as preauthorized grants; **issued tokens persist to `~/.config/ichnos/oauth_tokens.json`** (survive restarts; OAuth-minted only — config tokens not duplicated) | `StaticOAuthProvider(preauthorized, runtime_tokens, static_clients?, persist_path?)` — SDK's `OAuthAuthorizationServerProvider`; tokens persist across restarts |

_Last verified: 2026-09-17_

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Client protocol | MCP | Client-agnostic by invariant; both transports (stdio + streamable-HTTP) proven live |
| Retrieval precedence | API/protocol fast-path default; OS-level inspection as universal fallback | Handoff invariant; compiled per channel in `docs/channel-matrix.md` — structural, not per-prompt |
| Display isolation | Structural — separate virtual display substrate; never primary-session attachment | Terminal bound (`docs/scope.md`); substrate chosen by Phase 2 (dormant debt) |
| Adapter write posture | Read-only observers for external channels; read/write for the engine's own curated memory store | Owner sanction 2026-09-15 (issue #2); the memory store is the engine's substrate, not an external channel |
| Auth seeding | Browser-mediated extraction (ABE era): encrypted profile copies only, plaintext memory-resident host→VM, pipe transport, never plaintext on disk, in logs, or in tool output | Terminal bound (`docs/scope.md`); re-derived after Near fired on DPAPI (`docs/auth-seeding.md`) |
| Consumer access | Registered (owner-sanctioned) consumers only, scoped per consumer with least-privilege capability grants | Owner sanction 2026-09-15 (issue #2); write requires explicit per-consumer grant (default read-only) |
| OAuth 2.1 on the public surface | Auto-consent (single-operator, redirect URIs pinned); issued tokens persist to disk (survive restarts); unauthenticated requests default to the `web` consumer | Declared v1 tradeoffs (`cce_server/auth.py` docstring): auto-consent, Funnel-URL-as-access-gate; DCR + static credentials both supported; token persistence supersedes the volatile in-memory state |

---

## Constraints

- **Secrets/session material** never leave the OS credential store; never logged or surfaced in tool or API output (`docs/scope.md`, Terminal bound).
- **Fallback executor** never attaches to the primary session's input devices or viewport; isolation is enforced by the substrate, not process behavior.
- **Context** is served only to registered consumers, scoped per consumer; adapters never write to external channels (the memory store is the engine's substrate — read/write is the store's purpose).
- **Host**: Windows + WSL2 (Ubuntu) + Docker present; Hyper-V unverified — Phase 2 settles the display substrate.
- **Auth states are time-dependent**: seeded sessions expire and walled gardens change; adapters isolate drift (Isolation of fragility).
- **Memory store idempotency**: the mcp-memory service deduplicates identical content (returns no `content_hash` on duplicate store); delete is idempotent by hash. No explicit idempotency key required.

_Last verified: 2026-09-17_
