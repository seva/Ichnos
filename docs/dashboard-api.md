# Glasswing CVD Dashboard — Interface Notes (Phase 0)

**Status: PARTIAL / BLOCKED.** The dashboard interface is not directly observable from this
environment (see Reachability). This document records what was confirmed firsthand, and
separately records secondary-source claims labelled as unverified. The `IMPLEMENTATION.md`
checkbox stays open until the response format, pagination, and rate limits are observed
firsthand against the live dashboard.

_Last verified: 2026-05-24_

---

## Confirmed (observed firsthand)

- **Dashboard URL:** `https://red.anthropic.com/2026/cvd/` — Project Glasswing coordinated
  vulnerability disclosure dashboard.
- **Reachability from this sandbox: BLOCKED.** Both `curl` and the WebFetch tool return
  `HTTP 403` with response header `x-deny-reason: host_not_allowed`. The environment's
  network policy does not allowlist `red.anthropic.com` (nor `www.anthropic.com`). The
  dashboard's response format, pagination, and rate limits therefore **cannot** be
  characterised from this environment. Observed 2026-05-24.

## Secondary-source claims (UNVERIFIED — leads, not interface spec)

Provenance: web-search result summaries, 2026-05-24. These are NOT the primary interface and
are NOT corpus-admissible. They are recorded only as leads to verify once access exists.

- The dashboard lists **report identifiers** (~1,611 entries as of 2026-05-22) but withholds
  project name and bug class until the maintainer ships a fix.
- Per entry, reportedly: a **SHA-3-512 hash** of the sealed report published as proof of
  possession; a **status**; and identifier / project / bug-class revealed only when the
  disclosure window closes (CVD window ~90 days, or ~45 days after a patch).
- Aggregate as of 2026-05-22 (reported): 1,596 vulnerabilities disclosed across 281 OSS
  projects; 97 patched; 88 assigned a CVE or GHSA.

## Implication for Open Question #1

If the secondary-source description holds, the dashboard serves **identifiers + hash +
status, not advisory prose**. Advisory *text* — the substrate this project's stylometry needs
— would come from GHSA, NVD, the oss-sec list, or the maintainer's own advisory, with the
dashboard acting only as the index of which disclosures are Glasswing-credited. This must be
confirmed against the live dashboard before it can be relied on.

## Blocking constraint (gates all of Phase 1)

Under this environment's current network policy, the primary data sources are mostly
unreachable. Reachability probed 2026-05-24:

| Source | Host | Result |
|---|---|---|
| Glasswing CVD dashboard | `red.anthropic.com` | 403 `host_not_allowed` |
| Anthropic Glasswing pages | `www.anthropic.com` | 403 `host_not_allowed` |
| NVD API + site | `services.nvd.nist.gov`, `nvd.nist.gov` | 403 `host_not_allowed` |
| oss-sec archive | `openwall.com`, `seclists.org` | 403 `host_not_allowed` |
| GHSA database (web) | `github.com/advisories` | 200 reachable |
| GitHub API | `api.github.com` | host allowed, unauthenticated/rate-limited |
| Web search channel | (tool) | works, but summaries are not corpus-admissible |

**Resolution required: an operator decision on the environment network policy.** See issue #1.
Network policy is fixed at environment-creation time and cannot be changed from inside the
session: https://code.claude.com/docs/en/claude-code-on-the-web
