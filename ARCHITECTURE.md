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

Planned data flow (Phase 0 established the sources; `ingest/` and `detector/` are built in Phases 1–6).

```
EXTERNAL (read-only)                                 PROJECT

red.anthropic.com/2026/cvd   ── ledger.json ──┐
  (PRIMARY: Mythos text,        payload.json   │
   hash-verified)               findings/*.html│
                                +preimage.json  │
                                                ▼
services.nvd.nist.gov ──── CVE text ───►  ingest/ (Phase 1) ──► corpus/manifest.jsonl
  (maintainer/CNA text)        corroboration      │             {url,sha256,class,maintainer,…}
                               + control text     │                       │
api.github.com /advisories ─ GHSA text ───────────┘                       ▼
  (maintainer text, authed gh)                                     corpus/features.parquet
                                                                    (Phase 2, raw-text features)
                                                                          │
        detector/heldout.json (frozen, sha256-committed) ──────►  detector/ (Phase 3–4)
                                                                          │
                                                                          ▼
                                                            reports/ (append-only): paired AUCs + CIs
```

_Last verified: 2026-05-25_

---

## Components

| Component | Responsibility | Key interface |
|---|---|---|
| _(none yet)_ | Phase 0 is discovery-only — no implementation code written | Components are specified in `IMPLEMENTATION.md` (Phases 1–6) and recorded here as they are built; each contract change updates this row in the same commit |

_Last verified: 2026-05-25_

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Primary data source | `red.anthropic.com/2026/cvd` JSON (`ledger.json`, `payload.json`, per-finding pages + `preimage.json`) | Only complete, SHA-3-512-verified source of Mythos-authored text; NVD/GHSA resolve only partially as of 2026-05-25 (`docs/nvd-api.md`, `docs/ghsa-api.md`). NVD/GHSA used for corroboration and control text only |
| Corpus unit | one finding (`ANT-2026-XXXXXXXX`) | Each finding carries its own Mythos report; CVE/GHSA↔finding is many-to-many (`docs/mythos-advisories.md`) |
| Confirmatory text scope | maintainer CVE/GHSA description for **both** Mythos and control classes (Option A) | Only scope where same-maintainer + held-out-maintainer isolates a Mythos trace from a source/author confound (`docs/text-scope.md`). Mixed scope (Mythos report vs maintainer control) rejected as confounded. **Pending operator ratification** |
| External fetch | direct local HTTP; GitHub via authenticated `gh` | The prior web sandbox's GitHub-only egress policy made the corpus unbuildable; local network reaches all required hosts (`docs/dashboard-api.md`) |

_Last verified: 2026-05-25_

---

## Constraints

- **Network policy** must allowlist `red.anthropic.com`, `services.nvd.nist.gov`, and `api.github.com`. A GitHub-only egress policy (the prior web sandbox) blocks the dashboard and NVD and makes the corpus unbuildable.
- **NVD**: ≤120-day query windows; 5 req / 30 s unauthenticated (50/30 s with a free API key). **GHSA**: authenticated `gh` (5,000/hr) vs 60/hr unauthenticated.
- **No model fitting** until the corpus clears the `docs/power-analysis.md` floor (≥4–5 maintainers × ≥10 revealed findings + matched controls). Today: 27 findings across 15 maintainers (11 singletons) — underpowered; the held-out-maintainer AUC is not yet computable.
- **Identifier retrievability is partial and time-dependent**; every corpus entry's identifier is verified retrievable at ingest, and absences are logged and skipped (never fabricated).
- `detector/heldout.json` is frozen and its sha256 committed before any model fitting; verified on every validation run.
- Both AUCs (random-split + held-out-maintainer) are reported **as a pair** with 95% CIs; a single AUC is rejected.
- Features must be computable from raw text without LLM mediation (no mediated stylometry).
- `reports/` is append-only; every corpus entry carries a logged URL + sha256 in `corpus/manifest.jsonl`.

_Last verified: 2026-05-25_
