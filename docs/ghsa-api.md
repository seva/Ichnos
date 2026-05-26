# GHSA Database — Interface Notes (Phase 0)

**Status: CONFIRMED (firsthand, 2026-05-25).** Queried GitHub's global advisory API via the
authenticated `gh` CLI.

_Last verified: 2026-05-25_

---

## Endpoint

GitHub global security advisory database.

| Call | Endpoint |
|---|---|
| Single advisory | `GET /advisories/{ghsa_id}` (`gh api /advisories/GHSA-…`) |
| List / search | `GET /advisories` — filters: `ghsa_id`, `cve_id`, `ecosystem`, `severity`, `affects` (package), `published`, `updated`, `modified`, `type`, `sort`, `per_page` |
| Web (human) | `https://github.com/advisories/{ghsa_id}` |

**Auth & rate limit:** `gh api` uses the CLI token → 5,000 req/hr. Unauthenticated → 60/hr (this
was the wall the prior web session hit). Use `gh api` for all GHSA work.

## Response schema (firsthand, from `GHSA-jfh8-c2jp-5v3q` log4shell)

```
{ ghsa_id, cve_id, summary, description, severity, published_at, updated_at, withdrawn_at,
  identifiers: [ {type:"GHSA"|"CVE", value} ],
  references: [ url, … ],
  credits: [ { user:{login,…}, type } ],          # <-- finder attribution
  source_code_location,
  vulnerabilities: [ { package:{ecosystem,name}, vulnerable_version_range, patched_versions } ],
  cvss, cwes }
```

The `credits[]` field is directly relevant: when a dashboard GHSA does publish, check whether
GitHub credits Anthropic/Mythos vs the maintainer — that is an independent attribution signal.
`description` is the maintainer/advisory-surface prose (not Mythos-authored), same authorship
caveat as NVD (see `text-scope.md`).

## Key finding — most dashboard GHSAs do not resolve (corpus-integrity)

Verified 2026-05-25. The endpoint works (log4shell resolves; `credits=ppkarwasz`), so 404s are
real absences, not interface error:

| Dashboard GHSA | Project | Result |
|---|---|---|
| GHSA-jfh8-c2jp-5v3q (control) | log4j | ✓ resolves (CVE-2021-44228) |
| GHSA-w52v-v783-gw97 | TryGhost/Ghost | ✓ resolves — but maps to **CVE-2026-26980**, which the dashboard did *not* list for it |
| GHSA-9f49-8x56-jmjc | libyang | ✗ 404 (API and web) |
| GHSA-crr4-7rm4-8gpw | mastodon | ✗ 404 |
| GHSA-mpxh-8fq3-x8mh | freerdp | ✗ 404 |

The dashboard files these under "publicly available," yet most 404 on GitHub. Most likely
**publication lag** between the dashboard's claim and GitHub serving the record (not proof of
fabrication — do not over-read). The one that resolves carries metadata the dashboard omitted.

**Implications:**
- For the **8 GHSA-only findings** (CraftCMS, gitoxide, ImageMagick, junrar, libyang, minio,
  Ghost, freerdp-RXYVE4DZ), GHSA is **not** a reliable text/identifier source today — their text
  exists only on the dashboard finding page.
- Resolution is time-dependent (like the revealed corpus). Re-check at ingest; never assume a
  dashboard GHSA resolves.

## For Phase 1

- Use `gh api` (authenticated). Verify each GHSA resolves before relying on it; log absences.
- Capture `credits[]` for an independent attribution check.
- Treat the dashboard finding page as the authoritative text source; GHSA/NVD as corroboration
  only, when present.
