# Glasswing CVD Dashboard — Interface Notes (Phase 0)

**Status: CONFIRMED (observed firsthand from local network, 2026-05-24).** This revision
supersedes the 2026-05-24 `PARTIAL / BLOCKED` version, which recorded a sandbox egress block
(GitHub-only allowlist → `403 host_not_allowed`). That block was an artifact of the Claude
Code web sandbox; work moved to a local machine with normal network access and every
previously-blocked host is now reachable. Secondary-source claims in the prior revision are
now confirmed or corrected against the live primary source below.

_Last verified: 2026-05-24_

---

## Reachability (resolved)

Re-probed 2026-05-24 from the local machine via `Invoke-WebRequest` (not WebFetch — local
requests use this machine's real network stack; the sandbox policy no longer applies):

| Source | Host | Prior (sandbox) | Now (local) |
|---|---|---|---|
| Glasswing CVD dashboard | `red.anthropic.com` | 403 `host_not_allowed` | **200** text/html |
| Anthropic site | `www.anthropic.com` | 403 | **200** |
| NVD API | `services.nvd.nist.gov/rest/json/cves/2.0` | 403 | **200** application/json |
| NVD site | `nvd.nist.gov` | 403 | **200** |
| oss-sec (openwall) | `www.openwall.com/lists/oss-security/` | 403 | **200** |
| oss-sec (seclists) | `seclists.org/oss-sec/` | 403 | **200** |
| GHSA (web) | `github.com/advisories` | 200 | 200 |

---

## Overview

- **URL:** `https://red.anthropic.com/2026/cvd/` — "Anthropic's coordinated vulnerability
  disclosure dashboard," published by the Anthropic Frontier Red Team.
- **Hosting:** static, server-rendered HTML behind Cloudflare (`Server: cloudflare`,
  `cf-cache-status: DYNAMIC`). No app server, no auth, no API key. `Access-Control-Allow-Origin: *`.
- **Snapshot model:** the page is a dated snapshot ("Snapshot generated at 2026-05-22 10:27 PT",
  `revision: 1`). The footer states archived snapshots remain available at their dated paths so
  any figure can be verified against the page that was live on that date. Reproducibility-friendly.
- **Premise confirmed (primary source):** "In February 2026, Anthropic began using an early
  snapshot of Claude Mythos Preview to find security vulnerabilities in open-source software."
  Every finding on the dashboard is a Mythos Preview discovery.

## Site map (firsthand)

| Path | Type | Purpose |
|---|---|---|
| `/2026/cvd/` (`index.html`) | HTML | Overview: funnel stats, disclosure ledger (compact), CVE/GHSA cards, severity heatmap, provenance hash |
| `/2026/cvd/ledger/index.html` | HTML | Full ledger UI (same data as `data/ledger.json`) |
| `/2026/cvd/archive/index.html` | HTML | Archived dated snapshots — *purpose noted from nav; not fetched this session* |
| `/2026/cvd/about/index.html` | HTML | Glossary of pipeline terms — *not fetched this session* |
| `/2026/cvd/findings/{ANT_ID}.html` | HTML | **Per-finding full report** (title, description, technical details, reproduction, timeline, provenance) |
| `/2026/cvd/data/ledger.json` | JSON | **Full ledger** — array of 1,611 entries (metadata only, no prose) |
| `/2026/cvd/data/payload.json` | JSON | **Authoritative structured snapshot** — stats, CVE/GHSA records, per-project/class breakdowns; its SHA-3-512 is the published manifest hash |
| per-finding `preimage.json` | JSON | The exact sealed bytes a finding's SHA-3-512 hash commits to; served as a `data:application/json` download link embedded in each finding page |

**Response format: HTML for humans, JSON for machines.** Ingestion does not need HTML scraping —
`data/ledger.json` and `data/payload.json` are the canonical machine-readable surfaces, and each
revealed finding's prose is available both as rendered HTML and as a downloadable `preimage.json`.

## Pagination & rate limits

- **No server-side pagination.** The compact overview table and the CVE/GHSA card lists paginate
  **client-side in JavaScript** (`assets/ledger.js`, `data-page-size="10"`) over the full dataset.
  The complete data arrives in a **single fetch** of `data/ledger.json` (875 KB) or
  `data/payload.json` (992 KB). The `<noscript>` block confirms: "The full data is available at
  `data/ledger.json`."
- **No documented rate limit, no API key.** These are static files behind Cloudflare. Response
  carries a `__cf_bm` (Cloudflare bot-management) cookie; aggressive automated fetching could draw
  a challenge. Polite, low-rate, cached fetching is appropriate. The snapshot updates roughly daily,
  so re-fetch cadence of ≤1/day is sufficient.

## Integrity (aligns with the corpus-integrity rule)

The dashboard is **tamper-evident**, which is favourable for `corpus/manifest.jsonl` provenance:

- **Snapshot hash:** `payload.json` carries `manifest_sha3`, a SHA-3-512 over the structured
  payload, republished with every dated snapshot (observed: `b7a0c536…f69ff8e4`).
- **Per-finding hash:** each finding page publishes a SHA-3-512 over its `preimage.json` and offers
  the preimage as a download, so the sealed report text is independently verifiable
  (observed for `ANT-2026-HY56VRSB`: `64bfee70…79344db5`).
- **Verification is deferred to Phase 1** (`ingest/audit_manifest.py`): canonical serialization /
  key-order of the preimage was not reverse-engineered this session, and no hash was recomputed.
  Recording these hashes per entry and verifying them on ingest satisfies the corpus-integrity
  contract.

---

## Open Question #1 — RESOLVED: does the dashboard serve advisory TEXT, or only IDs + hash + status?

**Both — depending on disclosure stage.**

- **In-window findings (still sealed):** the ledger shows **only** `hash` + `committed_at` +
  `status`; `project`, `bug_class`, and identifier are withheld (`—`). This matches the prior
  secondary-source description.
- **Revealed findings (disclosure window closed):** the per-finding page serves the **full
  advisory prose** — a structured report with `title`, `description`, `technical_details`, and a
  numbered `reproduction[]`, plus CVE/GHSA identifiers, a discovery→reveal timeline, and the
  SHA-3-512 provenance. Verified firsthand on `findings/ANT-2026-HY56VRSB.html` (nginx).

**Consequence for the project's data strategy:** the dashboard is **itself the authoritative
Mythos-authored text source.** NVD, GHSA, and oss-sec are therefore **not required to obtain the
Mythos text** — they remain relevant only for (a) building *control* advisories (same-maintainer,
non-Mythos) and (b) the alternative text-scope option of using maintainer-written CVE/GHSA
descriptions. This collapses much of the originally-planned ingestion surface. See `text-scope.md`.

## Authorship provenance (feeds Open Question #5: Mythos-drafted vs human-edited)

The finding page attributes text in layers, which bounds any "Mythos signature" claim:

- `Discovered by [Claude Mythos Preview]` (explicit model attribution).
- Report header: *"Anthropic's analysis, sealed at approval. Disclosure to the maintainer was
  performed by Calif."* — the prose is Anthropic/Claude's analysis; an external security research
  firm (here "Calif", one of six) performed the disclosure act, not the writing.
- Acknowledgement: *"discovered by Claude … and triaged by the Anthropic security team in
  collaboration with Anthropic Research."*

So the report body is **Mythos-drafted and human-reviewed-before-sealing**, not raw model output.
This is a *favourable* substrate (clean attribution + cryptographic seal) but Open Question #5
stands: triage/review may have edited the prose. The disclosing-firm field is a candidate
within-Mythos confound worth capturing per entry.

## ⚠ Confound flag (feeds text-scope decision)

If Mythos text is taken from `red.anthropic.com` (a uniform Anthropic report template) while
controls are maintainer-written GHSA/NVD advisories, a classifier will separate **source/format**,
not **Mythos authorship**. Held-out-*maintainer* validation does **not** catch this: the format gap
is uniform across maintainers, so it inflates *both* the random-split and held-out-maintainer AUCs
and would masquerade as an act-tier signature. This is distinct from — and sharper than — the
maintainer confound the methodology already names. The text-scope decision must hold the text
*domain* constant across the Mythos and control classes. Recorded for `text-scope.md`.

---

## Inventory snapshot (from `payload.json` / `ledger.json`, dashboard snapshot 2026-05-22)

Headline (all Mythos Preview findings): 23,019 candidates → 1,900 triaged → 1,726 confirmed valid
(90.8% TPR) → 1,596 disclosed across 281 projects → 1,451 acknowledged → 97 patched → 88 advisories
assigned (28 CVE + 60 GHSA).

Ledger composition (1,611 entries): 1,424 acknowledged_by_maintainer · 145 sent · 27 revealed ·
15 discovered (sealed, pre-disclosure).

**Corpus-relevant figure (feeds `power-analysis.md` / Open Question #2):** only **27 findings are
revealed** (full text public) as of this snapshot, across **15 projects** —
wolfSSL 9, freerdp 3, mastodon 2, nginx 2, and 11 projects with exactly 1 each (19 carry a CVE,
14 a GHSA). The remaining ~1,569 disclosed findings are hash-only until their windows close. The
revealed corpus grows over time as windows close; today it is small and maintainer-skewed. The
feasibility verdict belongs to `power-analysis.md`; this is the raw count.

## Deferred / not characterized this session

- `archive/index.html`, `about/index.html` — existence and purpose noted from nav; not fetched.
- Preimage canonical serialization and hash recomputation — deferred to Phase 1 ingest/audit.
- Whether `data/ledger.json` / `data/payload.json` expose ETag/Last-Modified for cheap delta polls
  (relevant to Phase 6 daily poll) — not checked.
