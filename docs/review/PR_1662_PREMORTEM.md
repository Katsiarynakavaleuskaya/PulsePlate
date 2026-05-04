# PR #1662 — Premortem Risk Review

<!-- markdownlint-disable MD013 -->

## Frame

It is 6 months from now. The item statistics PR merged and created false confidence that PulsePlate has psychometric calibration.

## Failure Modes

### 1. Fake IRT Claims

**Story:** A contributor sees `difficulty_band`, `anchor_item`, `invariance_agreement_rate` and assumes these are calibrated psychometric parameters. They build an "adaptive eval" on top of these descriptive stats, claiming IRT-level item discrimination without empirical calibration.

**Underlying assumption:** Field names look psychometric, so they must be psychometric.

**Warning signs:** Someone refers to `difficulty_band` as "item difficulty parameter" or cites `invariance_agreement_rate` as a "reliability coefficient" in a PR.

**Mitigation:** Explicit doc wording ("heuristic label, not calibrated IRT estimate"); AST guard test rejects IRT vocabulary in both source files (stats module + CLI runner); report output guard test rejects IRT-claiming field names in output schema.

### 2. Descriptive Stats Misread as Calibrated

**Story:** `pass_rate` and `invariance_agreement_rate` are presented in a product context as "psychometric quality measures" when they are simple proportions from 10 curated fixture items.

**Mitigation:** Report `schema_version` and doc section explicitly state "descriptive measurement layer, not psychometric calibration."

### 3. Registry/Fixture Drift

**Story:** New fixture items are added in a future PR without updating the registry, causing the statistics builder to raise `ValueError` on coverage mismatch.

**Mitigation:** Bidirectional coverage test (`test_item_statistics_covers_all_registry_items` + `test_item_statistics_has_no_orphan_items`).

### 4. Stats Overriding PASS/NO-GO

**Story:** Someone imports `build_item_statistics` from the RAG gate runner and uses instability flags to override the PASS/NO-GO decision.

**Mitigation:** AST guard tests (tests 12 + 13) verify no imports of gate/judgment decision modules in both source files (stats module + CLI runner). Decision-function vocabulary guard (test 14) rejects gate/decision function names in source. Stats module does not export any decision function.

### 5. Non-Deterministic Output

**Story:** Floating point ordering or dict ordering causes different report JSON across Python versions or platforms.

**Mitigation:** Determinism test runs computation twice and compares JSON byte-for-byte. Sorting by `(lane, canonical_id)`. Sorted keys in `json.dump`.

### 6. Provider/Network Contamination

**Story:** Accidental import of httpx/requests in the statistics module leaks network capabilities into an offline-only tool.

**Mitigation:** AST scan test (test 1) rejects network library imports at source level in both source files (stats module + CLI runner).

### 7. Docs Overclaiming Production Robustness

**Story:** Docs say "item statistics prove psychometric readiness" when they only prove curated fixture coverage for 10 items.

**Mitigation:** Required wording includes "not IRT, not psychometric calibration, not an adaptive item selector, and not a release-gate decision source." Limitations section explicitly states stats are simple proportions.

### 8. (Round 2) FileNotFoundError on Module Rename (FM-B)

**Story:** `_GUARDED_MODULES` was a hard-coded list of two Path objects. If either file was renamed, parametrized AST tests crashed with `FileNotFoundError` instead of a policy-style skip.

**Mitigation:** Added `.exists()` filter per repo policy (`tests/AGENTS.md`). Commit: 6d59716db.

### 9. (Round 2) Bare `# type: ignore` Without Justification (FM-C)

**Story:** `_make_outcome()` returned `dict[str, Any]` as `EvalOutcomeRecord` with bare `# type: ignore[return-value]`. Repo policy forbids this without justification.

**Mitigation:** Replaced with `cast(EvalOutcomeRecord, base)`. Commit: 6d59716db.

### 10. (Round 2) Shallow Timestamp Key Check (FM-D)

**Story:** `test_item_statistics_cli_output_has_no_timestamp` only checked top-level `report.keys()`. Nested `generated_at` or `timestamp` keys would pass undetected.

**Mitigation:** Recursive `_collect_all_keys()` helper now traverses all nested dicts and lists. Commit: 6d59716db.

### 11. (Round 2) Missing CLI returncode Assert (FM-E)

**Story:** Second CLI test (`TestCliOutputHasNoTimestamp`) didn't check `returncode == 0`. Silent CLI failure would produce misleading test results.

**Mitigation:** Added `assert result.returncode == 0` and `assert output_file.exists()`. Commit: 6d59716db.

## Decision

**proceed** — plan is sound as designed. All 11 failure modes (7 original + 4 from round 2) have concrete mitigations implemented in code and tests.

## Most Likely Failure

Registry/fixture drift (FM-3) — most likely because future PRs add items to fixtures without updating the registry. Bidirectional coverage tests catch this at test time.

## Hidden Assumption

The 10-item fixture set is representative enough to make descriptive statistics meaningful. In reality, 10 items per lane is a minimal foundation; the statistics become more informative with larger, more diverse item pools.

## Single Most Important Revision

None required — the current implementation has sufficient guardrails. The most impactful future improvement would be expanding the fixture set beyond 10 items to make the statistics more representative before building IRT on top.
