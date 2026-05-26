# Stylometric Power Analysis (Phase 0)

**Status: CONFIRMED.** Computed 2026-05-24 against the verified corpus inventory
(`mythos-advisories.md`: 27 revealed Mythos findings, 15 maintainers, 11 singletons).
**Verdict: the project is underpowered today for its stated two-AUC design. Feasible only as an
exploratory single-split; the held-out-maintainer validity check is not satisfiable until the
revealed corpus grows.**

_Last verified: 2026-05-24_

---

## 1. Prescribed floor — Cohen's d on Burrows' Delta

Two independent groups (Mythos vs control), Delta score treated as a continuous measure, mean
shift = d in pooled-SD units. Two-sided α=0.05, power=0.80. Standard formula
`n/group = 2·(z_{1−α/2} + z_{1−β})² / d²` with z = 1.95996, 0.84162:

| Effect | Cohen's d | n per class | Total (incl. control) |
|---|---|---|---|
| Large | 0.8 | **25** | 50 |
| Medium | 0.5 | **63** | 126 |
| Small | 0.3 | **175** | 350 |

These are the canonical numbers. **Caveat:** Burrows' Delta is multivariate (~100+ function-word
z-scores aggregated). A single-measure t-test floor is an order-of-magnitude guide, not an exact
requirement — many weak features can raise achievable separation, or a single dominant feature can
lower it. Treat as a planning floor.

## 2. Translation to what the project actually reports (paired AUCs)

The deliverable is two AUCs with 95% CIs, not a t-test. Under equal-variance normal scores,
`AUC = Φ(d/√2)`, so the prescribed effects map to **modest** AUCs:

| Cohen's d | Implied AUC |
|---|---|
| 0.3 | 0.584 |
| 0.5 | 0.638 |
| 0.8 | 0.714 |

Inverting the project's decision thresholds (`detector`/Phase 5) gives the effect sizes they
*demand*:

| Decision threshold | Implied Cohen's d |
|---|---|
| maintainer-confound bar, AUC = 0.70 | d ≈ 0.74 |
| **act-tier bar, AUC = 0.80** | **d ≈ 1.19** |

So the act-tier classification requires a **very large** effect (d≈1.19) — larger than the "large"
d=0.8 case in §1. That is good news for *sample size if the signal is real* (strong signals need
fewer samples) but bad news for *false positives*: a format/source confound (`text-scope.md`) can
manufacture exactly this kind of large, uniform separation.

## 3. Why n governs the CI, not just the point estimate

The project rejects a single AUC; it needs a CI. Hanley–McNeil SE(AUC) with n_pos = n_neg = n:

| Target AUC | n/class | 95% CI half-width | 95% CI |
|---|---|---|---|
| 0.80 | 13 | ±0.174 | [0.63, 0.97] |
| 0.80 | **27** (today) | ±0.119 | **[0.68, 0.92]** |
| 0.80 | 50 | ±0.087 | [0.71, 0.89] |
| 0.80 | 100 | ±0.061 | [0.74, 0.86] |
| 0.71 | 27 | ±0.138 | [0.57, 0.85] |

Reading: even if a real act-tier signal (AUC≈0.80) exists, at today's n=27 the CI is **[0.68,
0.92]** — it excludes chance (0.5) but its **lower bound (0.68) dips below the 0.70 maintainer
bar**, so the result could not be cleanly classified act-tier. Clearing 0.70 at the CI lower bound
needs **≥50/class**. For a tight ±0.05-ish CI, ~100/class.

## 4. The binding constraint — held-out-maintainer is not satisfiable at n=27

This is the real gate, and it fails independently of effect size.

The design validates on a **held-out maintainer**: train on some maintainers, test on a maintainer
unseen in training, to separate a Mythos signature from a maintainer confound. Leave-one-
maintainer-out over the current 15 maintainers produces:

- **11 folds with n_pos = 1** (the singletons) — a one-point "AUC" is degenerate; no CI.
- **1 usable fold:** wolfSSL (9 findings). **1 marginal:** freerdp (3).
- A "mean held-out-maintainer AUC" over these folds is dominated by degenerate folds and is not
  interpretable.

There is effectively **one** maintainer-author class with enough text (wolfSSL). You cannot train-
on-others-and-hold-out-wolfSSL meaningfully (the "others" are mostly n=1), nor hold out a singleton
(n_pos=1). **The held-out-maintainer AUC cannot be produced today.** Since the methodology rejects a
lone random-split AUC, the full deliverable is currently unachievable.

## 5. Recommended minimum corpus

To make **both** AUCs meaningful (random-split CI lower-bound clears the relevant threshold **and**
held-out-maintainer has non-degenerate folds):

- **≥4–5 maintainers**, each with **≥10 revealed Mythos findings** and **≥10 matched controls**
  (so every held-out fold has n_pos ≥ ~10 and a usable per-fold AUC), giving **~50+ per class**.
- Equivalently: enough that leave-one-maintainer-out yields ≥4 folds with n_pos ≥ 10.

Today: 27 findings, **one** maintainer near the per-author floor. ~1 order of magnitude short on
maintainer breadth.

## 6. Go / no-go trigger (quantitative)

Re-poll the dashboard (windows close ~90 d post-disclosure, ~45 d post-patch; revealed set grows):

- **GO (full design):** ≥4 maintainers with ≥10 revealed findings each, each with ≥10 same-
  maintainer ±90-day controls available.
- **PARTIAL (exploratory, labelled non-confirmatory):** proceed on wolfSSL alone as a single-author
  feasibility probe — but this *cannot* distinguish a Mythos signature from the wolfSSL-maintainer
  confound, which is the project's whole question. Exploratory only; not a Phase 5 decision.
- **NO-GO (today, for the stated design):** held-out-maintainer unsatisfiable.

## 7. Dependencies and caveats

- **Control availability** (`control-candidates.md`) is a precondition even for the random-split:
  singletons like jq/junrar/libyang may have no same-maintainer ±90-day non-Mythos advisory. The
  control side may be the harder constraint than the Mythos side.
- **Confound dependency** (`text-scope.md`): power is necessary, not sufficient. If Mythos text is
  drawn from `red.anthropic.com` and controls from maintainer GHSA/NVD prose, a large AUC measures
  source/format, not Mythos — and §2 shows the act-tier bar *expects* a large effect, so the
  project is primed to mislabel a confound as a signature unless the text domain is held constant.
- **Assumptions:** equal-variance normal scores for the d↔AUC map; independence of findings (the
  freerdp shared-GHSA cluster and nginx shared-CVE pair mildly violate this — effective n < nominal
  n). All push the true requirement **upward**, never down.
