# NVD API — Interface Notes (Phase 0)

**Status: CONFIRMED (firsthand, 2026-05-25).** Queried `services.nvd.nist.gov` directly; sample
response saved during discovery.

_Last verified: 2026-05-25_

---

## Endpoint

`GET https://services.nvd.nist.gov/rest/json/cves/2.0`

| Param | Use | Notes |
|---|---|---|
| `cveId` | single CVE | e.g. `?cveId=CVE-2026-27654` |
| `keywordSearch` | text match over descriptions | e.g. `?keywordSearch=wolfssl`; precision varies by term (clean for `wolfssl`, noisy for `jq`) |
| `pubStartDate` / `pubEndDate` | publication window | ISO-8601 with ms, e.g. `2026-02-01T00:00:00.000`. **Max 120 days** between the two — wider windows must be paged in ≤120-day slices |
| `lastModStartDate` / `lastModEndDate` | modification window | for delta polling (Phase 6) |
| `startIndex` / `resultsPerPage` | pagination | `resultsPerPage` max 2000; page with `startIndex` until `startIndex+resultsPerPage ≥ totalResults` |

No API key required for low volume. **Rate limit (NVD docs):** 5 requests / rolling 30 s
unauthenticated; 50 / 30 s with a free API key. No `X-RateLimit-*` headers are returned (verified
empty) — self-throttle; request a key before Phase 1 bulk ingestion.

## Response schema (NVD_CVE 2.0)

```
{ resultsPerPage, startIndex, totalResults, format:"NVD_CVE", version:"2.0", timestamp,
  vulnerabilities: [ { cve: {
     id, sourceIdentifier, published, lastModified, vulnStatus,
     descriptions: [ {lang, value} ],          # value = the CVE description text
     metrics: { cvssMetricV31|V40: [...] },
     weaknesses: [...], configurations: [...],
     references: [ {url, source, tags} ]
  } } ] }
```

`published`/`lastModified` deserialize as timestamps. `descriptions[lang=="en"].value` is the text
the project would use under the "formal CVE description" text-scope option.

## Key finding — CVE description authorship (decisive for text-scope)

`sourceIdentifier` is the **CNA** that assigned the CVE, and for these projects it is the
**maintainer**, not Anthropic:

| CVE | CNA (`sourceIdentifier`) |
|---|---|
| CVE-2026-5446…5503 (wolfSSL) | `facts@wolfssl.com` |
| CVE-2026-27654 (nginx) | `f5sirt@f5.com` |
| CVE-2026-5199 (temporal) | `security@temporal.io` |

So the NVD description of even a *Mythos-found* CVE is **written by the maintainer/CNA**, carrying
no Mythos authorship. Using NVD text makes the Mythos and control classes same-author → no Mythos
signature to detect (clean but likely null). See `text-scope.md`.

## Key finding — partial retrievability (corpus-integrity)

Dashboard CVEs resolve **inconsistently** in NVD as of 2026-05-25:

- Resolve: wolfSSL batch, CVE-2026-27654 (nginx), CVE-2026-5199 (temporal) — descriptions
  consistent with the dashboard.
- **Does not resolve:** CVE-2026-46348 (mastodon SSRF) → `totalResults=0`.

Per the corpus-integrity rule, every CVE must be verified retrievable at ingest; absence in NVD is
logged and the entry skipped (or text taken from the dashboard finding page instead).

## For Phase 1

- Slice `pubStartDate`/`pubEndDate` into ≤120-day windows; page on `startIndex`.
- Acquire an API key; throttle to the documented limit.
- Record `sourceIdentifier`, `published`, and the en description per CVE in the manifest; verify
  presence before relying on NVD text.
