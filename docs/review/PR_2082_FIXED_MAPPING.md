# PR 2082 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2082

Branch: `codex/deps-pyarrow-24-data-profile`

## Summary

This PR supersedes Dependabot PR #2078 with a current-main, user-owned
data-profile lane. It pins the offline/manual data-build lockfile to
`pyarrow==24.0.0` while preserving the existing `requirements-data.in`
minimum floor `pyarrow>=20.0.0,<25.0.0`.

The replacement is intentionally narrower than #2078: the exact lock pin moves
to 24.0.0, but the policy floor is not raised without separate advisory or
compatibility evidence.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Original Dependabot PR #2078 review state checked: no inline review
  threads and only a non-actionable Codecov report comment.
- [x] Post-open role-order evidence completed before replacement PR open:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor ->
  cursor-specialist-agent -> architecture-specialist`.
- [ ] Current-head GitHub CI and external bot state pending for PR #2082.

## Fixed in Commit Mapping

- No actionable review comments

## Replacement Findings

Disposition: FIXED
Commit: 504dd44b9d915212a42483d347b6d915ed0bd94f
Evidence: `requirements-data.txt` now pins `pyarrow==24.0.0` and keeps the
generated `pip-compile` annotation limited to `requirements-data.in`.
`requirements-data.in` is unchanged, so the supply-chain floor remains
`pyarrow>=20.0.0,<25.0.0`. Focused dependency tests passed:
`.venv/bin/python -m pytest -q tests/test_python_dependency_surfaces.py
tests/test_python_supply_chain_controls.py::test_constraints_keep_dependency_security_floors_aligned
tests/test_python_supply_chain_controls.py::test_eval_and_data_dependency_profiles_are_compiled_and_pinned
tests/test_python_supply_chain_controls.py::test_eval_and_data_dependencies_stay_out_of_default_install_profiles
tests/test_python_supply_chain_controls.py::test_eval_and_data_profiles_do_not_join_shared_install_routing
tests/test_python_supply_chain_controls.py::test_security_scan_workflow_audits_runtime_and_optional_manifests`.
Reason: #2078 raised the `.in` lower bound to `24.0.0`, which made the
focused supply-chain guard fail because the repo treats that lower bound as a
policy floor. The replacement keeps the floor contract intact and updates only
the exact data-profile lock pin.

Disposition: FIXED
Commit: 504dd44b9d915212a42483d347b6d915ed0bd94f
Evidence: PR #2082 was opened from current `main`
`4e59bb927fb5266792d64093bc8bf8783ab405be`, while Dependabot PR #2078 was
still based on stale `main` `632076f92fb85156399124b520ab30c907a83194`.
Reason: The stale Trivy ignore-policy failure on #2078 was old-base evidence,
not a pyarrow diff finding. This replacement takes the refreshed Trivy policy
through current base instead of patching Trivy files in the pyarrow lane.

Disposition: NOT-A-BUG
Evidence: `docs/contracts/PYTHON_DEPENDENCY_SURFACES.md` keeps `pyarrow`
owned by `requirements-data.in` / `requirements-data.txt` and absent from
runtime, Docker runtime, CI-lite, and aggregate lock surfaces. `python3
scripts/ci/check_python_dependency_surfaces.py` and `python3
verify_requirements.py` passed on this branch.
Reason: The lockfile-only diff does not promote `pyarrow` into production
runtime authority or shared install routing.

## Production Premortem

Most likely failure: reviewers mistake the `pyarrow` pin for runtime authority
and miss that it must remain local/manual data-profile only.
Mitigation: the branch changes only `requirements-data.txt`; dependency
surface checks and focused supply-chain tests passed.

Most dangerous failure: the private proxy advertises an unusable or missing
`pyarrow==24.0.0` wheel, so a later data-build job fails after merge.
Mitigation: the canonical private proxy probe found exact `pyarrow==24.0.0`
wheel evidence for Python 3.11, 3.12, and 3.13, and an isolated temp-venv
pandas Parquet smoke passed.

Hidden assumption: a Dependabot major bump should automatically raise the
minimum supported `pyarrow` floor. This PR rejects that assumption; a floor
raise requires a separate policy/compatibility rationale.

Decision: proceed with changes already applied; keep the replacement
lockfile-only and close #2078 as superseded after this PR is published.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/pr2078-pyarrow24-oracle-result-network1.json`

- Result: accepted
- Mode: `oracle_only_governance_reviewer`
- Oracles: `python3 scripts/ci/check_python_dependency_surfaces.py`,
  `python3 verify_requirements.py`, focused dependency/supply-chain pytest, and
  `git diff --check HEAD^..HEAD`
- Shared tree: untouched
- Limitation: the first zero-network packet was rejected because this macOS host
  lacks `unshare`; the accepted fallback used `network_budget=1` with offline
  oracle commands only.
- Attribution: no Experiment Runner co-author trailer is required because the
  runner validated the already-selected lockfile-only decision and did not
  materially shape the implementation commit.

## Implementation Evidence

- Commit: 504dd44b9d915212a42483d347b6d915ed0bd94f
- Evidence: `requirements-data.txt` contains `pyarrow==24.0.0`.
- Evidence: `requirements-data.in` remains unchanged at
  `pyarrow>=20.0.0,<25.0.0`.
- Evidence: `git diff --name-only origin/main...HEAD` contains only
  `requirements-data.txt` before this mapping artifact commit.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
  - Warning observed: ambient `PULSEPLATE_PYTHON_INDEX_URL` is not the
    canonical private proxy root; proxy checks supplied the canonical URL
    inline.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_python_dependency_surfaces.py`
- PASS: `python3 verify_requirements.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_python_dependency_surfaces.py
  tests/test_python_supply_chain_controls.py::test_constraints_keep_dependency_security_floors_aligned
  tests/test_python_supply_chain_controls.py::test_eval_and_data_dependency_profiles_are_compiled_and_pinned
  tests/test_python_supply_chain_controls.py::test_eval_and_data_dependencies_stay_out_of_default_install_profiles
  tests/test_python_supply_chain_controls.py::test_eval_and_data_profiles_do_not_join_shared_install_routing
  tests/test_python_supply_chain_controls.py::test_security_scan_workflow_audits_runtime_and_optional_manifests`
- PASS: `PULSEPLATE_PYTHON_INDEX_URL=https://packages.pulseplate.app/root/pulseplate/+simple/
  python3 scripts/ci/check_private_python_proxy_health.py --requirements-file
  requirements-data.txt --project pyarrow --python-version 3.11
  --python-version 3.12 --python-version 3.13 --max-bytes 3000000`
  - Output: `project name=pyarrow status=200 expected=24.0.0 bytes=373175
    reason=ok`.
- PASS: isolated temp-venv install through
  `scripts/ci/install_locked_python_requirements.py` using
  `requirements-data.txt` and the canonical private proxy, followed by pandas
  `to_parquet` / `read_parquet` smoke.
  - Output: `pyarrow_parquet_smoke ok version=24.0.0 rows=2`.
- PASS: `make validate-changed`
  - Note: no-op selector for this lockfile-only diff.
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks during `git push`.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/pr2078-pyarrow-data-profile.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Bootstrap:
  `python3 scripts/orchestration/task_bootstrap.py --goal "Validate Dependabot
  PR #2078 pyarrow 24.0.0 as an isolated data-profile dependency lane after PR
  #2081 merge; do not mix with testing-deps PR #2077." --task-class Dependency
  --path requirements-data.in --path requirements-data.txt --requested-agent
  agent-coordinator --requested-agent security-auditor --requested-agent
  qa-engineer-agent --requested-agent bug-hunter --pr-phase post_open_review`
- Role order completed:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor ->
  cursor-specialist-agent -> architecture-specialist`
- Codex Security / Trivy scans: not run for this continuation because the
  operator explicitly requested no more scans.

## Follow-ups

- Close Dependabot PR #2078 as superseded by PR #2082.
- Keep Dependabot PR #2077 out of this lane; rebuild it separately if the
  testing-deps update is still desired.
