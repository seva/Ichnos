# Implementation Plan

---

## Phase 0 — Discovery

Must complete before any implementation code that depends on external interfaces, display substrates, or auth surfaces.

### Tasks

- [x] `docs/channel-matrix.md`
  * Inventory the operator's context channels (Telegram, GitHub, email, browser sessions, memory stores, filesystem) with per-channel: API fast-path availability, auth mechanism and state, rate limits, and whether OS-level inspection is required
  * Compile retrieval precedence per channel: fast-path vs isolated-display fallback — a structural choice, not per-prompt
- [ ] `docs/display-isolation.md` — **DEFERRED AS DEBT** (2026-09-15): trigger = first Phase 2 task; constraint set still moving (dedicated-profile ruling, VSS elevation sanction pending) — re-derive at trigger per Set-3 class. Probe result recorded: `sudo` exits 0 but produces no observable output (3 attempts) — elevation availability **UNVERIFIED**; treat Hyper-V check as sanction-gated until proven otherwise.
  * Settle the display-isolation substrate: WSLg vs Hyper-V VM vs Docker+VNC, against the structural-isolation constraint (never the primary session's input devices or viewport)
  * Record Hyper-V status (requires elevation — unverified); select the substrate that structurally guarantees isolation without it, or surface elevation as an owner sanction
  * Constraint added by auth-seeding: substrate must carry an authenticated control channel into the VM (stage-2 transport)
- [ ] `docs/hitl-portal.md`
  * Evaluate the HITL teleoperation surface: LUMINOR index (vendored lmnr) vs plain noVNC/browser portal for 2FA, CAPTCHA, and login checkpoints
  * Verify the chosen portal reaches the isolated display and requires no primary-session attachment
- [x] `docs/auth-seeding.md`
  * Formalize the Chrome DPAPI session-extraction ladder (rule 01-024 precedent): what is extractable, where it is stored (OS credential store only), and how seed state flows into the fallback display without ever touching disk in plaintext
- [x] `docs/consumer-registration.md`
  * Document the consumer registration pattern (`claude mcp add-json` / `openclaw mcp set`, proven with grok-research-mcp) and the per-consumer context-scoping model
  * Define the "on prompt" trigger semantics: the MCP tool contract states when context is fresh, when it is re-read, and what staleness means per channel

**Outputs:** the five `docs/` files above, committed — hard prerequisites for Phases 1–5.

---

## Phase 1 — MCP server core

**Goal:** A live MCP server serving the operator's context to OpenClaw on prompt — the L2 rung.

**Adapter decision (2026-09-15):** first fast-path adapter = **GitHub** (RAROC ≈ 1.7 vs Telegram-bot 1.27: V5 — repo/issue/PR state is the context developer agents actually consume; both channels machine-verified; GitHub's content matches the primary consumer class). Telegram-bot follows as the second adapter.

### Tasks

<!-- TDD order: test task FIRST, then implementation task. -->

- [ ] `tests/test_channels.py` — ChannelState contract semantics: fresh-within-TTL serves cache (stale=False); past-TTL triggers live read bounded by timeout; live failure keeps last value + reason (explicit staleness); cold start = live-or-unavailable (no cached-serve)
- [ ] `cce_server/channels.py` — ChannelConfig, ChannelReading, Channel (TTL/timeout logic, adapter protocol)
- [ ] `tests/test_scoping.py` — consumer scoping: full → all channels; channels:[...] → intersection only; unregistered consumer → rejection with no context data; summary level → payload without raw data fields
- [ ] `cce_server/registry.py` — ConsumerScope, Registry (from config), UnregisteredConsumer error
- [ ] `tests/test_server.py` — FastMCP server builds only for a registered consumer binding (CCE_CONSUMER env at registration — client-declared identity never trusted); get_context tool exposed; empty channel set returns valid contract payload
- [ ] `cce_server/server.py` — build_server(registry, channels, binding) → FastMCP app
- [ ] *(next step)* GitHub fast-path adapter (`tests/test_github.py` first; httpx; mocks allowed — external third-party API)
- [ ] *(next step)* consumer registration against OpenClaw gateway (proves the UNPROVEN gateway path — the L2 rung's remaining gap)

**Verification:** OpenClaw retrieves live context on prompt in a real session, scoped per consumer; secrets never surfaced in tool output.

---

## Phase 2 — Fallback tier

**Goal:** Walled-garden channels served through the isolated virtual display, with the HITL portal reachable.

### Tasks

- [ ] *(expand after Phase 0)* display executor on the selected substrate
- [ ] *(expand after Phase 0)* HITL portal (browser/VNC) wired to the isolated display

**Verification:** A walled-garden channel is driven end-to-end in the isolated display; a login checkpoint is resolved through the HITL portal; the primary session's input devices are untouched throughout (verifiable by operator during the run).

---

## Phase 3 — Auth seeding

**Goal:** Login state flows from the operator's browser sessions into the fallback display via the DPAPI ladder, credential store only.

### Tasks

- [ ] *(expand after Phase 0)* seeding ladder implementation

**Verification:** A seeded session authenticates in the isolated display; no secret ever appears in plaintext on disk, in logs, or in tool output (audit item 4 check).

---

## Phase 4 — Multi-consumer

**Goal:** A second consumer class (web surface) retrieves scoped context; the engine holds its guarantees under more than one client.

### Tasks

- [ ] *(expand after Phase 0)* second consumer registration + scoping tests

**Verification:** Both consumer classes retrieve correctly scoped context; an unregistered client receives nothing.

---

## Open Questions

1. Which display-isolation substrate holds the structural constraint without Hyper-V elevation? — resolved by Phase 0
2. Does LUMINOR index add value over a plain noVNC portal at this scale? — resolved by Phase 0
3. What does consumer identity mean for a web surface (L5) that MCP alone cannot scope? — open, Phase 1+ design
4. Which channel is first (highest RAROC fast-path)? — resolved by the channel matrix
5. How fresh is "on prompt" per channel, and who pays the read cost? — resolved by Phase 0 (trigger semantics)

---

## Dependencies

```
httpx, mcp>=1.0, fastmcp (server lineage), pywin32 (DPAPI, host-side), pytest, pytest-asyncio, ruff
(display-substrate dependencies pinned by Phase 0: WSLg | Hyper-V | Docker+VNC)
```
