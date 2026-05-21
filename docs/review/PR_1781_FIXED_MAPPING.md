# PR #1781 - Fixed in Commit Mapping

**PR:** fix(ci): install frontend token toolchain before shards
**Branch:** `codex/main-design-token-toolchain-stabilization`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping initialized
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: ec8e52289
Evidence: Added locked frontend dependency setup before `test-pr`, `test-feature`, and `test-main` Python pytest execution; hardened `tests/test_design_token_parity.py` so CI fails closed on missing or partial `style-dictionary`; added workflow regression coverage for frontend dependency setup ordering.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1781 -> ec8e52289

Disposition: FIXED
Commit: 56a71b68e
Evidence: Addressed Sourcery/QA feedback by routing root Node installs through the same bounded retry composite action as frontend installs, generalizing the composite action description, adding workflow assertions for root retry usage, and adding a negative traversal test for `style-dictionary` package entrypoints. Local proof: focused review tests passed (`4 passed`), full design-token parity passed (`16 passed`), workflow/supply-chain pack passed (`19 passed`), and `make validate-changed` passed (`34 passed`).
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1781#pullrequestreview-4332081193 -> 56a71b68e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1781#discussion_r3277027875 -> 56a71b68e

Disposition: FIXED
Commit: 0ea50e696
Evidence: Closed Sourcery high-level helper/test maintainability feedback by replacing CI-readiness `assert` paths with explicit `pytest.fail(...)` diagnostics and centralizing the Python test job list used by the workflow regression guard. Local proof: focused review tests passed (`4 passed`), full design-token parity passed (`16 passed`), workflow/supply-chain pack passed (`19 passed`), and `make validate-changed` passed (`34 passed`).
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1781#pullrequestreview-4332081193 -> 0ea50e696
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1781#discussion_r3277027880 -> 0ea50e696

## Premortem Disposition

- FIXED: CI shard race is addressed by installing `frontend` dependencies once at job level before pytest shards can run design-token parity.
- FIXED: Partial/corrupt `style-dictionary` installs now fail with actionable diagnostics instead of relying on a directory-only guard.
- NOT-A-BUG: No token values, product runtime, frontend UI, OpenAPI contracts, food-data, philosophy, or semantic-cache runtime changes are required for this `main` stabilization.
- DEFERRED: Full local `make verify` remains deferred under the operator-approved machine-heavy CI/tooling exception; current-head PR CI parity is required before merge-readiness claims.

## Validation

- `python3 scripts/orchestration/check_preflight.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/orchestration/task_bootstrap.py ... --task-class "Orchestration" --pr-phase pre_open` - PASS, packet `37ec3e059043`, primary `agent-coordinator`
- `python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py::test_python_test_jobs_install_frontend_dependencies_before_pytest tests/test_design_token_parity.py::test_style_dictionary_readiness_uses_package_export_target tests/test_design_token_parity.py::test_style_dictionary_readiness_rejects_partial_install` - PASS (`3 passed`)
- `cd frontend && npm ci` - PASS from committed `frontend/package-lock.json`; npm reported 2 existing moderate audit findings and no lockfile changes were made.
- `python -m pytest -q tests/test_design_token_parity.py` - PASS (`15 passed`)
- `python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_python_supply_chain_controls.py::test_ci_workflow_uses_single_direct_proxy_python_install_path_per_job` - PASS (`19 passed`)
- `make validate-changed` - PASS; no changed Python production files
- `pre-commit run --all-files` - PASS
- Commit hook with root `.venv` on `PATH` - PASS
- Pre-push hook - PASS, including `pip-audit`, backend pre-push tests, and full-repo Bandit; docker build skipped because no matching files changed.

## Full Verify Deferral

Full local `make verify` is deferred for this narrow CI/tooling stabilization per operator instruction and the documented machine-heavy exception. Merge readiness requires the narrow local bundle plus current-head PR CI parity, especially `CI / test-main (3.12, 90)`.

## Post-Open Review

- Post-open bootstrap packet: `artifacts/orchestration/task_packets/pr_1781_post_open_review.json` (local gitignored artifact).
- Mandatory post-open QA -> bug-hunter pass: completed. QA found two Sourcery-aligned actionables; bug-hunter found no code bugs after the fixes and blocked readiness only on stale mapping/body/current-head evidence.
- Security/Codex Security diff-scoped pass: PASS. Security-auditor found no blockers: npm workflow changes use local bounded retry action without permission expansion, composite action callers stay within `.`/`frontend`, style-dictionary parsing reads metadata only and keeps entrypoints inside the package root, and `.secrets.baseline` changes are line-number/generated timestamp drift only.
- CodeRabbit: no actionables reported on the mapping-only update; current-head review after latest push pending.
- Sourcery: actionables from review `pullrequestreview-4332081193` and resolved threads `discussion_r3277027875` / `discussion_r3277027880` are fixed in `56a71b68e` and `0ea50e696`; current-head review after latest push pending.
- Cubic: neutral/no actionable signal observed before latest push; current-head activity pending.
- Current-head checks: pending.
- Review-thread disposition guard: pending.

## Experiment Runner

Not applicable. Experiment Runner did not materially contribute to this commit, so no co-author trailer is required.
