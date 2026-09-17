# ichnos — Cross-Channel Context Engine (CCE)

A context engine that lets sanctioned agents and surfaces retrieve the operator's live cross-channel context on prompt over MCP — API/protocol fast-paths where they exist, an isolated virtual display as the universal fallback for walled gardens, and a HITL teleoperation portal for authentication checkpoints (2FA, CAPTCHA, login).

## Session Start

1. Read `METHODOLOGY.md`
2. Read `ARCHITECTURE.md` — verify component descriptions match current code before acting
3. Scan `IMPLEMENTATION.md` checkboxes — first unchecked task is current state
4. Check open GitHub issues for failures and decisions
5. Search memory for relevant prior knowledge
6. Locate the project in the operating cycle (`CYCLE.md`) — which step is current?
7. Identify your role (`ROLES.md`; default Steward) and the declared role instances — no role grades its own work

## Conventions

- **Scope position** (`docs/scope.md`, updated by Orient): L3 reached (multi-channel: github + memory live; second consumer openclaw proven); first L5 web-surface consumer live (gemini via Tailscale Funnel); next rung is L4 (fallback tier). The ladder climbs to L15 (galactic civilizational); far rungs are heuristic shapes — Orient measures only against the next rung.
- **Compiled terminal-bound constraints** (`docs/scope.md`, Terminal bound — the filter Decide applies before ranking): secrets/session material never leave the OS credential store, never logged or surfaced; the fallback executor never attaches to the primary session's input devices or viewport; adapters are read-only observers (no write-back to external channels); context is served only to registered (owner-sanctioned) consumers, scoped per consumer; the operator-scale terminal position lives only in `docs/scope.md`, owner-owned. Commitment classes run at PRAROC sets: software 1, channel adapters 2, host-isolation stack 3, credential handling 5.
- **Language/runtime**: Python ≥3.11 for the MCP server (FastMCP lineage of `grok-research-mcp`); PowerShell on the Windows host for host-side operations; WSL2 Ubuntu + Docker for isolated components (Hyper-V status unverified — Phase 0 settles the display-isolation substrate).
- **Test runner**: `python -m pytest` (pytest-asyncio, auto mode); coverage via pytest-cov, diagnostic only (METHODOLOGY.md Quality Signals).
- **Formatting/linting**: `ruff check` + `ruff format --check` must pass before commit.
- **Role instances** (`ROLES.md`): Steward = the executing agent session on this repo. Critic = a fresh subagent instance, spawned at step completion, seeing only the claim and its evidence — never the Steward's reasoning. Auditor = a separate fresh subagent instance, verifying against the constitution and the success criterion. Owner = Seva Lapsha (@swearlock) — legislative acts (scope amendments, sanctions, disposition) arrive as operator prompts and are recorded on the relevant issue. No instance grades its own work.
- **Accepted deviations**: none.
- **Idempotency posture** (`ARCHITECTURE.md` Re-entrant mutations): the mcp-memory service deduplicates identical content (returns no `content_hash` on duplicate store); delete is idempotent by hash. No explicit idempotency key required — the service's native dedup serves as the guard.
