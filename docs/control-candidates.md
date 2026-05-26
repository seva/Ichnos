# Control Candidates — Policy & Feasibility (Phase 0)

**Status: CONFIRMED policy + spot-checked feasibility (2026-05-25).** Full per-maintainer
enumeration is a Phase 1 task; this fixes the control definition and tests whether controls exist.

_Last verified: 2026-05-25_

---

## Control policy

For a Mythos finding at maintainer/project `M` with disclosure date `D`, a **control** is an
advisory such that:

1. **Same maintainer/project** `M` (matches author + topic domain; the held-out-maintainer split
   then tests cross-maintainer generalization).
2. **Within ±90 days of `D`**, where `D = committed_at` (the seal/disclosure-to-maintainer date;
   the nginx finding's timeline confirms `committed_at` == "Sent to maintainer").
3. **Not Glasswing/Anthropic-credited** and **not** one of the 27 Mythos findings.

The text scope of the control (CVE description vs GHSA prose vs other) is decided in
`text-scope.md` and **must match the Mythos class's text scope** to avoid the source/format
confound.

## Spot-check — wolfSSL (the only viable author class)

NVD `keywordSearch=wolfssl`, `pubStartDate=2026-02-01 … pubEndDate=2026-05-31` → **29 CVEs**, all
CNA `facts@wolfssl.com`:

| Group | Count | CVEs |
|---|---|---|
| Mythos (revealed, in window) | 7 | 5446, 5448, 5466, 5479, 5500, 5501, 5503 |
| **Control candidates** | 22 | 0819, 1005, 2645, 2646, 3229, 3230, 3503, 3547, 3548, 3549, 3579, 3580, 3849, 4159, 4395 (all pub 2026-03-19); 5188, 5263, 5295, 5393, 5460, 5504, 5778 (pub 2026-04-09/10) |

None of the 22 mention Anthropic/Mythos/Glasswing in description or references. **By count,
controls are abundant** for wolfSSL (≈22 vs 9), and same-maintainer ±90-day matching is satisfiable
for this project.

## ⚠ The contamination ceiling (a fundamental, not Phase-1, limitation)

A control candidate **cannot be verified non-Mythos from public data**, for two compounding
reasons:

1. **The dashboard hides unrevealed findings' project.** 1,569 of 1,611 ledger entries expose only
   a hash until their window closes. Some could be wolfSSL Mythos findings that received a CVE but
   whose dashboard detail isn't revealed — they would appear in NVD as ordinary wolfSSL CVEs,
   indistinguishable from genuine non-Mythos ones.
2. **The CNA need not credit the finder.** wolfSSL self-assigns (`facts@wolfssl.com`); a
   Mythos-found bug's wolfSSL CVE may carry no Anthropic credit. "0 Anthropic mentions" is
   necessary, not sufficient.

The 2026-04-09/10 candidates are the most suspect: they interleave with the Mythos CVEs in one
contiguous number cluster (5446–5504) on the same publication dates — plausibly one co-disclosed
batch. The 2026-03-19 batch is safer (distinct date, lower number range) but still not provably
clean. The only provably-clean controls are **pre-Mythos-era** wolfSSL CVEs (before ~Feb 2026) —
which fall **outside** the ±90-day window. This is a direct tension between *temporal matching* and
*clean attribution*, and it bites hardest exactly on the heavily-Mythos-targeted projects that have
enough findings to be useful.

## Singletons

The 11 single-finding maintainers (jq, junrar, libyang, …) are moot for the held-out-maintainer
design (they cannot be an author class — see `power-analysis.md`), so their control density is not
on the feasibility critical path today. Several are GHSA-only and their GHSAs do not currently
resolve (`ghsa-api.md`), compounding control retrieval. Deferred to Phase 1.

## Verdict

- **Controls exist in quantity** for the data-rich maintainer (wolfSSL) → the *count* side of the
  random-split is satisfiable.
- **Provably-clean controls are not constructible from public data** for active Mythos targets,
  because unrevealed findings hide their project and CNAs need not credit the finder. Any control
  set carries residual Mythos-contamination risk that biases the comparison toward a *null* (some
  "controls" are actually Mythos), and cannot be fully eliminated.
- Mitigations to weigh in Phase 1: prefer pre-wave / lower-number-cluster CVEs; cross-reference the
  growing revealed set to remove confirmed Mythos; treat the contamination as a bounded,
  documented bias in the Phase 5 conclusion rather than something resolvable.

## For Phase 1

Enumerate per maintainer via NVD (`keywordSearch` + ≤120-day windows) and GHSA (`gh api`); record
each candidate's CNA/`credits`, publication date, and a `mythos_excluded` provenance flag with the
basis for exclusion. No candidate is admitted as a control without a logged exclusion rationale.
