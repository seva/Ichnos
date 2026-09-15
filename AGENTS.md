# ichnos — Mythos Footprint Detector

A research instrument that tests whether Claude Mythos has a stylometric signature detectable in Glasswing-credited vulnerability advisories, by training a classifier on Mythos-attributed advisory text against same-maintainer same-period controls and validating on a held-out maintainer to distinguish a Mythos signature from a maintainer confound.

## Session Start

1. Read `METHODOLOGY.md`
2. Read `ARCHITECTURE.md` — verify component descriptions match current code before acting
3. Scan `IMPLEMENTATION.md` checkboxes — first unchecked task is current state
4. Check open GitHub issues for failures and decisions
5. Search memory for relevant prior knowledge

## Conventions

- **Corpus integrity.** Every entry in `corpus/` is fetched from a logged URL recorded in `corpus/manifest.jsonl` with `{url, fetch_ts, sha256, class, maintainer, domain}`. If a fetch fails, log the failure and skip; never invent advisory text or attribution. Plausibility is not evidence.
- **Frozen held-out splits.** `detector/heldout.json` is committed before any model fitting. Its sha256 is recorded in `docs/heldout-provenance.md` and verified on every validation run. Touching it post-commit invalidates all downstream results and requires opening a corruption issue.
- **Two AUCs reported as a pair.** Random-split AUC and held-out-maintainer mean AUC are always reported together with 95% CIs. A single AUC is rejected at audit. If random-split AUC is high but held-out-maintainer is low, the finding is a maintainer confound, not a Mythos signature — classify it as such, do not suppress.
- **No mediated stylometry.** Features must be computable from raw text without LLM mediation (no "ask GPT to rate Mythos-likeness"). Mediated features are circular and disqualifying.
- **Black-box discipline.** Mythos is treated as an opaque source observed only through outputs. The project does not call the Mythos model, does not infer architecture, and does not speculate about training data.
- **Immutable reports.** Files in `reports/` are append-only. Revisions create a new dated file referencing the prior; nothing is overwritten or deleted. Updates are also reflected in the open phase issue.
- **Operator.** Seva Lapsha (@swearlock). Terse, will probe for fabrication, expects numbered findings with citations. Sarcasm and unsolicited alternatives are correct behavior, not defects.
