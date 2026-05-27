# PR 1841 Fixed Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Future actionable review comments will be fixed first, then mapped with disposition evidence before resolution.

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1841#pullrequestreview-51129dee-efc1-4216-a86a-2ffd883c3cd4 -> af04ca326

Disposition: FIXED
Commit: af04ca326
Evidence: `scripts/ci/check_pr_size_governance.py` preserves leading dotfile paths when removing only literal `./`; `tests/test_check_pr_size_governance.py` covers `.github/workflows/ci.yml`, `./.github/workflows/ci.yml`, `.trivyignore`, and `./.trivyignore` as privileged paths.

Disposition: FIXED
Commit: af04ca326
Evidence: `docs/policy/PR_SCOPE_RULES.md` Quick Reference now requires `Operator approval: approved` plus `Privileged scope exception: approved` for privileged PRs over the hard cap.

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
- `DEV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/PulsePlate-ci-pr-scope-guard-policy-v2/.venv/bin/python VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/PulsePlate-ci-pr-scope-guard-policy-v2/.venv/bin/python make validate-changed` passed.
- `PATH=/Users/katsiaryna_kavaleuskaya/Developer/PulsePlate-ci-pr-scope-guard-policy-v2/.venv/bin:$PATH pre-commit run --all-files` passed.

## Machine-Heavy Local Verify Deferral

- Full local `make verify` was not run per operator instruction for this narrow CI/governance unblocker.
- Required narrow local gates passed as listed above.
- Merge readiness still requires current-head CI parity and the strict auth wrapper before any readiness claim.
