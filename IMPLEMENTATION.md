# Implementation Plan

---

## Phase 0 — Discovery

Must complete before any ingestion, feature extraction, or model code.

- [x] Document the Anthropic Glasswing CVD dashboard interface (URL, response format, pagination, rate limits, whether advisory text is returned or only IDs) in `docs/dashboard-api.md`
- [x] Enumerate Mythos-credited disclosures from the oss-sec mailing list (Alan Coopersmith threads, May 2026 onward) and record advisory list with URL, maintainer, CVE/GHSA ID, disclosure date in `docs/mythos-advisories.md`
- [x] For each Mythos advisory, identify candidate controls (same maintainer, ±90 days, no Glasswing or Anthropic credit) and record in `docs/control-candidates.md`
- [x] Document NVD API authentication, rate limits, and CVE description retrieval in `docs/nvd-api.md`
- [x] Document the GHSA database query interface and advisory text extraction pattern in `docs/ghsa-api.md`
- [x] Run a stylometric power analysis: minimum corpus size to detect a small (Cohen's d=0.3), medium (0.5), and large (0.8) effect on Burrows' Delta with α=0.05, power=0.8; record in `docs/power-analysis.md`
- [ ] Decide and document text-scope policy: formal CVE/GHSA description only, or include maintainer commit messages, or include Anthropic-authored advisory text from `red.anthropic.com`. Record decision and rationale in `docs/text-scope.md`

**Outputs:** `docs/dashboard-api.md`, `docs/mythos-advisories.md`, `docs/control-candidates.md`, `docs/nvd-api.md`, `docs/ghsa-api.md`, `docs/power-analysis.md`, `docs/text-scope.md` committed to `docs/`.

---

## Phase 1 — Ingestion

**Goal:** A reproducible corpus of Mythos-credited advisories and same-maintainer controls, with full provenance, sufficient to support Phase 2 feature extraction.

### Tasks

- [ ] `tests/ingest/test_dashboard_scraper.py`
  * Returns expected entry count against fixture dashboard response
  * Logs sha256 of fetched content
  * Handles HTTP 429 with exponential backoff
- [ ] `ingest/dashboard_scraper.py`
- [ ] `tests/ingest/test_ghsa_pull.py`
- [ ] `ingest/ghsa_pull.py`
- [ ] `tests/ingest/test_nvd_pull.py`
- [ ] `ingest/nvd_pull.py`
- [ ] `tests/ingest/test_osssec_parse.py`
- [ ] `ingest/osssec_parse.py`
- [ ] `tests/ingest/test_audit_manifest.py`
- [ ] `ingest/audit_manifest.py`
- [ ] Populate `corpus/manifest.jsonl` with the minimum corpus determined in Phase 0 power analysis

**Verification:** `python -m ingest.audit_manifest` reports zero missing fields, zero sha256 mismatches; corpus reproducible from manifest URLs alone.

---

## Phase 2 — Feature extraction

**Goal:** A stable feature vector for every corpus entry, computable from raw text alone.

### Tasks

- [ ] `tests/detector/test_features.py`
- [ ] `detector/features.py`
  * Six feature groups: function-word frequency (top-100 English), sentence-length statistics (mean, std, skew, kurtosis), punctuation density, hedge-word frequency, technical-jargon density, paragraph structure
  * Writes `corpus/features.parquet` keyed by manifest entry ID

**Verification:** `corpus/features.parquet` row count equals manifest length, zero NaN, deterministic across re-runs.

---

## Phase 3 — Held-out split definition

**Goal:** Both held-out splits frozen and committed before any model fitting.

### Tasks

- [ ] `detector/heldout.json` containing `random_70_30` and `holdout_maintainer` splits
- [ ] sha256 of `detector/heldout.json` recorded in `docs/heldout-provenance.md` and commit message
- [ ] `tests/detector/test_heldout_integrity.py` verifies sha256 on every run

**Verification:** Integrity test passes; sha256 cross-referenced between commit message and provenance doc.

---

## Phase 4 — Classifier

**Goal:** Primary (Burrows' Delta) and secondary (logistic regression) classifiers with paired AUCs and 95% CIs.

### Tasks

- [ ] `tests/detector/test_burrows_delta.py`
- [ ] `detector/burrows_delta.py`
- [ ] `tests/detector/test_logistic.py`
- [ ] `detector/logistic.py`
- [ ] `tests/detector/test_validate.py`
  * Refuses to evaluate if heldout sha256 has changed since commit
  * Refuses if training set leaks any held-out ID
- [ ] `detector/validate.py`
  * Reports both AUCs with 95% CI as a pair
  * Per-maintainer AUC breakdown
  * Writes `reports/YYYYMMDD_phase4_metrics.md`

**Verification:** `python -m detector.validate` outputs both AUCs with CIs and per-maintainer table; refuses to run on tampered heldout.

---

## Phase 5 — Decision

**Goal:** A decision document classifying the result and bounding any conclusion.

### Tasks

- [ ] `reports/YYYYMMDD_phase5_decision.md` containing:
  * Both AUCs with 95% CIs
  * Per-maintainer breakdown
  * Classification: act-tier signature (random ≥0.80 AND maintainer ≥0.70), maintainer-confounded (random ≥0.80 AND maintainer <0.70), or no-signature (random <0.80)
  * Bounded scope statement
  * Next-action recommendation

**Verification:** Decision committed; operator authorizes Phase 6 or project close.

---

## Phase 6 — Monitor and apply (conditional on Phase 5 act-tier result)

**Goal:** Daily dashboard polling and arbitrary-text scoring.

### Tasks

- [ ] `tests/monitor/test_daily_poll.py`
- [ ] `monitor/daily_poll.py`
  * Logs entry count, maintainer list, CVE/GHSA delta to `monitor/logs/YYYY-MM-DD.jsonl`
  * Tracks the disclosure gap day-over-day
- [ ] `tests/detector/test_score.py`
- [ ] `detector/score.py`
  * Refuses to score on tampered heldout or unvalidated model
  * Logs every scoring run to `reports/scoring_runs.jsonl`

**Verification:** Daily poll runs 7 consecutive days clean; scoring returns feature vector, Delta score, logistic probability, similarity to nearest corpus entry, and tiered confidence label.

---

## Open Questions

1. Does the Anthropic CVD dashboard return advisory text directly or only IDs? — open, resolved by Phase 0
2. Are there ≥ minimum-corpus Mythos-credited advisories with publicly retrievable full text? — open, resolved by Phase 0
3. What text scope produces the cleanest signal? — open, decision in Phase 0
4. Can features survive normalization without losing discriminative power? — open, Phase 2 fixtures
5. How does Mythos-as-tool attribution affect signal (Mythos-drafted vs human-edited)? — open, may bound Phase 5 conclusion

---

## Dependencies

```
requests, beautifulsoup4, numpy, pandas, pyarrow, scipy, scikit-learn, nltk, pytest
(refined and pinned in Phase 0)
```
