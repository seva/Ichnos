# Scope — Maximal Imaginable

Established 2026-09-15. Strategy artifact: the ladder this project climbs. Orient (CYCLE.md, step 1) measures the status quo against this document.

**Maximal mission:** The context layer for agentic computing — every sanctioned agent or surface, local or web, any operator, retrieves live cross-channel context on prompt, through API fast-paths where they exist and isolated-display fallback where they don't, with authentication checkpoints resolved through HITL portals.

---

## Scope ladder

| Level | Scope | Current system's contribution |
|---|---|---|
| L1 | Instance bootstrapped on the epistegrity scaffold (85e657e); terminal bound compiled; OpenClaw gateway declared as first consumer | as-is (this document) |
| L2 | CCE MCP server live: first channel served over fast-path (API/protocol) to OpenClaw on prompt, in a real session | registration pattern proven by grok-research-mcp (`claude mcp add-json` / `openclaw mcp set`) |
| L3 | Multi-channel context matrix: per-channel precedence (API fast-path vs OS fallback) with per-channel auth state; second local MCP consumer | OpenClaw config; the DPAPI rung of the rule 01-024 escalation ladder (Automation First: API → web_fetch → Playwright → PyAutoGUI → DPAPI) |
| L4 | Fallback tier live: walled-garden channels driven through an isolated virtual display on the Windows host, with a HITL teleoperation portal (browser/VNC) for 2FA/CAPTCHA/auth checkpoints | WSL2 + Docker present (Hyper-V unverified — needs elevation); LUMINOR index (vendored lmnr) as fallback-executor candidate; AGA `browser_controller.user.js` as adapter-contract reference |
| L5 | Web surfaces consume the same context: browser-based interfaces retrieve operator context on prompt, scope-limited by consumer identity | AGA adapter lineage (contract only — its primary-session design is forbidden by the Host Isolation invariant) |
| L6 | The engine is operator-portable: any sanctioned MCP client on any machine retrieves this operator's context on prompt, with the isolation and HITL guarantees intact | — |
| L7 | Multi-operator: the engine generalizes beyond its first operator — sanctioned consumers retrieve *any enrolled operator's* context under the same guarantees, scoped per consumer identity | — |
| L8 | The context layer for agentic computing: agent sessions anywhere arrive context-primed as a native property of the stack; the engine's guarantees (precedence, isolation, HITL, sanction) are the standard the layer enforces | — |
| L9 (institutional) | Every agent within an institution context-primed on prompt; sanction delegation is org-governed — context domains per institution, consumer scoping enforced by the org, not by each operator | — |
| L10 (federated) | Cross-institution context exchange: independently governed deployments interoperate through trust chains; the four guarantees become the interop standard *between* instances, not just within one | — |
| L11 (utility) | Context retrieval as market infrastructure: commodity service level with SLAs, competing interoperable implementations, protocol governance open and versioned — the layer is a utility any provider can run | — |
| L12 (jurisdictional) | State recognition: operator sovereignty (self-owned context) and the guarantee standard encoded in law; enforcement is compliance-grade and survives crossing legal regimes | — |
| L13 (planetary) | Civilizational infrastructure: every institution and machine is context-primed on prompt, cross-operator and cross-jurisdiction; sovereignty preserved by the sanction guarantee, not by geography | — |
| L14 (interplanetary/interstellar) | Light-lag-tolerant context transport: mirrors at each settlement serve prompt-latency reads while provenance-verified state reconciles across partitions; sanction chains and credential lifetimes engineered for decades-to-centuries horizons; self-verifying context state (hash-committed) travels where trust cannot precede it | — |
| L15 (galactic civilizational — universal) | The layer serves any cognitive substrate — biological, machine, or other — as the standard way intelligence inquires after its own and others' traces: maximal reach (any asker), maximal flexibility (any substrate, any physics that permits communication), the four guarantees as the enforcement standard at every scale | — |

Rungs beyond L8 are far positions — heuristic shapes bounding the direction of expansion, tagged as such (profile, not total). Orient measures only against the next rung; the galactic rungs price nothing into today's steps. Where physics removes response — beyond any possible echo, no correction can arrive — the filter applies at its largest: those are End/Unreachable positions, not markets.

---

## Functional depth

- **Retrieval precedence** — API/protocol fast-path is the default; OS-level screen/window inspection is the universal fallback for walled gardens. Precedence is enforced structurally per channel, not chosen ad hoc per prompt.
- **Isolation depth** — screen interactions run in an isolated virtual display; never the primary mouse, keyboard, or viewport.
- **HITL coverage** — every auth checkpoint class the fallback can hit (2FA, CAPTCHA, login) has a defined teleoperation path.
- **Client breadth** — one protocol (MCP), any consumer; consumer identity scopes what context is served.
- **Trigger semantics** — "on prompt" is a defined surface: the MCP tool contract states when context is fresh, when it is re-read, and what staleness means per channel.
- **Guarantee portability** — the four guarantees hold at every rung; each rung's expansion changes reach and substrate, never the enforcement standard. Scale never purchases exemption.

---

## Survivability

- **Exfiltration** — the context store is a high-value personal-data target; every consuming agent is a potential leak path. Consumer registration is the sanction record; unregistered clients get nothing.
- **Credential theft** — the auth-seeding tier (DPAPI session extraction) concentrates credential material; defense is the terminal-bound constraint on secrets (below), not behavior.
- **Fallback hijack** — a screen-driving executor that attaches to the primary session destroys operator trust irrecoverably; defense is structural isolation (VM/display boundary), not process discipline.
- **Malicious surface** — a web surface requesting context may be adversarial; consumer identity and per-consumer scoping are the boundary, enforced at the MCP server.
- **Drift** — external APIs change shape, walled gardens change DOM/auth flows; adapters are isolated modules (ARCHITECTURE.md, Isolation of fragility) so drift burns one module, not the engine.
- **Scale-band threats** — institutional: governance capture (the org widens sanction beyond its mandate). Federated: trust-chain compromise — one captured instance poisons the chain; defense is verification at the consumer, not trust in transit. Utility: market consolidation and rent-seeking at the protocol layer; defense is open, versioned governance. Jurisdictional: regulatory capture redefining "operator-owned"; defense is the guarantee standard remaining machine-checkable, not merely legal. Planetary: jurisdictional conflicts at civilizational scale. Interplanetary/interstellar: partition (split-brain context reads) and light-lag making correction impossible in real time — the regimes where responses stop existing are handled structurally (no commitment whose failure requires a check that may never fire), not by cadence. Galactic: substrate-strange adversaries — intelligences whose failure modes are not modeled here; the defense is the same as at L1: sanctions enforced at the boundary, isolation enforced in the substrate, nothing trusted on behavior.

---

## Terminal bound

| Compiled constraint | Irrecoverable margin it protects |
|---|---|
| Secrets, session material, and credentials never leave the OS credential store (DPAPI/keychain); never logged, never surfaced in tool or API output, never written in plaintext to disk | Credential exposure — a leaked session cannot be un-leaked; the trust boundary of every channel collapses with it |
| The fallback display executor never attaches to the primary session's input devices or viewport; isolation is enforced by the substrate (separate VM/display), not by process behavior | Host input integrity — a hijacked operator session is unrecoverable trust loss |
| The engine observes operator context; it never writes back to external channels. Read-only is a standing property of every adapter | External-channel integrity — a context engine with write access is an autonomous actor in the operator's name, outside this project's scope |
| Context is served only to registered (owner-sanctioned) consumers, scoped per consumer | Personal-data boundary — context served to an unregistered client cannot be recalled |
| The operator-scale terminal position lives only here, compiled and Owner-owned; the cycle never models it internally | Operator margin — a project-scale cycle that models its own end unbounds the terminal position and removes the filter |

| Commitment class | Refinement level (PRAROC-n, HORIZONS.md) | Terms below the cut, registered non-drifting |
|---|---|---|
| Software (code, tests, docs, MCP server) | Set 1 — scalar RAROC | — |
| Channel adapters (external API surfaces) | Set 2 — Now–Later (measure against forecast) | API shapes and rate limits assumed stable within an adapter's live life; drift is the adapter's own failure signal |
| Host isolation stack (virtual display, executor, portal) | Set 3 — Now–Far–Unreachable (respond against accept) | Windows host OS version, WSL2/Docker substrate assumed non-drifting at session scale |
| Credential and session handling (DPAPI seeding) | Set 5 — Now–Near–Far–End–Unreachable (state against check) | DPAPI mechanism assumed stable on this host; any credential-store change crosses Near and forces re-derivation |
| Project terminus | Owner-compiled (this document) | — |

---

## Terminal form

Manual context assembly for agent sessions becomes unnecessary — first for the operator, then for any operator, then for every asking intelligence at every scale the layer reaches: every sanctioned session arrives pre-primed with live cross-channel context, walled gardens covered by the isolated fallback, auth checkpoints resolved through HITL portals. The universal end is not a conquered territory but a vanished task: no cognitive agent anywhere assembles context by hand. When context transport is native to the substrates that ask, the retrieval layer is redundant and this project's form survives only as the substrate it left behind (longevity) or is released into its successors (seeding). That disposition — which branch, when — is an Owner act (CYCLE.md, Autonomy).

---

## Constraint analysis

- **Adoption band:** consumers are MCP clients. First: OpenClaw gateway (registration pattern proven with grok-research-mcp). Web surfaces arrive via the MCP protocol or the adapter contract referenced from AGA — never its primary-session design.
- **Platform band:** Windows host with WSL2 + Docker present; Hyper-V unverified (requires elevation). The display-isolation spike settles WSLg vs Hyper-V VM vs Docker+VNC against the structural-isolation constraint.
- **Channel band:** API fast-paths exist for Telegram (bot API), GitHub (authed `gh`), and keyed HTTP APIs; walled gardens fall to the display fallback. Precedence is compiled per channel in the channel matrix (Phase 0 output).
- **Composes with current system:** the MCP server extends the grok-research-mcp FastMCP skeleton; OpenClaw consumes it as it consumes grok-research-mcp today.
- **Requires rewrites:** any design that must drive the operator's primary session (AGA's architecture) — excluded by the terminal bound, not by preference.
- **Nearest concrete anchors:** OpenClaw gateway (first consumer, `~/.openclaw/openclaw.json`), grok-research-mcp (MCP registration + FastMCP skeleton), LUMINOR index (fallback executor candidate), `~\OMN\SandBox\AGA\browser_controller.user.js` (adapter contract reference), Chrome DPAPI session extraction (auth-seeding precedent, rule 01-024 ladder).
