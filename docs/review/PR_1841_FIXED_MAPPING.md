# PR 1841 Fixed Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Future actionable review comments will be fixed first, then mapped with disposition evidence before resolution.

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1841#discussion_r3309708921 -> af04ca326
Disposition: FIXED
Commit: af04ca326
Evidence: `scripts/ci/check_pr_size_governance.py` preserves leading dotfile paths when removing only literal `./`; `tests/test_check_pr_size_governance.py` covers `.github/workflows/ci.yml`, `./.github/workflows/ci.yml`, `.trivyignore`, and `./.trivyignore` as privileged paths.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1841#discussion_r3309708946 -> af04ca326
Disposition: FIXED
Commit: af04ca326
Evidence: `docs/policy/PR_SCOPE_RULES.md` Quick Reference now requires `Operator approval: approved` plus `Privileged scope exception: approved` for privileged PRs over the hard cap.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1841#discussion_r3310205948 -> 62a5b19a
Disposition: FIXED
Commit: 62a5b19a
Evidence: `scripts/ci/check_pr_size_governance.py` evaluates frontend/backend mixed scope before the micro threshold; `tests/test_check_pr_size_governance.py` covers a two-file frontend/backend mix that must classify as `frontend_vertical_mvp`, not `micro`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1841#pullrequestreview-4371616259 -> 62a5b19a
Disposition: FIXED
Commit: 62a5b19a
Evidence: Parent CodeRabbit review summarized the same actionable `classify_pr_scope` micro frontend/backend mix issue fixed by commit `62a5b19a`; `tests/test_check_pr_size_governance.py` covers the regression.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/pr-scope-guard-policy-v2-oracle-result.json`

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/cdd4a64c3c37.json`

## Merge Readiness

- [ ] Current-head CI is complete and passing.
- [ ] PR Scope Guard passes on this PR.
- [ ] No pending required jobs.
- [ ] No unresolved review threads.
- [ ] No actionable bot comments remain.
- [ ] Strict merge-readiness wrapper passes with auth.
- [ ] Mandatory wait-window completed.

## Local Evidence

- `gh run view 26497109962 --repo Katsiarynakavaleuskaya/PulsePlate --job 78027942164 --log` diagnosed the original failure as `scripts/ci/check_pr_size_governance.py` in the `PR size governance` step.
- `.venv/bin/python scripts/orchestration/check_preflight.py` passed.
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py` passed.
- `.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py` passed.
- `.venv/bin/python -m pytest -q tests/test_repo_policy_guards.py` passed.
- `DEV_PYTHON=$PWD/.venv/bin/python VENV_PYTHON=$PWD/.venv/bin/python make validate-changed` passed.
- `PATH=$PWD/.venv/bin:$PATH pre-commit run --all-files` passed.

## Machine-Heavy Local Verify Deferral

- Full local `make verify` was not run per operator instruction for this narrow CI/governance unblocker.
- Required narrow local gates passed as listed above.
- Merge readiness still requires current-head CI parity and the strict auth wrapper before any readiness claim.
