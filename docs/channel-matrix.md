# Channel Matrix — Inventory & Precedence (Phase 0)

**Status: channel facts CONFIRMED by machine verification 2026-09-15 (paths probed, auth states checked — booleans, not proxy claims). TTL/timeout values PROPOSED — they parameterize the `get_context` contract (`docs/consumer-registration.md`) and are ratified at adapter implementation.**

---

## Inventory & precedence

Precedence is **structural per channel** (ARCHITECTURE.md Design Decisions): fast-path where an API/protocol exists; the isolated-display fallback only for walled gardens. A channel never negotiates precedence per prompt.

| Channel | Content | Fast-path | Auth mechanism | Verified 2026-09-15 | Precedence |
|---|---|---|---|---|---|
| GitHub | repos, issues, PRs, advisories, code | `gh` CLI (REST/GraphQL) | keyring token, account `seva` | authed ✓ (5000 req/hr authed; 60 unauth) | **fast-path** |
| Telegram (bot-mediated) | messages to/from the bot (VixeYult channel) | Bot API; token present in `openclaw.json` (`channels.telegram.botToken`) | bot token | present ✓ | **fast-path** |
| Telegram (personal) | the operator's own chats and history | none — Bot API sees only bot-addressed traffic; no user API on this host | n/a | walled ✓ (structural) | **fallback** (isolated display, HITL for login/2FA) |
| OpenClaw session store | agent session transcripts, memory DBs | local sqlite reads (`~/.openclaw/memory/` — `amara.sqlite` active; per-agent `*.sqlite.migrated` legacy) | none (local files) | present ✓ (amara last write 2026-03-27 — freshness at implementation TBD) | **fast-path** (local read) |
| MCP memory store | curated long-term operator memory | local HTTP MCP (`http://127.0.0.1:8000/mcp`) | localhost binding | live ✓ (serves this session) | **fast-path** |
| Filesystem | documents, projects, vaults | direct local reads | none (local) | n/a | **fast-path** |
| Browser profiles (Chrome, Edge) | history, cookies, logged-in sessions | profile DBs exist on disk; cookie decryption requires the DPAPI rung; *driving* logged-in sites requires a live session | DPAPI (credential-store only, terminal bound) | profiles present ✓ (Chrome, Edge) | **split**: local DB reads = fast-path; live site sessions = **fallback** |
| Email | operator mail | none verified on this host | UNKNOWN | not verified | **deferred** — operator to name the account/API before this row compiles |
| Work surfaces (D2L/DTOL) | work context | UNKNOWN — organizational access | UNKNOWN | not verified | **deferred** — operator ruling required (scope: is work context in-reach at L2–L4?) |

---

## TTL / timeout parameters (PROPOSED — own the contract's values)

Per `docs/consumer-registration.md`: freshness = per-channel TTL; reads bounded by per-channel timeout; cold cache = live-or-timeout.

| Channel | TTL (serve cache within) | Timeout (live read cap) | Rationale |
|---|---|---|---|
| GitHub | 300 s | 10 s | push/event-driven activity; REST latency modest |
| Telegram bot | 60 s | 5 s | conversational — freshness matters, API is fast |
| OpenClaw sessions | 60 s | 5 s | local sqlite; cheap reads |
| MCP memory | 900 s | 2 s | curated, slow-moving, local |
| Filesystem | 300 s | 10 s | cheap local reads; mtime-based invalidation possible later |
| Browser DB (local reads) | 900 s | 10 s | history/cookie metadata changes slowly; decryption cost |
| Fallback channels (display-driven) | n/a at L2 | n/a | served only when the fallback tier exists (Phase 2); each walled garden gets its own row then |

Values are starting points owned by this file; changed by commit with rationale, never silently.

---

## Open items

1. **Email** — operator to name the account and acceptable access path (IMAP? webmail via fallback?). No row compiles without it.
2. **Work surfaces** — operator ruling on whether DTOL/D2L context is in-scope for L2–L4, and under what scope level. Default: out of scope until ruled.
3. **OpenClaw session-store freshness** — `amara.sqlite` last write 2026-03-27 predates the July 2026 gateway upgrade; locate the current session store at implementation before trusting reads.
4. **Gateway trigger surface** — how OpenClaw decides to call `get_context` is a Phase 1 integration task (not a channel property).
5. **First adapter choice** — GitHub and Telegram-bot are the two verified fast-path channels; selection is the Phase 1 Decide, scored then (this file supplies the facts, not the pick).
