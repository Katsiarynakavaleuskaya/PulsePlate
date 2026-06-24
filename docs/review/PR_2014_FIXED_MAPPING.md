# PR #2014 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2014
Title: `fix(deps): bump testing dependency stack`
Branch: `codex/deps-testing-stack-refresh`

## Summary

This PR is the human-owned replacement for Dependabot PR #2001.

- `pytest`: `9.1.0` -> `9.1.1`
- `hypothesis`: `6.155.2` -> `6.155.7`
- `coverage`: `7.14.1` -> `7.14.3`

The update is scoped to testing dependency surfaces and the guard expectation
that asserts the split test profile. It does not touch Torch, Faraday,
RAG/vector, Docker, runtime, app/core, iOS/Fastlane, or workflow surfaces.

## Implementation Commit

- `8f3b35906fcfc83b1602f4867673f837c3577b7b` - `fix(deps): refresh testing dependency stack`

The implementation commit includes the governed Experiment Runner attribution
trailer:

`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Lane Start Provenance

- Worktree: `worktrees/deps-testing-stack-refresh`
- Branch: `codex/deps-testing-stack-refresh`
- Packet: `artifacts/orchestration/task_packets/797969cddfec.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Role dispatch:
  `.venv/bin/python scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/797969cddfec.json --pretty`
- Pre-open role order completed:
  `agent-coordinator -> cursor-specialist-agent -> architecture-specialist`

## Premortem Risk Review

- Pass: `pulseplate-premortem-risk-review`
- Status: `PASS_WITH_REQUIRED_PRE_OPEN_GATES`
- Result: no blocking findings remained in the inspected diff.
- Scope evidence: 10 files changed, 23 insertions, 23 deletions.
- Controlled risks:
  - Broad lock churn rejected after `piptools compile` through the approved proxy
    attempted unrelated transitive updates.
  - Raw private index URL emission rejected by keeping tracked lock headers
    sanitized and auditing added lines.
  - Unsafe `pip==...` lock churn rejected per repo-managed lock policy.
  - Stale test expectation drift fixed in
    `tests/test_python_supply_chain_controls.py`.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-2c147f9cd4f3.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-2c147f9cd4f3.json`
- Status: `accepted`
- Mode: `oracle_only_governance_reviewer`
- Contribution: `oracle_review`
- Mutated paths: `[]`
- Shared tree untouched: `true`
- Co-author required: yes, included on implementation commit
  `8f3b35906fcfc83b1602f4867673f837c3577b7b`.

## Local Validation

Focused local gates:

- `python3 scripts/orchestration/check_preflight.py --path constraints.txt --path requirements-all.txt --path requirements-ci-lite.in --path requirements-ci-lite.txt --path requirements-dev.in --path requirements-dev.txt --path requirements-test.in --path requirements-test.txt --path requirements-lock.txt --path tests/test_python_supply_chain_controls.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- Approved proxy exact-wheel proof for `pytest==9.1.1`,
  `hypothesis==6.155.7`, and `coverage==7.14.3` using
  `.venv/bin/python -m pip download --isolated --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --only-binary=:all: --no-deps` - PASS
- `.venv/bin/python scripts/ci/install_locked_python_requirements.py --requirements-file requirements-dev.txt --constraints-file constraints.txt --install-dev --preflight-only` - PASS
- `.venv/bin/python scripts/ci/install_locked_python_requirements.py --requirements-file requirements-test.txt --constraints-file constraints.txt --preflight-only` - PASS
- `.venv/bin/python scripts/ci/install_locked_python_requirements.py --requirements-file requirements-ci-lite.txt --constraints-file constraints.txt --preflight-only` - PASS
- `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/test_dependency_security_guard.py tests/guards/test_security_devtooling_regression_guards.py` - PASS
- `.venv/bin/python -m pip_audit -r requirements-dev.txt` - PASS; no known vulnerabilities found.
- `.venv/bin/python -m pip_audit -r requirements-test.txt` - PASS; no known vulnerabilities found.
- `.venv/bin/python -m pip_audit -r requirements-ci-lite.txt` - PASS; no known vulnerabilities found.
- `.venv/bin/python -m pip_audit -r requirements-lock.txt` - PASS; no known vulnerabilities found.
- `VENV_PYTHON=.venv/bin/python make validate-changed` - PASS; selected no Python or cross-surface governance files, so it is not sufficient alone for this dependency lane.
- `pre-commit run --all-files` - PASS.
- Pre-push hooks - PASS, including `pip-audit`, backend pre-push pytest, and full-repo Bandit.

Full local `make verify` was not run under the operator-approved machine-heavy
exception for this dependency lane. Current-head CI is the required heavy parity
signal before any merge-readiness claim.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No actionable review threads existed at PR open. Any post-open bot, human,
CodeRabbit, Sourcery, Cubic, Codex Security, QA, bug-hunter, security-auditor,
or `pulseplate-pr-review` finding remains blocking until fixed or formally
dispositioned with evidence.

## Fixed in Commit Mapping

- No actionable review comments at artifact creation time.

## Implementation Evidence

- Testing stack dependency refresh ->
  `8f3b35906fcfc83b1602f4867673f837c3577b7b`

## Deferred / Follow-ups

- Dependabot PR #2001 remains open until this human-owned replacement is merged
  or otherwise confirmed as superseding.
- Dependabot alerts #160/#161/#162 for `torch` remain deferred because the GHSA
  lane currently has no patched version.
- Dependabot alert #224 for `faraday` remains a dedicated Fastlane/Ruby security
  lane for dependency graph remediation/removal.

## Merge Readiness

Not merge-ready at artifact creation time.

- Full local `make verify` is deferred under the operator-approved machine-heavy
  exception documented above.
- Post-open role passes are still required:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- Codex Security diff scan/finding discovery and `pulseplate-pr-review` are
  still required.
- CodeRabbit, Sourcery, Cubic, bot actionables, review-thread disposition,
  current-head CI, diff coverage, and strict
  `check_merge_ready.py --require-auth` must pass before any readiness or merge
  claim.
