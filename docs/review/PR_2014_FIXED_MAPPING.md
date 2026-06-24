# PR #2014 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2014
Title: `fix(deps): bump testing dependency stack`
Branch: `codex/deps-testing-stack-refresh`

## Summary

This PR is the human-owned replacement for Dependabot PR #2001.

- `pytest`: `9.1.0` -> `9.1.1`
- `hypothesis`: `6.155.2` -> `6.155.7`
- `coverage`: `7.14.1` -> `7.14.3`

The update is scoped to testing dependency surfaces, active requirements
documentation, and the guard expectation that asserts the split test profile.
It does not touch Torch, Faraday,
RAG/vector, Docker, runtime, app/core, iOS/Fastlane, or workflow surfaces.

## Implementation Commits

- `8f3b35906fcfc83b1602f4867673f837c3577b7b` - `fix(deps): refresh testing dependency stack`
- `15b0e0c403974b714aa6815cd3b49ec518e3847f` - `test(deps): cover hypothesis testing stack pin`
- `6c85ab9ac763ae2aadd6aa846f3435f2f74d61ca` - `docs(deps): align testing requirements guide`
- `23635b2f4fb2575120d356b952898dc3796cfd41` - `docs(deps): require approved proxy in requirements guide`

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
- `VENV_PYTHON=.venv/bin/python make validate-changed` - PASS; selected `tests/test_python_supply_chain_controls.py`.
- `pre-commit run --all-files` - PASS.
- Pre-push hooks - PASS, including `pip-audit`, backend pre-push pytest, and full-repo Bandit.
- Codex Security diff scan `e8ff0e1e-63f6-4932-aac3-b78356b41f32`
  against head `4be4fc1edebd9cdbf5fbafe2cf434fc8384a862c` - PASS;
  0 findings, 12/12 review receipts completed.

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

## Post-Open Role Findings

- `qa-engineer-agent`: initially found missing `hypothesis==6.155.7` coverage
  in `tests/test_python_supply_chain_controls.py`; fixed in
  `15b0e0c403974b714aa6815cd3b49ec518e3847f`.
- `bug-hunter`: initially found stale active requirements guide examples for
  `pytest==9.1.0` / `pytest>=9.1.0`; fixed in
  `6c85ab9ac763ae2aadd6aa846f3435f2f74d61ca`.
- `Codex Security`: initial diff scan candidate validation found active
  `REQUIREMENTS.md` commands that could bypass the approved private proxy and
  an unreachable full SHA in this mapping artifact; both fixed in
  `23635b2f4fb2575120d356b952898dc3796cfd41`.
- `Codex Security`: diff scan
  `e8ff0e1e-63f6-4932-aac3-b78356b41f32` completed against head
  `4be4fc1edebd9cdbf5fbafe2cf434fc8384a862c` after those fixes with
  0 findings and 12/12 review receipts.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 15b0e0c403974b714aa6815cd3b49ec518e3847f
Evidence: `qa-engineer-agent` missing-Hypothesis guard finding is covered by `tests/test_python_supply_chain_controls.py` asserting `hypothesis==6.155.7`.

Disposition: FIXED
Commit: 15b0e0c403974b714aa6815cd3b49ec518e3847f
Evidence: `tests/test_python_supply_chain_controls.py` asserts `hypothesis==6.155.7` in the split test dependency profile.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2014#discussion_r3465713725 -> 15b0e0c403974b714aa6815cd3b49ec518e3847f

Disposition: FIXED
Commit: 6c85ab9ac763ae2aadd6aa846f3435f2f74d61ca
Evidence: `bug-hunter` stale active requirements guide finding is fixed by updating `REQUIREMENTS.md` testing-stack examples from `pytest==9.1.0` / `pytest>=9.1.0` to the refreshed stack.

Disposition: FIXED
Commit: 23635b2f4fb2575120d356b952898dc3796cfd41
Evidence: Codex Security approved-proxy bypass finding is fixed by requiring `PULSEPLATE_PYTHON_INDEX_URL` for raw `pip` / `pip-compile` examples and by preferring `scripts/ci/install_locked_python_requirements.py` in shared install examples.

Disposition: FIXED
Commit: 23635b2f4fb2575120d356b952898dc3796cfd41
Evidence: Codex Security unreachable-SHA finding is fixed by replacing the invalid mapping SHA with reachable commit `6c85ab9ac763ae2aadd6aa846f3435f2f74d61ca`.

## Implementation Evidence

- Testing stack dependency refresh ->
  `8f3b35906fcfc83b1602f4867673f837c3577b7b`
- Sourcery Hypothesis guard completion ->
  `15b0e0c403974b714aa6815cd3b49ec518e3847f`
- Active requirements guide alignment ->
  `6c85ab9ac763ae2aadd6aa846f3435f2f74d61ca`
- Codex Security approved-proxy guide and reachable mapping proof ->
  `23635b2f4fb2575120d356b952898dc3796cfd41`

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
- Post-open role passes ran in order:
  `qa-engineer-agent -> bug-hunter -> security-auditor`; their actionable
  findings are fixed above.
- Codex Security diff scan/finding discovery completed against head
  `4be4fc1edebd9cdbf5fbafe2cf434fc8384a862c` with 0 findings.
  Fresh current-head Codex Security parity and `pulseplate-pr-review` are still
  required if the branch head advances before readiness.
- CodeRabbit, Sourcery, Cubic, bot actionables, review-thread disposition,
  current-head CI, diff coverage, and strict
  `check_merge_ready.py --require-auth` must pass before any readiness or merge
  claim.
