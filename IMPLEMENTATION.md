# Implementation Plan

---

## Phase 0 — Discovery

Must complete before any implementation code that depends on external interfaces, display substrates, or auth surfaces.

### Tasks

- [x] `docs/channel-matrix.md`
  * Inventory the operator's context channels (Telegram, GitHub, email, browser sessions, memory stores, filesystem) with per-channel: API fast-path availability, auth mechanism and state, rate limits, and whether OS-level inspection is required
  * Compile retrieval precedence per channel: fast-path vs isolated-display fallback — a structural choice, not per-prompt
- [ ] `docs/display-isolation.md` — **DEFERRED AS DEBT (dormant)** (2026-09-15): original trigger (first Phase 2 task) fired but its consumer was withdrawn before derivation — WhatsApp integration deferred to its own tentative future decision (issue #3). Re-derivation re-fires when a walled-garden tenant materializes or L4 work begins; the headless-first question raised during the aborted start (does an automated browser need a display at all?) is carried into the re-derivation question set.
  * Settle the display-isolation substrate: WSLg vs Hyper-V vs Docker+VNC vs headless-on-host, against the structural-isolation constraint (never the primary session's input devices or viewport)
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

**Goal:** A live MCP server serving the operator's context to a sanctioned registered consumer on prompt — the L2 rung. First live target: **opencode** (Owner ruling 2026-09-15: the OpenClaw-gateway framing was unnecessary drift).

**Adapter decision (2026-09-15):** first fast-path adapter = **GitHub** (RAROC ≈ 1.7 vs Telegram-bot 1.27: V5 — repo/issue/PR state is the context developer agents actually consume; both channels machine-verified; GitHub's content matches the primary consumer class). Telegram-bot follows as the second adapter.

### Tasks

<!-- TDD order: test task FIRST, then implementation task. -->

- [x] `tests/test_channels.py` — ChannelState contract semantics: fresh-within-TTL serves cache (stale=False); past-TTL triggers live read bounded by timeout; live failure keeps last value + reason (explicit staleness); cold start = live-or-unavailable (no cached-serve)
- [x] `cce_server/channels.py` — ChannelConfig, ChannelReading, Channel (TTL/timeout logic, adapter protocol)
- [x] `tests/test_scoping.py` — consumer scoping: full → all channels; channels:[...] → intersection only; unregistered consumer → rejection with no context data; summary level → payload without raw data fields
- [x] `cce_server/registry.py` — ConsumerScope, Registry (from config), UnregisteredConsumer error
- [x] `tests/test_server.py` — FastMCP server builds only for a registered consumer binding (CCE_CONSUMER env at registration — client-declared identity never trusted); get_context tool exposed and called through the real tool path; empty channel set returns valid contract payload (repaired per audit G1/G2: seam deleted, tests use `app.call_tool`)
- [x] `cce_server/server.py` — build_server(registry, channels, binding) → FastMCP app
- [x] `tests/test_github.py` — adapter tests first: context shape, bearer auth, empty results, HTTP error propagation, token resolution ladder (explicit → env → gh CLI; failure/empty modes) — respx mocks (external third-party API)
- [x] `cce_server/adapters/github.py` — GitHubAdapter: assigned open issues + review-requested PRs + user, brief mapping, token never logged or surfaced
- [x] *(step)* server config wiring — registry + channels loaded from one JSON config (`cce.example.json` ships the shape; live config at `~/.config/ichnos/cce.json`); `__main__` entry point real (CCE_CONFIG + CCE_CONSUMER env)
- [x] *(step)* opencode registration + live-session proof: live config installed at `~/.config/ichnos/cce.json`; `mcp.ichnos-cce` registered in opencode.json; **operator-verified in a real opencode session (2026-09-15)**: fresh GitHub context on prompt (`stale: false`, user `seva`), cache hit on immediate re-read (identical `as_of`), unconfigured channel absent, zero secret material in any payload. L2 reached.
- [x] *(step)* second consumer (OpenClaw) + gateway-path proof: registered via `openclaw mcp set` (`CCE_CONSUMER=openclaw`), gateway hot-reload verified, **live 5-check test passed through VixeYult (2026-09-16)** — fresh context, cache hit, unconfigured channel absent, credential scan clean. Both registration paths production-verified.
- [ ] `secret-scrub` boundary module — **DEFERRED AS SECURITY DEBT** (2026-09-16, Owner ruling): purpose = make the terminal bound (secrets never surface in tool output) hold for free-form message-body content. Design carried from evaluation: pattern redaction at the channel boundary (OTP shapes, credential-shaped strings, tokenized URLs; Luhn-validated to spare dates/prices), opaque replacement (`[REDACTED:<id>]`), redaction events visible in payload metadata, message bodies cached post-scrub only — raw text never resides in the engine. Fixed-key channels skip it. **HARD PREREQUISITE for any message-body channel** — first candidate: Telegram-bot adapter.
- [ ] *(postponed)* Telegram-bot adapter — Owner ruling 2026-09-16: low value feature. The multi-channel clause’s remaining half waits on a pull (messaging context wanted on prompt, or an extra client lacking native channel access). Tests-first shape recorded when reactivated.

**Verification:** a sanctioned registered consumer (opencode) retrieves live context on prompt in a real session, scoped per consumer; secrets never surfaced in tool output.

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

## Phase 4 — Multi-consumer: Gemini web UI via Tailscale Funnel (issue #4)

**Goal:** The Gemini web UI consumes ichnos memory read/write via `@ichnos` — the engine itself registered as a Gemini custom Connected App, exposed over Tailscale Funnel. Forecast V=4, P=0.75, C=3.

### Tasks

<!-- TDD order: test task FIRST, then implementation task. -->

- [x] A1 `tests/test_memory_tools.py` — search (query → top-k briefs), store (text + tags + provenance `client: gemini`), delete (by hash), recall; service failure → explicit errors; no raw service errors escape
- [x] A2 `cce_server/adapters/memory.py` — MCP client to the memory service (streamable-http `127.0.0.1:8000`); search/store/delete/recall passthrough with brief mapping + provenance injection
- [x] B1 `tests/test_scoping.py` extension — `summary` orthogonal to channel filtering; gemini = memory read/write; existing scopes regression-pinned
- [x] B2 `cce_server/registry.py` — capability dimension added
- [x] C1 `tests/test_http.py` — streamable-HTTP serves the toolset per consumer capability; bearer token → consumer per request; unknown token → no context data (real-path integration: ASGI transport + real MCP client + LifespanManager)
- [x] C2 `config.py`/`server.py` — HTTP mode (port 8001) + token→consumer map in `cce.json`; stdio mode unchanged; memory channel = first query-driven channel (no TTL cache, retrieval against the prompt); snippet_length rendering
- [x] C3 **state-advance commit** — memory channel live ⇒ L3 reached ⇒ AGENTS.md + scope.md + record-sync rules updated in the same commit
- [x] D1 Tailscale Funnel: enable public funnel for port 8001; cleanup stale serve rule (→ 4096, no listener); verify external reachability + TLS
- [x] D2 Minimal OAuth 2.1 layer: `/.well-known` metadata + `/authorize` (operator one-time-code consent) + `/token` (static client ID/secret); unknown clients rejected
- [x] D3 Registration: ts.net URL → Custom apps for Spark → Next
- [x] E1 End-to-end manual test: `@ichnos <prompt>` → memory-informed answer; store-verify-search-delete round-trip from the real UI; gemini token cannot reach github; secret scan; funnel-off degrades visibly — **PASSED 2026-09-17 (Operator-verified from the real Gemini UI)**: memory_search returned 5 briefs, memory_store landed (bcf47ac1…, verified in-store via independent funnel client), Gemini's consent flow (Allow/Deny per call) worked. Known gap: provenance metadata not returned in search briefs (service-side) — minor.

**Verification:** the five E1 checks hold in the real Gemini UI. Until then: provisional only.

---

## Open Questions

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
