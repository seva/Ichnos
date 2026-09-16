# Auth Seeding — Ladder & Flow (Phase 0)

**Status: host facts CONFIRMED by machine verification 2026-09-15. NEAR FIRED on the DPAPI term — App-Bound Encryption (ABE, Chrome ≥127) is present on this host (`app_bound_encrypted_key` in Local State), so the classic "DPAPI-decrypt the cookie key" rung does not hold. This document is the re-derivation the scope's commitment-class table required (`docs/scope.md`, credential handling, Set 5). Route selection PROPOSED for Phase 2/3 implementation.**

---

## Host facts (verified 2026-09-15)

- Chrome profile present; `Local State` carries **both** `encrypted_key` (legacy DPAPI) and `app_bound_encrypted_key` (ABE).
- Cookies DB present at `Default\Network\Cookies` (sqlite; `encrypted_value` blobs).
- Edge profile present (same ABE mechanics, same treatment).
- Consequence: cookie key material is bound to the browser's elevation service — extracting it by direct DPAPI decryption is the *old* mechanism; on this host the **browser must mediate decryption** (it holds the unbound key internally via its COM elevation service).

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

Stage 1 — **host-side browser-mediated extraction**: launch a *separate, temporary* Chrome instance on the host (never attach to the operator's running browser) with a **minimal profile copy**: `Local State` + the cookies DB only, into a temp user-data-dir. Values remain encrypted at rest in the copy (no plaintext-at-rest violation). Launch with a loopback-only remote-debugging port; read cookies via CDP (`Storage.getCookies`) — the browser decrypts internally; decrypted values exist only in process memory.

Stage 2 — **transport**: decrypted cookie values flow host → isolated display VM over the display stack's control channel (direct CDP to the VM's browser: `Network.setCookie`). **Never through files, never through logs, never in tool output.** The extraction process's memory is the only plaintext residence on the host.

Stage 3 — **probe & handoff**: the seeded session is verified inside the display with a low-risk authenticated probe (read-only page fetch). On success: display session live, seeding record = `{channel, cookie_count, as_of}` metadata only. On failure: **no plaintext fallback anywhere** — the channel degrades to the HITL portal (operator logs in manually inside the display), which is the designed path for exactly this.

Bound compliance: no plaintext at rest (copy holds only encrypted blobs; decrypted values memory-resident then in-VM); no attach to the primary session's browser (separate instance, separate profile copy); source profile is read-only (never written back); secrets never logged/surfaced (metadata-only records); values never leave host+VM memory.

---

## Checks & drift terms (Set 5 — state against check)

| Term | Registered drift signal | Check |
|---|---|---|
| ABE mechanism | Chrome/Edge major update altering `Local State`/elevation-service behavior | pre-seed probe: stage-1 extraction verified on a canary cookie before any transport |
| Profile layout | browser update moving/renaming Cookies DB or Local State fields | stage-1 path assertions fail loudly → Near, re-derive |
| Display transport | display substrate change (Phase 0 display-isolation output) | stage-2 CDP reachability check per seeding run |
| Session validity | sites rotate/invalidate sessions independently of the browser | stage-3 probe failure → HITL portal (normal, not exceptional) |

Term below the cut, registered non-drifting: DPAPI as the *underlying* protector on this host for legacy keys (the `encrypted_key` blob) — its own drift is subsumed by the stage-1 check.

---

## Failure modes

| Failure | Response |
|---|---|
| Stage-1 probe fails (ABE/layout drift) | stop; no partial seeding; Near fired → re-derive the ladder; channel serves `unavailable` per contract |
| Stage-2 transport unreachable (substrate down) | stop; channel `unavailable`; no local caching of decrypted values |
| Stage-3 probe fails (session invalid/rotated) | non-exceptional: HITL portal handoff; seeding record marked stale |
| Extraction process crash | decrypted values die with the process (memory-only); no cleanup problem exists by construction |

---

## Open items

1. **Route ratification** — the browser-mediated route (stages 1–3) is PROPOSED; it constrains the display-isolation choice (stage 2 requires a control channel into the VM — a substrate selection criterion, fed to `docs/display-isolation.md`).
2. **Dedicated extraction profile** — long-term alternative: the operator maintains a dedicated, non-primary browser profile whose sessions are display-bound (no profile copying at all). Cleaner, but requires operator behavior change — surfaced for the Owner, not decided here.
3. **Chrome version pinning policy** — whether seeding pins to known-good browser versions or always rides current; interacts with the stage-1 canary check cadence.
