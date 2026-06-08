# PR 1907 Fixed Mapping

## Summary

This PR adds an internal-only food provenance verification bridge that converts
food-source provenance and confidence traces into existing `VerificationBundle`
and `VerificationProvenance` lineage artifacts. Public API and response shapes
are unchanged.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/4be1d7740a8b.json`

- Packet id: `4be1d7740a8b`
- Branch: `feat/food-provenance-verification`
- Head commit at artifact creation: `236632c3a`

## Scope

IN:

- `core/food_provenance_verification.py`
- `tests/test_food_provenance_verification_bundle.py`
- `.github/workflows/ci.yml` (adds the focused test to the existing `food_catalog` coverage-producing suite)
- `scripts/ci/ci_risk_profile.py` (routes this new core provenance file to the existing `food_catalog` suite)
- `tests/test_ci_risk_profile.py`

OUT:

- public API response shape changes
- OpenAPI artifacts
- GraphRAG / semantic-cache / cache admission changes
- frontend / iOS changes
- provider or network behavior

## Agent Execution Log

- `agent-coordinator`: PASS. Confirmed internal-only provenance bridge scope.
- `cursor-specialist-agent`: PASS after repair. Confirmed workflow/script order.
- `architecture-specialist`: PASS after repair pre-open; PASS post-open with one optional future policy-scope note.
- `qa-engineer-agent`: PASS after fixes. Observations fixed in `8d615f418`.
- `bug-hunter`: PASS after fixes. P1 findings fixed in `c899bce80`.
- `security-auditor`: PASS after fixes. High finding fixed in `b8fe4bfb4`.
- `pulseplate-pr-review`: PASS after fixes. Findings fixed in `5c2219031`, `7f80ac2cf`, and `236632c3a`.

## Skill Execution Log

- `pulseplate-workflow`: coordinator-first setup and scoped preflight.
- `pulseplate-backend-endpoints`: backend/core contract guardrails.
- `pulseplate-gates`: focused tests, changed validation, pre-commit evidence.
- `pulseplate-premortem-risk-review`: actual-diff premortem before PR open.
- `pulseplate-pr-review`: post-open self-review after role lane.
- `code-review-expert`: review checklist context.

## Experiment Runner Evidence

Packet: `artifacts/orchestration/experiments/food_provenance_oracle_packet.json`

Artifact: artifacts/orchestration/experiments/results/exp-88ab466995e9.json

Status: accepted.

Oracle commands:

- `python -m pytest -q tests/test_food_provenance_verification_bundle.py` - PASS at oracle time.
- `python -m pytest -q tests/test_repo_policy_guards.py tests/test_food_provenance_verification_bundle.py` - PASS at oracle time.

The Experiment Runner materially shaped the pre-open validation and commit
decision. Commit `06097a817` includes the canonical co-author trailer.

## Risk Fix Matrix

| Risk ID | Failure mode | Fix | Regression test | Evidence command | Fix commit SHA | Evidence | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PREMORTEM-001` | Duplicate same-source inputs could overwrite record/version lineage. | Resolve lineage by `(source, nutrient)` and fail closed on ambiguous duplicate lineage. | `test_food_provenance_traces_fail_closed_on_ambiguous_duplicate_source` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `06097a817` | `core/food_provenance_verification.py:77`; `tests/test_food_provenance_verification_bundle.py:393` | FIXED |
| `PREMORTEM-002` | Boolean confidence could coerce to `1.0`. | Reject `bool` before numeric conversion. | `test_food_provenance_bundle_rejects_bool_confidence` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `06097a817` | `core/food_provenance_verification.py:348`; `tests/test_food_provenance_verification_bundle.py:126` | FIXED |
| `PREMORTEM-003` | Invalid `min_confidence` could admit low confidence. | Invalid thresholds fall back to default. | `test_food_provenance_bundle_falls_back_for_invalid_min_confidence` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `06097a817` | `core/food_provenance_verification.py:209`; `tests/test_food_provenance_verification_bundle.py:143` | FIXED |
| `QA-001` | Missing record-level confidence fallback coverage. | Added fallback test for missing nutrient-specific confidence. | `test_food_provenance_traces_use_record_confidence_fallback` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `8d615f418` | `tests/test_food_provenance_verification_bundle.py:222` | FIXED |
| `QA-002` | Missing unsafe URL/path token coverage. | Added URL/path token rejection test and safer normalization. | `test_food_provenance_trace_tokens_do_not_leak_raw_url_or_path_values` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `8d615f418` | `core/food_provenance_verification.py:359`; `tests/test_food_provenance_verification_bundle.py:259` | FIXED |
| `BUG-001` | Confidence values above `1.0` could pass. | Added `[0, 1]` confidence range validation. | `test_food_provenance_bundle_rejects_out_of_range_confidence` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `c899bce80` | `core/food_provenance_verification.py:218`; `tests/test_food_provenance_verification_bundle.py:165` | FIXED |
| `BUG-002` | Path-like record/version/source tokens could leak into evidence refs. | Reject URL/path/traversal/domain-like tokens before normalization. | `test_food_provenance_trace_rejects_path_like_record_and_version_values` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `c899bce80` | `core/food_provenance_verification.py:359`; `tests/test_food_provenance_verification_bundle.py:301` | FIXED |
| `SEC-001` | Secret/email-like tokens could leak in plaintext evidence refs. | Reject token/email-like values before evidence ref construction. | `test_food_provenance_trace_rejects_secret_and_email_like_tokens` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `b8fe4bfb4` | `core/food_provenance_verification.py:24`; `tests/test_food_provenance_verification_bundle.py:325` | FIXED |
| `PR-REVIEW-001` | Realistic token bodies and mixed valid/invalid rows could still pass. | Expanded token detection and fail closed on any rejected trace row. | `test_food_provenance_bundle_fails_closed_for_mixed_valid_and_rejected_rows` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `5c2219031` | `core/food_provenance_verification.py:42`; `tests/test_food_provenance_verification_bundle.py:365` | FIXED |
| `PR-REVIEW-002` | Safe SKU-style food identifiers were over-rejected. | Narrowed OpenAI token detection to real `sk-` prefix and added safe SKU test. | `test_food_provenance_trace_allows_sku_style_food_identifiers` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `7f80ac2cf` | `core/food_provenance_verification.py:27`; `tests/test_food_provenance_verification_bundle.py:356` | FIXED |
| `PR-REVIEW-003` | Domain-like query/fragment values could enter evidence refs. | Reject domain-like values followed by query/fragment delimiters. | `test_food_provenance_trace_rejects_domain_query_and_fragment_values` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `236632c3a` | `core/food_provenance_verification.py:23`; `tests/test_food_provenance_verification_bundle.py:376` | FIXED |
| `BOT-SOURCERY-001` | Sourcery requested lineage-present validation use `traces` instead of derived `evidence_refs`. | `_lineage_present_artifact` now checks `traces` directly. | `test_food_provenance_bundle_fails_closed_for_missing_traces` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `25c93d85019895e1928fba32c8caf83e972b1839` | `core/food_provenance_verification.py:268`; `tests/test_food_provenance_verification_bundle.py:61` | FIXED |
| `BOT-CODERABBIT-001` | CodeRabbit requested boolean `min_confidence` fail-closed coverage and code validation. | `min_confidence` now resolves through `_numeric_float`, rejecting bool; regression test added. | `test_food_provenance_bundle_falls_back_for_bool_min_confidence` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `25c93d85019895e1928fba32c8caf83e972b1839` | `core/food_provenance_verification.py:225`; `tests/test_food_provenance_verification_bundle.py:160` | FIXED |
| `BOT-CUBIC-001` | Cubic identified over-broad local-path prefix filtering. | Local-path prefix check is exact-match only; safe private-label/SKU identifiers are covered. | `test_food_provenance_trace_allows_sku_style_food_identifiers` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` | `7f80ac2cf887c51e09410186bb9460d63267ebc9` | `core/food_provenance_verification.py:373`; `tests/test_food_provenance_verification_bundle.py:356` | FIXED |
| `CI-COV-001` | CI diff-coverage reported 0% because `test-pr` coverage artifact did not include the new focused test file. | Added `tests/test_food_provenance_verification_bundle.py` to the existing `food_catalog` contract/risk suite in `.github/workflows/ci.yml`. | `test_food_provenance_verification_bundle.py` via CI `test-pr` | `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py`; `pre-commit run --all-files` | `b42921f903b089887ce2e0ad985cb7d976a82d61` | `.github/workflows/ci.yml`; `tests/test_food_provenance_verification_bundle.py` | FIXED |
| `CI-COV-002` | CI still did not select `food_catalog` for `core/food_provenance_verification.py`, so the coverage-producing suite was not routed. | Added `core/food_provenance_verification.py` to the `food_catalog` risk profile and covered it with a routing regression test. | `test_food_provenance_core_change_hits_food_catalog_and_route_groups` | `.venv/bin/python -m pytest -q tests/test_ci_risk_profile.py tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py`; `pre-commit run --all-files` | `099ca9beb6db8a23941cc8c1d076d74f537f8197` | `scripts/ci/ci_risk_profile.py`; `tests/test_ci_risk_profile.py` | FIXED |
| `CI-COV-003` | Local diff-cover still showed uncovered defensive branches in the new core helper. | Added input-driven regression tests for missing provenance, exact local-path prefix rejection, malformed mapping/raw-input shapes, and missing source/nutrient lineage rows. | `test_food_provenance_bundle_fails_closed_for_missing_source_provenance`; `test_food_provenance_trace_extraction_handles_malformed_record_shapes` | `.venv/bin/diff-cover coverage.xml --compare-branch=origin/main --fail-under=97 ...` | TBD | `tests/test_food_provenance_verification_bundle.py`; local diff-cover reports `core/food_provenance_verification.py (100%)` | FIXED |
| `SCOPE-001` | Helper has no production call site in this foundation slice. | Intentional foundation-only scope; no runtime exposure or public DTO changes. | N/A | `git grep -n "build_meal_plan_food_provenance_bundle" -- app core tests` | N/A | Helper/test-only usage in current diff; PR body `Out of scope` | NOT-A-BUG |

## Tests / Bounded Checks

- `python3 scripts/orchestration/check_preflight.py` - PASS.
- `python3 scripts/orchestration/check_preflight.py --path .github/workflows/ci.yml --path core/food_provenance_verification.py --path tests/test_food_provenance_verification_bundle.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `.venv/bin/python -m pytest -q tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` - PASS, 34 passed.
- `.venv/bin/python -m pytest -q tests/test_ci_risk_profile.py tests/test_food_provenance_verification_bundle.py tests/test_repo_policy_guards.py` - PASS.
- Local diff-cover after focused coverage run - PASS, `core/food_provenance_verification.py (100%)`.
- `make validate-changed` - PASS, 16 passed.
- `pre-commit run --all-files` - PASS.
- Push hooks - PASS: changed-file mypy, pip-audit, pre-push pytest, full-repo bandit, docker build test.

Full `make verify` was not run by operator instruction. This PR relies on
changed-scope local gates plus current-head CI for heavy validation.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1907#pullrequestreview-4447927847 -> 25c93d85019895e1928fba32c8caf83e972b1839
Disposition: FIXED
Commit: 25c93d85019895e1928fba32c8caf83e972b1839
Evidence: `core/food_provenance_verification.py:268`; `tests/test_food_provenance_verification_bundle.py:61`
Reason: Sourcery's lineage-present suggestion is fixed; `_lineage_present_artifact` now checks `traces` directly and the missing-traces regression remains covered.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1907#discussion_r3371935928 -> 25c93d85019895e1928fba32c8caf83e972b1839
Disposition: FIXED
Commit: 25c93d85019895e1928fba32c8caf83e972b1839
Evidence: `core/food_provenance_verification.py:268`; `tests/test_food_provenance_verification_bundle.py:61`
Reason: Sourcery line comment is fixed by the same trace-based lineage presence check.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1907#pullrequestreview-4447938648 -> 25c93d85019895e1928fba32c8caf83e972b1839
Disposition: FIXED
Commit: 25c93d85019895e1928fba32c8caf83e972b1839
Evidence: `core/food_provenance_verification.py:225`; `tests/test_food_provenance_verification_bundle.py:160`
Reason: CodeRabbit's actionable boolean `min_confidence` review is fixed by routing threshold validation through `_numeric_float` and adding the bool regression test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1907#discussion_r3371944107 -> 25c93d85019895e1928fba32c8caf83e972b1839
Disposition: FIXED
Commit: 25c93d85019895e1928fba32c8caf83e972b1839
Evidence: `core/food_provenance_verification.py:225`; `tests/test_food_provenance_verification_bundle.py:160`
Reason: CodeRabbit line comment is fixed by the same boolean `min_confidence` validation and regression coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1907#pullrequestreview-4448110066 -> 7f80ac2cf887c51e09410186bb9460d63267ebc9
Disposition: FIXED
Commit: 7f80ac2cf887c51e09410186bb9460d63267ebc9
Evidence: `core/food_provenance_verification.py:373`; `tests/test_food_provenance_verification_bundle.py:356`
Reason: Cubic's over-broad local-path prefix finding is fixed by exact-match local prefix rejection and safe SKU/private-label regression coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1907#discussion_r3372085358 -> 7f80ac2cf887c51e09410186bb9460d63267ebc9
Disposition: FIXED
Commit: 7f80ac2cf887c51e09410186bb9460d63267ebc9
Evidence: `core/food_provenance_verification.py:373`; `tests/test_food_provenance_verification_bundle.py:356`
Reason: Cubic line comment is fixed by the same exact-match local prefix check.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1907#pullrequestreview-4449728555 -> 099ca9beb6db8a23941cc8c1d076d74f537f8197
Disposition: FIXED
Commit: 099ca9beb6db8a23941cc8c1d076d74f537f8197
Evidence: `docs/review/PR_1907_FIXED_MAPPING.md:89`; `docs/review/PR_1907_FIXED_MAPPING.md:90`
Reason: CodeRabbit requested replacing `TBD` placeholders in CI-COV rows; the mapping now records exact fix SHAs for both CI coverage routing fixes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1907#discussion_r3373413965 -> 099ca9beb6db8a23941cc8c1d076d74f537f8197
Disposition: FIXED
Commit: 099ca9beb6db8a23941cc8c1d076d74f537f8197
Evidence: `docs/review/PR_1907_FIXED_MAPPING.md:89`; `docs/review/PR_1907_FIXED_MAPPING.md:90`
Reason: CodeRabbit line comment is fixed by the same exact SHA replacement.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1907#pullrequestreview-4449770185 -> 099ca9beb6db8a23941cc8c1d076d74f537f8197
Disposition: FIXED
Commit: 099ca9beb6db8a23941cc8c1d076d74f537f8197
Evidence: `docs/review/PR_1907_FIXED_MAPPING.md:89`; `docs/review/PR_1907_FIXED_MAPPING.md:90`
Reason: Cubic requested replacing `TBD` placeholders in CI-COV rows; the mapping now records exact fix SHAs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1907#discussion_r3373445922 -> 099ca9beb6db8a23941cc8c1d076d74f537f8197
Disposition: FIXED
Commit: 099ca9beb6db8a23941cc8c1d076d74f537f8197
Evidence: `docs/review/PR_1907_FIXED_MAPPING.md:89`; `docs/review/PR_1907_FIXED_MAPPING.md:90`
Reason: Cubic line comment is fixed by the same exact SHA replacement.

## Bot Review Summary

- CodeRabbit: FIXED. Evidence: review/comment mapping above and `test_food_provenance_bundle_falls_back_for_bool_min_confidence`.
- Codex connector: NOT-A-BUG. Evidence: usage-limit notice only, no code finding.
- Sourcery: FIXED. Evidence: review/comment mapping above and `_lineage_present_artifact` now checks `traces`.
- Cubic: FIXED. Evidence: review/comment mapping above and safe SKU/private-label token regression coverage.

## Deferred / Follow-ups

None.

## Merge Readiness

Not merge-ready yet. Pending after this artifact commit:

- Current-head CI rerun with `PR Body Phase2 gates` PASS.
- Current-head CI rerun with `Merge readiness gate` updated for this artifact.
- Pending required/security/test checks complete.
- Cubic / Sourcery / external bot status checked for no actionables.
- Mandatory wait-window and final strict merge-readiness pass per `AGENTS.md`.
