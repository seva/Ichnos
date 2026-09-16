# Auth Seeding — Ladder & Flow (Phase 0)

**Status: host facts CONFIRMED by machine verification 2026-09-15. NEAR FIRED on the DPAPI term — App-Bound Encryption (ABE, Chrome ≥127) is present on this host (`app_bound_encrypted_key` in Local State), so the classic "DPAPI-decrypt the cookie key" rung does not hold. This document is the re-derivation the scope's commitment-class table required (`docs/scope.md`, credential handling, Set 5). Route selection PROPOSED for Phase 2/3 implementation.**

---

## Host facts (verified 2026-09-15)

- Chrome profile present; `Local State` carries **both** `encrypted_key` (legacy DPAPI) and `app_bound_encrypted_key` (ABE).
- Cookies DB present at `Default\Network\Cookies` (sqlite; `encrypted_value` blobs). **Exclusively locked by the running browser** — live reads fail with a sharing violation (verified by probe 2026-09-15).
- Edge profile present; `app_bound_encrypted_key` re-verified in Edge's `Local State`. Mechanics-equivalence with Chrome is argued from the shared Chromium codebase, not independently probed.
- Per-cookie protection state migrates gradually (legacy `v10` DPAPI blobs vs `v20` ABE blobs coexist during transition); the individual state of each cookie blob was **not** verified (source DB locked). The route below deliberately works regardless of which protector a given cookie uses.
- Consequence: cookie decryption is **browser-mediated** on this host — the browser alone holds the unbound key internally via its elevation service. Whether a given cookie is DPAPI- or ABE-protected, the extraction route is the same.

---

## What is extracted (scope of the ladder)

| Material | Extracted? | Rationale |
|---|---|---|
| Session cookies | **yes** | this is the seeding tier's entire purpose — restore login state in the isolated display |
| Browsing history / metadata | no | that is the channel matrix's fast-path read (metadata), not seeding |
| Passwords (`Login Data`) | **never** | blast radius; operator types credentials at HITL checkpoints when needed |
| Payment methods, autofill | **never** | out of scope; no consumer needs them |

---

## The ladder (re-derived)

Stage 0 (removed): direct DPAPI decryption of `encrypted_key` — **retired**: ABE binds current cookie encryption to the browser's elevation service; the DPAPI rung of rule 01-024 remains valid only for legacy stores and as the underlying protector below ABE.

Stage 1 — **host-side browser-mediated extraction**: launch a *separate, temporary* Chrome instance on the host (never attach to the operator's running browser) against a **minimal profile copy** in a fresh temp user-data-dir. No `SingletonLock` is copied (fresh dir, by construction — the running primary's lock is irrelevant). The copy contains only `Local State` and the cookies DB, which holds **encrypted** blobs — no plaintext at rest; the temp dir is **deleted immediately after stage 2 completes or on any abort**, so the encrypted duplicate exists only for the extraction window.

*Live-copy problem (verified): the source Cookies DB is exclusively locked while Chrome runs. The copy is therefore one of:* (a) taken while the operator's browser is closed (simplest, needs operator quiescence), (b) via a VSS shadow copy (works against the live DB; **requires elevation — owner sanction**), or (c) deferred entirely in favor of the dedicated-profile route (open item 2). Implementation picks one per run and records which; no silent fallback between them. A **partial/torn copy is a failure**: the copied DB's cookie name-set (names are plaintext columns, not secret) is diffed against the expected session set before proceeding — mismatch aborts.

Launch with **`--remote-debugging-pipe`** (fd-based, no TCP socket, unconnectable by other processes — a loopback port would authenticate nothing and expose decrypted cookies to any local process). The temp instance decrypts internally; decrypted values exist only in the extraction process's memory.

Stage 2 — **transport**: decrypted cookie values flow host → isolated display VM over an **authenticated control channel** (pipe-based where the substrate allows; TCP only with mutual authentication — transport auth is a **substrate selection criterion** fed to `docs/display-isolation.md`), injected via CDP into the VM's browser (`Network.setCookie`). **Never through files, never through logs, never in tool output.** Plaintext residence: the extraction process's memory, then the VM's browser process — nothing else, no host disk.

Stage 3 — **probe & handoff**: the seeded session is verified inside the display with a low-risk authenticated probe (read-only page fetch) — this is the check that actually states session validity. On success: display session live, seeding record = `{channel, cookie_count, as_of, stale}` metadata only. On failure: **no plaintext fallback anywhere** — the channel degrades to the HITL portal (operator logs in manually inside the display), which is the designed path for exactly this.

Bound compliance: no plaintext at rest (copy holds only encrypted blobs, deleted post-extraction; decrypted values memory-resident then in-VM); no attach to the primary session's browser (separate instance, pipe transport, no TCP); source profile is read-only (never written back — no planted canary cookies); secrets never logged/surfaced (metadata-only records); values never leave host+VM memory; every local endpoint is a pipe, not a socket.

---

## Checks & drift terms (Set 5 — state against check)

| Term | Registered drift signal | Check |
|---|---|---|
| Extraction-mechanism viability | browser update altering CDP surface, `Local State` schema, or elevation-service behavior | stage-1 canary: fresh temp instance + CDP cookie read verified mechanically before any transport (the browser absorbs protector changes internally by design — this check states the term the route actually depends on: extraction working, not ABE state frozen) |
| Copy integrity | torn/partial copy while the live DB is locked | cookie name-set diff (names are plaintext, not secret) against the expected session set — mismatch aborts |
| Display transport | display substrate change (Phase 0 display-isolation output) | stage-2 authenticated-channel reachability check per seeding run |
| Session validity | sites rotate/invalidate sessions independently of the browser | stage-3 probe failure → HITL portal (normal, not exceptional) |

Term below the cut, registered non-drifting: DPAPI as the *underlying* protector for legacy blobs (the `encrypted_key` path) — its own drift is subsumed by the stage-1 canary.

---

## Failure modes

| Failure | Response |
|---|---|
| Source DB locked and no copy route sanctioned (no quiescence, no VSS elevation) | seeding unavailable this run — channel serves `unavailable` per contract; operator chooses route (a), (b), or (c) explicitly |
| Torn/partial copy (name-set mismatch) | abort; temp dir deleted; no partial seeding; retry or HITL |
| Stage-1 probe fails (mechanism/layout drift) | stop; no transport; Near fired → re-derive the ladder; channel serves `unavailable` |
| Stage-2 transport unreachable/unauthenticated (substrate down or misconfigured) | stop; temp dir deleted; channel `unavailable`; no local caching of decrypted values |
| Stage-3 probe fails (session invalid/rotated) | non-exceptional: HITL portal handoff; seeding record marked stale |
| Extraction process crash | decrypted values die with the process (memory-only); temp dir deleted on restart detection; no cleanup problem beyond the encrypted copy |

---

## Open items

1. **Route ratification** — the browser-mediated route (stages 1–3) is PROPOSED; it constrains the display-isolation choice (stage 2 requires a control channel into the VM — a substrate selection criterion, fed to `docs/display-isolation.md`).
2. **Dedicated extraction profile** — long-term alternative: the operator maintains a dedicated, non-primary browser profile whose sessions are display-bound (no profile copying at all). Cleaner, but requires operator behavior change — surfaced for the Owner, not decided here.
3. **Chrome version pinning policy** — whether seeding pins to known-good browser versions or always rides current; interacts with the stage-1 canary check cadence.
