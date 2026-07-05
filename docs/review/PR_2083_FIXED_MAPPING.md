# PR 2083 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2083

Branch: `codex/deps-testing-controlled`

## Summary

This PR supersedes Dependabot PR #2077 with a current-main, user-owned
testing-dependency lane. It updates only `coverage`, `faker`, and `hypothesis`
across the test/dev dependency surfaces and keeps runtime requirements
unchanged.

The replacement is intentionally narrower than #2077: it rejects generated
lock churn, does not add `pip==26.1.2`, and does not change Trivy policy,
Docker, OpenAPI, or application code.

## Discussion Thread Pass

- [x] Discussion-thread pass completed for replacement PR open state.
- [x] Fixed in commit mapping completed for replacement findings.
- [ ] Current-head GitHub CI and external bot state pending for PR #2083.

## Fixed in Commit Mapping

- No actionable review comments at PR open time.

## Replacement Findings

Disposition: FIXED
Commit: b83f1de9a99d42053a9ebbfb6a38ca60ea0f4cf27
Evidence: `requirements-dev.in`, `requirements-test.in`,
`requirements-dev.txt`, `requirements-test.txt`, `requirements-lock.txt`,
`constraints.txt`, and `requirements-all.txt` now align on
`coverage==7.15.0` / `coverage>=7.15.0`, `faker==40.28.1`, and
`hypothesis==6.156.1`; the guard expectation in
`tests/test_python_supply_chain_controls.py` was updated to the same test
profile pins.
Reason: Dependabot PR #2077 bundled the requested testing dependency updates
with broad generated lock churn. This replacement keeps the intended testing
dependency update while preserving the repo's bounded dependency-surface
contract.

Disposition: FIXED
Commit: b83f1de9a99d42053a9ebbfb6a38ca60ea0f4cf27
Evidence: `requirements.txt` is unchanged, and focused supply-chain tests plus
`python3 scripts/ci/check_python_dependency_surfaces.py` and
`python3 verify_requirements.py` passed.
Reason: The testing dependency updates must not promote dev/test tooling into
runtime dependency authority.

Disposition: FIXED
Commit: b83f1de9a99d42053a9ebbfb6a38ca60ea0f4cf27
Evidence: `requirements-dev.txt`, `requirements-test.txt`,
`requirements-lock.txt`, `requirements-all.txt`, and `constraints.txt` contain
no `pip==...` pins.
Reason: The repo-managed lock surfaces intentionally reject unsafe `pip` pins;
the #2077 generated output included `pip==26.1.2`, so it is not acceptable as a
direct merge candidate.

Disposition: NOT-A-BUG
Evidence: `trivy/`, `.trivyignore`, Docker files, and application code are
unchanged in this branch. The operator explicitly requested no additional
scans on this lane.
Reason: No new Trivy suppression or runtime image surface is introduced by the
controlled testing-dependency replacement. Current-head GitHub CI remains the
authoritative remote signal before any merge-readiness claim.

## Production Premortem

Most likely failure: generated dependency tooling reintroduces broad lock churn
or `pip==...` while trying to make the Dependabot PR look mechanically
complete.
Mitigation: this branch uses a bounded manual dependency-surface diff and
verifies that managed lock/constraint surfaces contain no `pip==...` pins.

Most dangerous failure: test/dev dependencies leak into runtime install
authority or production image surfaces.
Mitigation: `requirements.txt` is unchanged; dependency-surface checks,
`verify_requirements.py`, and focused supply-chain guard tests passed.

Hidden assumption: a Dependabot testing group can be merged directly when the
headline packages are safe. This PR rejects that assumption because generated
lock churn can change security posture independently of the headline updates.

Decision: proceed with the controlled replacement branch and close #2077 as
superseded after replacement PR evidence is published.

## Experiment Runner Evidence

No Experiment Runner oracle output is used as merge-readiness evidence for this
lane.

Experiment Runner bootstrap was attempted but blocked by the runner's hard
candidate budget:

- `.venv/bin/python` oracle was rejected because the binary is not in the
  immutable oracle allowlist.
- `python3 -m pytest ...` without retry budget was rejected because
  `retry_budget` must be greater than zero.
- `python3 -m pytest ... --retry-budget 1` over the full dependency surface was
  rejected because `max_changed_files` must be `<= 5`.

Disposition: this is a runner budget limitation, not a dependency-lane reason
to narrow the production diff artificially. The safe dependency surface requires
eight synchronized files.

## Implementation Evidence

- Commit: b83f1de9a99d42053a9ebbfb6a38ca60ea0f4cf27
- Evidence: `git diff --name-only origin/main...HEAD` contained the seven
  dependency files plus `tests/test_python_supply_chain_controls.py` before
  this mapping artifact commit.
- Evidence: `git diff --exit-code -- requirements.txt` passed.
- Evidence: `git diff --exit-code -- trivy .trivyignore` passed.
- Evidence: no `pip==...` pins were found in managed dev/test/lock/constraint
  surfaces.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
  - Warning observed: ambient `PULSEPLATE_PYTHON_INDEX_URL` is not the
    canonical private proxy root; proxy checks supplied the canonical URL
    inline.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_python_dependency_surfaces.py`
- PASS: `python3 verify_requirements.py`
- PASS: canonical private proxy health for `coverage`, `faker`, and
  `hypothesis` on Python 3.11, 3.12, and 3.13 using
  `https://packages.pulseplate.app/root/pulseplate/+simple/`.
- PASS: focused pytest for dependency security guard and test-profile split
  coverage.
- PASS: isolated temp-venv locked install/import smoke through the canonical
  private proxy:
  `isolated_dependency_import_smoke ok 7.15.0 40.28.1 6.156.1`.
- PASS: `make validate-changed`
  - Note: no-op selector for this dependency metadata diff.
- PASS: `pre-commit run --all-files`
- PASS: commit hook and pre-push hooks during `git commit` / `git push`,
  including backend changed-file tests, pre-push backend tests, pip-audit, and
  full-repo Bandit.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/pr2077-testing-deps-controlled.json`
- Packet id: `f819dacbd771`
- Bootstrap:
  `python3 scripts/orchestration/task_bootstrap.py --goal "Replace Dependabot
  PR #2077 testing dependency group with a current-main controlled lane; keep
  pyarrow PR #2078 separate; do not accept broad lock churn or pip unsafe pin
  changes." --task-class Dependency --path requirements-dev.in --path
  requirements-dev.txt --path requirements-test.in --path requirements-test.txt
  --path requirements-lock.txt --path constraints.txt --path requirements-all.txt
  --path tests/test_python_supply_chain_controls.py --requested-agent
  agent-coordinator --requested-agent qa-engineer-agent --requested-agent
  bug-hunter --requested-agent security-auditor --requested-agent
  cursor-specialist-agent --requested-agent architecture-specialist --pr-phase
  post_open_review`
- Role order completed:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor ->
  cursor-specialist-agent -> architecture-specialist`
- Codex Security / Trivy scans: not run for this continuation because the
  operator explicitly requested no more scans.

## Follow-ups

- Close Dependabot PR #2077 as superseded by PR #2083 after this PR evidence is
  published.
- Keep generated broad lock refreshes out of this lane unless a separate PR
  explicitly owns unsafe-package policy handling.
