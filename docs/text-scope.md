# Text-Scope Decision (Phase 0)

**Status: RECOMMENDATION RECORDED — operator ratification required at the Phase 0→1 gate.** The
choice determines whether the project's central comparison is well-posed, so it is flagged for
explicit sign-off rather than assumed.

_Last verified: 2026-05-25_

---

## The three candidate text sources (from discovery)

| # | Source | Author | Availability | Form |
|---|---|---|---|---|
| 1 | `red.anthropic.com` finding report (`description`, `technical_details`, `reproduction`) | **Mythos** (sealed, human-reviewed) | All 27 revealed; hash-verified | Uniform Anthropic template |
| 2 | NVD CVE description | **Maintainer/CNA** (wolfssl, F5, temporal…) | Partial (e.g. mastodon CVE absent) | Free prose |
| 3 | GHSA advisory description | **Maintainer** | Mostly unretrievable now (`ghsa-api.md`) | Free prose |

A fourth option named in `IMPLEMENTATION.md` — maintainer **commit messages** — is rejected as a
primary scope: author is the committer (not Mythos), it is not advisory text, and it is noisy. At
most a tertiary feature source later.

## The core problem (why scope is not a detail)

The Mythos-authored text exists **only** in source 1. There is **no same-author control** for it —
Mythos does not author non-Mythos advisories. So:

- **Use maintainer text (2/3) for both classes:** the Mythos and control classes are then
  *same-author, same-surface*. This is the only configuration in which the project's "same-maintainer
  control + held-out-maintainer" design is valid. It tests a real question: *does Mythos involvement
  leave a detectable trace in the maintainer's own advisory?* (e.g. the maintainer paraphrasing
  Mythos's report). Likely a small effect, possibly null — but a null here is a clean, publishable
  finding, not a failure.
- **Use Mythos text (1) vs maintainer control (2/3):** the classes now differ in **author and
  surface** (Anthropic template vs maintainer prose). A classifier separates *which document
  surface*, not *the Mythos model's style*. **Held-out-maintainer validation does not catch this** —
  the surface gap is uniform across maintainers, so it inflates *both* AUCs and masquerades as an
  act-tier signature (`power-analysis.md` §2 shows the act-tier bar already *expects* a large
  effect, so the project is primed to mislabel this confound as the result).

In short: the matching that controls maintainer identity (same-maintainer) simultaneously *breaks*
author identity unless the text is maintainer-authored on both sides. The "use red.anthropic.com
text" option is a confound trap dressed as the obvious choice.

## Options

| Option | Text scope | What it actually measures | Validity | Feasible today? |
|---|---|---|---|---|
| **A** | Maintainer CVE/GHSA description, **both** classes | Whether Mythos involvement perturbs the *maintainer's* advisory text | **Confound-clean**; held-out-maintainer valid | Retrieval-constrained (2/3 partial); underpowered |
| **B** | Mythos text (1) vs maintainer control (2/3) — the literal spec read naively | Document surface / template | **Confounded**; invalid as a "Mythos signature" test | Yes, but produces an artifact |
| **C** | Mythos text (1) vs human advisories, *explicitly reframed* as AI-report detection | "Mythos report template/style" vs human prose | Coherent *different* question; needs formatting normalization + held-out-**project** + length/topic controls | Only once corpus grows |

## Recommendation

1. **Primary (confirmatory) scope = Option A:** formal maintainer-authored CVE/GHSA description
   only, applied identically to Mythos and control entries. This is the project's *first* listed
   text-scope option and the only one under which the stated two-AUC / held-out-maintainer design
   isolates a Mythos trace from a maintainer confound. Accept that the expected effect is small and
   the honest outcome may be "no detectable trace."
2. **Reject Option B** (Mythos report text vs maintainer control) for any confirmatory AUC — it is
   a source/format confound, disqualified by the same black-box / no-circular-feature spirit as
   mediated features.
3. **Option C is permitted only as a clearly-labelled exploratory, non-confirmatory probe** on the
   dashboard text, with formatting stripped and held-out-project + topic/length controls, and never
   reported as "a Mythos signature in Glasswing advisories." Different question; label it as such.
4. The `red.anthropic.com` text remains essential as the **provenance/integrity anchor** (SHA-3-512,
   attribution, the authoritative finding list) regardless of scope — it just isn't the
   confirmatory *feature* substrate.

## Preconditions before any fitting (gates)

- **Power:** corpus must clear the `power-analysis.md` floor (≥4–5 maintainers × ≥10 findings +
  matched controls). Not met today; Option A is not runnable yet regardless.
- **Retrievability:** Option A needs maintainer CVE/GHSA text to actually resolve — partially
  blocked now (`nvd-api.md`, `ghsa-api.md`). Re-check as the corpus grows.
- **Contamination:** controls carry unverifiable Mythos-contamination (`control-candidates.md`),
  biasing Option A toward a null; document as a bounded bias in any Phase 5 conclusion.

## Decision status

**RECOMMENDED:** A (primary) · C (exploratory, non-confirmatory). **REJECTED:** B (literal mixed
scope) · commit-messages-as-primary. **PENDING:** operator ratification at the Phase 0→1 gate; A
vs C is a choice about the project's scientific question and is the operator's to make. **BLOCKED
ON:** corpus growth (power) before any model is fit.
