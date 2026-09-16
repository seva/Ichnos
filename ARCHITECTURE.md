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

Planned data flow (Phase 0 establishes the sources and precedence; components are built in Phases 1–4).

```
REGISTERED CONSUMERS (sanctioned, scoped)           ENGINE (this project)

OpenClaw gateway ──┐                                ┌─ fast-path adapters ──── channel APIs
web surfaces ──────┼── MCP ("context on prompt") ──► CCE MCP server ──┤   (docs/channel-matrix.md, Phase 0)
local agents ──────┘    context scoped per consumer  (context store)  │
                                                   └─ fallback: isolated virtual display executor
                                                      (walled gardens; never the primary session's
                                                       input devices or viewport)
                                                      └─ HITL portal (browser/VNC) — auth checkpoints
                                                         resolved by the operator
auth seeding: OS credential store (DPAPI) → display session — secrets never in plaintext
```

_Last verified: 2026-09-15 (planned; sources pinned by Phase 0)_

---

## Components

| Component | Responsibility | Key interface |
|---|---|---|
| `cce_server` (MCP server) | Serves `get_context` over MCP: per-channel TTL/timeout/staleness contract, server-side per-consumer scoping from registration config; identity from the `CCE_CONSUMER` registration binding, never client-supplied | `build_server(*, registry, channels, binding) -> FastMCP`; tool `get_context(channels_requested?) -> {consumer, summary, generated_at, channels: {name: {as_of (epoch), stale, data?, unavailable?, reason?, last_as_of?}}}`; console script `ichnos-cce` (stdio) |
| `cce_server.config` (wiring) | One JSON config → running app: registry from config, enabled channels wired to adapters, unknown channel names rejected at load; config path via `CCE_CONFIG` (default `~/.config/ichnos/cce.json`), shape shipped as `cce.example.json` | `load_config(path) -> dict`; `build_channels(channels_config) -> list[Channel]`; `build_app_from_config(config_path, binding?) -> FastMCP`; `CHANNEL_ADAPTERS: {name -> adapter class exposing async read()}` |
| `cce_server.adapters.github` (fast-path adapter) | GitHub channel: authenticated user, assigned open issues, review-requested open PRs; token ladder explicit arg → `GITHUB_TOKEN` env → gh CLI (standard-install fallback); token never logged or surfaced | `GitHubAdapter(token?)` with `async read() -> {user, assigned_issues[], review_requested_prs[]}`; raises `TokenUnavailable` before any call when unresolvable |

_Last verified: 2026-09-15_

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Client protocol | MCP | Client-agnostic by invariant; registration pattern proven with `grok-research-mcp` (formalized in `docs/consumer-registration.md`, Phase 0) |
| Retrieval precedence | API/protocol fast-path default; OS-level inspection as universal fallback | Handoff invariant; compiled per channel in `docs/channel-matrix.md` (Phase 0) — structural, not per-prompt |
| Display isolation | Structural — separate virtual display substrate; never primary-session attachment | Terminal bound (`docs/scope.md`); substrate chosen by Phase 0 (`docs/display-isolation.md`) |
| Adapter write posture | Read-only observers — no write-back to external channels | Owner sanction 2026-09-15, recorded on issue #2; a context engine with write access is an autonomous actor outside project scope |
| Auth seeding | Browser-mediated extraction (ABE era): encrypted profile copies only, plaintext memory-resident host→VM, pipe transport, never plaintext on disk, in logs, or in tool output | Terminal bound (`docs/scope.md`); re-derived after Near fired on DPAPI (`docs/auth-seeding.md`) |
| Consumer access | Registered (owner-sanctioned) consumers only, scoped per consumer | Owner sanction 2026-09-15, recorded on issue #2; unregistered clients receive nothing |

_Last verified: 2026-09-15_

---

## Constraints

- **Secrets/session material** never leave the OS credential store; never logged or surfaced in tool or API output (`docs/scope.md`, Terminal bound).
- **Fallback executor** never attaches to the primary session's input devices or viewport; isolation is enforced by the substrate, not process behavior.
- **Context** is served only to registered consumers, scoped per consumer; adapters never write to external channels.
- **Host**: Windows + WSL2 (Ubuntu) + Docker present; Hyper-V unverified (needs elevation) — Phase 0 settles the display substrate; elevation, if required, is an owner sanction.
- **Auth states are time-dependent**: seeded sessions expire and walled gardens change; adapters isolate drift (Isolation of fragility) so it burns one module, not the engine.

_Last verified: 2026-09-15_
