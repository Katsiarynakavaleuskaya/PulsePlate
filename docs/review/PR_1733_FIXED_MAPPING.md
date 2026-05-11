<!-- markdownlint-disable MD013 MD034 -->
# PR 1733 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1733>
- Branch: `fix-current-head-fallback`
- Title: `fix(ci): make current-head fallback gating canonical-only`
- Implementing commits:
  - `1701d1fd14d57782131890aa038d1017436d8166` — make canonical CI fallback checks explicitly non-fragile and non-blocking for non-canonical workflows.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Per root `AGENTS.md` review governance, each actionable bot/human comment receives a disposition (`FIXED` / `NOT-A-BUG` / `DEFERRED`) with proof before thread resolution.

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1733#pullrequestreview-4259985730 -> 1701d1fd14d57782131890aa038d1017436d8166

Disposition: FIXED
Commit: 1701d1fd14d57782131890aa038d1017436d8166
Evidence: `scripts/ci/check_current_head_pr_checks.py:30-33` (canonical workflow identifiers moved to `CANONICAL_FALLBACK_WORKFLOW_NAMES`) and `_is_blocking_fallback_advisory` now checks membership in workflow set, not a literal.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1733#pullrequestreview-4259986894 -> 1701d1fd14d57782131890aa038d1017436d8166

Disposition: FIXED
Commit: 1701d1fd14d57782131890aa038d1017436d8166
Evidence: `tests/test_current_head_pr_checks.py:149-159` adds explicit non-blocking test for canonical check-name in non-CI workflow (`lint` under `Docker Build and Push`), matching the review nitpick.

## Merge Readiness

- [ ] Pre-flight + agent consistency: PASS locally, re-run on final HEAD before final merge-call.
- [ ] Canonical artifact: this file.
- [ ] PR body Phase2 mirror synchronized (boxes + `Fixed in Commit Mapping`).
- [ ] Required current-head CI jobs green (required check metadata unavailable case + required CI jobs).
- [ ] Post-open reviewers completed (`qa-engineer-agent` → `bug-hunter`) and actionables dispositioned.
- [ ] Mandatory wait-window after latest bot/review activity observed.

## Local Validation Evidence

- Pre-flight: `python3 scripts/orchestration/check_preflight.py` — PASS.
- Agent consistency: `python3 scripts/orchestration/check_agent_consistency.py` — PASS.
- Required test: `source .venv/bin/activate && python -m pytest tests/test_current_head_pr_checks.py -k "required_check_metadata_is_unavailable_and_optional_lane_fails"` — PASS.
