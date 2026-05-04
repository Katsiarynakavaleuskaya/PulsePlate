# PR 1660 Fixed Mapping

## Summary

Evaluation item metadata registry PR — adds psychometric-readiness metadata
layer for RAG and judgment eval fixtures.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182596200 -> ca9aaee3c
Disposition: FIXED
Commit: ca9aaee3c
Evidence: scripts/evals/eval_item_registry.py:111-133 — removed str()/bool()/list() coercion, added explicit isinstance checks for all string fields and variant_family_coverage items

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182596228 -> ca9aaee3c
Disposition: FIXED
Commit: ca9aaee3c
Evidence: tests/evals/test_eval_item_metadata_registry.py:197,224 — added cross-lane canonical_id collision assertions before dict merge

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182596232 -> ca9aaee3c
Disposition: FIXED
Commit: ca9aaee3c
Evidence: tests/evals/test_eval_item_metadata_registry.py:340-362 — added _is_forbidden_module() helper that catches submodule imports (e.g. requests.sessions)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182624869 -> 2143209dc
Disposition: FIXED
Commit: 2143209dc
Evidence: scripts/evals/eval_item_registry.py:88 — added isinstance(raw, dict) guard that rejects non-dict JSON rows with clear ValueError

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182624885
Disposition: NOT-A-BUG
Evidence: scripts/evals/eval_item_registry.py:111-133
Reason: String coercion was already removed in commit ca9aaee3c (CodeRabbit comment 1 fix). Cubic reviewed a stale commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182624891 -> a8e5751ff
Disposition: FIXED
Commit: a8e5751ff
Evidence: tests/evals/test_eval_item_metadata_registry.py:357-368 — ImportFrom guard now checks qualified names (e.g. `from urllib import request` -> `urllib.request` matched against forbidden list)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182637817
Disposition: FIXED
Commit: 021a9a1c1
Evidence: docs/review/PR_1660_FIXED_MAPPING.md — line ranges updated in this artifact revision to match current file positions

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182727140 -> 35501f99d
Disposition: FIXED
Commit: 35501f99d
Evidence: tests/evals/test_eval_item_metadata_registry.py:59-64 — _load_fixture_canonical_rows() now raises ValueError on duplicate canonical_id within same fixture file

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182727153 -> a8e5751ff
Disposition: FIXED
Commit: a8e5751ff
Evidence: tests/evals/test_eval_item_metadata_registry.py:365-376 — ImportFrom guard now checks qualified names (from urllib import request -> urllib.request)

## Premortem / Bug-hunter Hardening (self-review)

Commit 2143209dc addressed findings from internal premortem + bug-hunter pass:
- BUG-1: non-dict raw input now rejected with clear ValueError (eval_item_registry.py:88)
- BUG-3: extract_canonical_ids_from_outcome_fixture now wraps json.loads with try/except (eval_item_registry.py:213)
- RISK-1: empty variant_family_coverage now rejected (eval_item_registry.py:113)
- GAP-1: 13 negative validation tests added (test_eval_item_metadata_registry.py:410-483)
- GAP-2: index_registry_by_canonical_id duplicate detection tested (test_eval_item_metadata_registry.py:490)
- GAP-3: validate_registry_coverage error paths tested (test_eval_item_metadata_registry.py:498-508)

## Merge Readiness Evidence

- PR Body Phase2 gates: PASS (CI current-head)
- All local pre-push hooks: PASS (black, ruff, mypy, pip-audit, pytest, bandit, docker)
- 32/32 registry tests pass (15 positive + 17 negative/error-path)
- 169/169 eval tests pass
- Merge readiness gate: expected FAIL (unresolved review threads — resolve after mapping)
- pr_scope_guard: expected FAIL (>800 LoC) — Split Justification added to PR body
