# Mythos-Credited Disclosures — Inventory (Phase 0)

**Status: CONFIRMED (firsthand, 2026-05-24).** Primary source is the Glasswing CVD dashboard
(`data/ledger.json` + `data/payload.json`, snapshot 2026-05-22 10:27 PT, `revision: 1`,
`manifest_sha3 = b7a0c536…f69ff8e4`). See `dashboard-api.md` for the interface.

_Last verified: 2026-05-24_

---

## Source correction (the planned oss-sec path is not an enumeration)

`IMPLEMENTATION.md` framed this task as "enumerate Mythos-credited disclosures from the oss-sec
mailing list (Alan Coopersmith threads, May 2026 onward)." Verified against the live archive:

- The oss-sec May 2026 index contains **exactly one** relevant thread —
  `openwall.com/lists/oss-security/2026/05/23/5`, Alan Coopersmith, 2026-05-23, subject
  *"Anthropic's coordinated vulnerability disclosure dashboard."*
- That post is a **pointer**, not an enumeration: it links to the Anthropic blog
  (`anthropic.com/research/glasswing-initial-update`) and to the dashboard, quotes the headline
  paragraph, and says only "The CVE list currently includes CVE's from nginx, jq, wolfSSL, and
  more. The GHSA list includes libyang, mastodon, freerdp, and more." No advisory text, no list.
- Coopersmith's own disclaimer: Oracle "is identified in the blog post as a partner" but he is
  "not personally involved." So **Oracle is one of the ~six external triage firms** (the nginx
  finding separately names "Calif" as a disclosing firm — see disclosing-firm confound below).

**Conclusion:** the dashboard supersedes oss-sec as the enumeration source. oss-sec is retained
only as (a) corroboration that the program is publicly acknowledged and (b) a potential source of
*control* advisories. The inventory below is built from the dashboard primary source.

## Corpus unit

The unit of analysis is the **finding (`ANT-2026-XXXXXXXX`)**, not the CVE/GHSA. Each finding has
its own Mythos-authored report (`title`, `description`, `technical_details`, `reproduction[]`) at
`https://red.anthropic.com/2026/cvd/findings/{ANT_ID}.html` (+ downloadable `preimage.json`).
CVE/GHSA↔finding is **many-to-many**: nginx's two findings share one CVE; freerdp's three findings
share a three-GHSA cluster. Counting by finding gives **27 Mythos documents**; counting by
published identifier gives ~26. Use the finding count.

## Inventory — 27 revealed Mythos findings (full text public as of 2026-05-22 snapshot)

All revealed in a single batch on 2026-05-20 (one on 05-21). `committed_at` (seal date) ranges
2026-03-20 → 2026-05-08. Finding URL = `…/cvd/findings/{ANT_ID}.html`.

| Maintainer / project | ANT-ID | Bug class | Claude sev | CVE | GHSA | Committed | Revealed |
|---|---|---|---|---|---|---|---|
| CraftCMS | ANT-2026-ZQ8AY22X | privilege-escalation | high | — | GHSA-cc7p-2j3x-x7xf | 2026-05-08 | 2026-05-20 |
| freerdp | ANT-2026-H97FY6C8 | heap-buffer-overflow | critical | CVE-2026-44420 | GHSA-mpxh-8fq3-x8mh / mvpx-xj7r-3p3r / p6r2-4hgm-m6ff | 2026-04-30 | 2026-05-20 |
| freerdp | ANT-2026-HN9XZXJ9 | heap-buffer-overflow | critical | CVE-2026-45700 | (same GHSA cluster) | 2026-04-30 | 2026-05-20 |
| freerdp | ANT-2026-RXYVE4DZ | heap-buffer-overflow | critical | — | (same GHSA cluster) | 2026-04-30 | 2026-05-20 |
| GitoxideLabs/gitoxide | ANT-2026-6SNS6KMP | rce | high | — | GHSA-f26g-jm89-4g65 | 2026-05-08 | 2026-05-20 |
| ImageMagick | ANT-2026-T44WA684 | heap-buffer-overflow | high | — | GHSA-x9h5-r9v2-vcww | 2026-04-05 | 2026-05-20 |
| jq | ANT-2026-EBDTPNVH | heap-buffer-overflow | medium | CVE-2026-32316 | GHSA-fhc2-96rr-cg32 | 2026-05-07 | 2026-05-20 |
| junrar | ANT-2026-9VJ9JJXQ | path-traversal | high | — | GHSA-j273-m5qq-6825 | 2026-05-08 | 2026-05-20 |
| libyang | ANT-2026-TZQ1KH7E | use-after-free | medium | — | GHSA-9f49-8x56-jmjc | 2026-05-07 | 2026-05-20 |
| MapServer | ANT-2026-9SZMPW41 | heap-buffer-overflow | medium | CVE-2026-33721 | GHSA-cv4m-mr84-fgjp | 2026-05-07 | 2026-05-20 |
| mastodon | ANT-2026-6DSMTXZ8 | ssrf | high | CVE-2026-46348 | GHSA-crr4-7rm4-8gpw | 2026-04-23 | 2026-05-20 |
| mastodon | ANT-2026-P2DWB2SK | signature-bypass | high | CVE-2026-46349 | GHSA-chgx-jx3p-rf73 | 2026-04-23 | 2026-05-20 |
| minio | ANT-2026-BRQZSDGZ | path-traversal | critical | — | GHSA-xh8f-g2qw-gcm7 | 2026-05-07 | 2026-05-20 |
| nginx | ANT-2026-HY56VRSB | heap-buffer-overflow | high | CVE-2026-27654 | — | 2026-03-20 | 2026-05-20 |
| nginx | ANT-2026-VS18SA90 | arbitrary-file-write | critical | CVE-2026-27654 | — | 2026-04-05 | 2026-05-20 |
| nomad | ANT-2026-CN7KX43N | path-traversal | critical | CVE-2026-7474 | — | 2026-05-07 | 2026-05-20 |
| temporalio/temporal | ANT-2026-DJBBBBPE | broken-access-control | critical | CVE-2026-5199 | — | 2026-05-08 | 2026-05-20 |
| TryGhost/Ghost | ANT-2026-H5T8XKWR | sql-injection | critical | — | GHSA-w52v-v783-gw97 | 2026-05-08 | 2026-05-20 |
| wolfSSL | ANT-2026-0JRYQPCF | heap-buffer-overflow | high | CVE-2026-5503 | — | 2026-04-05 | 2026-05-20 |
| wolfSSL | ANT-2026-6615Y595 | heap-buffer-overflow | medium | CVE-2026-5448 | — | 2026-04-05 | 2026-05-20 |
| wolfSSL | ANT-2026-K8YY7WWS | improper-cert-validation | high | CVE-2026-5501 | — | 2026-04-05 | 2026-05-20 |
| wolfSSL | ANT-2026-KNXJMVYC | signature-bypass | high | CVE-2026-5466 | — | 2026-04-05 | 2026-05-20 |
| wolfSSL | ANT-2026-P23DVQM2 | crypto-failure | high | CVE-2026-5500 | — | 2026-04-05 | 2026-05-20 |
| wolfSSL | ANT-2026-RSSMAMA7 | crypto-failure | high | CVE-2026-5479 | — | 2026-04-05 | 2026-05-20 |
| wolfSSL | ANT-2026-SB4PHA43 | crypto-failure | high | CVE-2026-5446 | — | 2026-05-07 | 2026-05-20 |
| wolfSSL | ANT-2026-VV0PRKKV | heap-buffer-overflow | high | CVE-2026-5447 | — | 2026-03-27 | 2026-05-21 |
| wolfSSL | ANT-2026-ZZY4987K | integer-overflow | high | CVE-2026-5477 | — | 2026-04-05 | 2026-05-20 |

Identifier coverage: 6 findings have both CVE+GHSA, 13 CVE-only, 8 GHSA-only, 0 with neither.

## Distribution by maintainer (the binding constraint)

| Maintainer | Findings | Note |
|---|---|---|
| wolfSSL | 9 | Only maintainer with a usable within-author sample |
| freerdp | 3 | Three findings, shared GHSA cluster |
| mastodon | 2 | |
| nginx | 2 | Both share CVE-2026-27654 |
| CraftCMS, GitoxideLabs/gitoxide, ImageMagick, jq, junrar, libyang, MapServer, minio, nomad, temporalio/temporal, TryGhost/Ghost | 1 each | 11 singletons |

15 maintainers; **11 have n=1**. This is the input to `power-analysis.md` and the reason the
held-out-maintainer design is not yet satisfiable (only wolfSSL, and marginally freerdp, carry
enough texts to be an author class).

## Disclosing-firm field (candidate within-Mythos confound)

The text is "Anthropic's analysis" but the *disclosing firm* varies per finding (nginx →
"Calif"; Oracle is a partner per Coopersmith). If different firms edit prose before sealing, firm
identity is a confound *inside* the Mythos class. The firm is stated on each finding page; capture
it per entry during Phase 1 ingestion.

## Provenance & integrity

Every row is sourced from the dashboard's `data/ledger.json` (entries where `revealed == true`),
corroborated by `data/payload.json` (`cve_records`, `ghsa_records`, `by_project`) and the
Coopersmith oss-sec post (2026-05-23). Per-finding text + SHA-3-512 are on the finding pages.
No row was invented; identifiers and dates are copied verbatim from the JSON. The snapshot
`manifest_sha3` (`b7a0c536…`) freezes this inventory to the 2026-05-22 dashboard revision.

## Growth over time

Only 27 of 1,596 disclosed findings are revealed today (windows close ~90 days after disclosure,
or ~45 days after a patch). ~88 advisories are assigned but only ~26 published; the revealed set
will grow as windows close. Feasibility is therefore **time-dependent** — see `power-analysis.md`.
