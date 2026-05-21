# PR #1788 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`;
`docs/orchestration/AGENTS.md`.

- [x] Artifact created after PR open
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1788#pullrequestreview-4338682892 -> 4736bd3bf
  - Disposition: FIXED
  - Commit: `4736bd3bf`
  - Evidence: `tests/test_install_locked_python_requirements.py` derives
    protobuf and wrapt wheel expectations from the active emergency manifest
    instead of duplicating filename, URL, or SHA256 literals.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1788#discussion_r3282690538 -> 4736bd3bf
  - Disposition: FIXED
  - Commit: `4736bd3bf`
  - Evidence: `test_repo_ci_lite_main_mirror_lag_emergency_wheels_are_selected`
    now compares staged downloads to the manifest-derived expected artifact set
    and asserts no unexpected emergency wheels are staged.

## Lane Start Provenance

Packet: artifacts/orchestration/task_packets/2f85f57b503f.json
Starter: scripts/orchestration/start_pr_lane.sh

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/exp-3322b408477f.json

The oracle-only result was accepted with `mutated_paths: []`,
`promotion_ready: false`, and `coauthor_required: true`. It shaped the exact
fallback choice and validation plan, so commit `749560148` includes
`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1788#pullrequestreview-4338682892 -> 4736bd3bf
  - Disposition: FIXED
  - Commit: `4736bd3bf`
  - Evidence: `tests/test_install_locked_python_requirements.py` derives
    protobuf and wrapt wheel expectations from the active emergency manifest
    instead of duplicating filename, URL, or SHA256 literals.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1788#discussion_r3282690538 -> 4736bd3bf
  - Disposition: FIXED
  - Commit: `4736bd3bf`
  - Evidence: `test_repo_ci_lite_main_mirror_lag_emergency_wheels_are_selected`
    now compares staged downloads to the manifest-derived expected artifact set
    and asserts no unexpected emergency wheels are staged.

## Pre-Open Role-Agent Findings

- agent-coordinator finding: this lane must remain a narrow supply-chain CI
  hotfix and must not loosen private-index, workflow, or dependency-pin policy.
  - Disposition: FIXED
  - Commit: `749560148`
  - Evidence: `scripts/ci/emergency_python_wheels.json` adds exact,
    time-boxed, SHA256-pinned `protobuf 6.33.5` and `wrapt 2.0.1` entries only;
    no requirements files or workflows were changed.
- architecture-specialist finding: the existing installer architecture already
  owns exact emergency fallback selection, so a broader installer/workflow
  rewrite is unnecessary.
  - Disposition: NOT-A-BUG
  - Evidence: `scripts/ci/install_locked_python_requirements.py` already
    selects active emergency artifacts from exact requirement pins and retries
    direct-proxy installs with a staged local wheelhouse.
- security-auditor finding: new fallbacks must be HTTPS-only, host-allowlisted,
  SHA256-pinned, and must not become a generic public-index bypass.
  - Disposition: FIXED
  - Commit: `749560148`
  - Evidence: `scripts/ci/emergency_python_wheels.json` uses
    `files.pythonhosted.org` URLs and pinned SHA256 digests; installer
    validation still rejects non-approved hosts and mismatched hashes.
- qa-engineer-agent finding: branch validation was stale after `origin/main`
  advanced by one commit.
  - Disposition: FIXED
  - Commit: `749560148`
  - Evidence: branch was fast-forwarded to `origin/main` commit `18be0c53`
    before final gates; `git rev-list --left-right --count origin/main...HEAD`
    returned `0 1` before push.
- bug-hunter finding: manifest-selection tests alone could miss a regression in
  the CI direct-proxy retry path.
  - Disposition: FIXED
  - Commit: `749560148`
  - Evidence: `tests/test_install_locked_python_requirements.py` adds
    `test_repo_ci_lite_direct_proxy_retry_stages_protobuf_then_wrapt`, which
    drives `install_from_proxy_with_emergency_fallback(...)` through the
    protobuf resolver miss, staged `--find-links` retry, wrapt resolver miss,
    and second staged retry.
- Experiment Runner finding: oracle-only review materially shaped validation and
  commit attribution.
  - Disposition: FIXED
  - Commit: `749560148`
  - Evidence: local artifact
    `artifacts/orchestration/experiments/results/exp-3322b408477f.json`
    recorded `oracle_only_governance_reviewer`, `mutated_paths: []`,
    `promotion_ready: false`, and `coauthor_required: true`; commit
    `749560148` includes the canonical Experiment Runner co-author trailer.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path scripts/ci/emergency_python_wheels.json --path tests/test_install_locked_python_requirements.py --path docs/roadmap/BACKLOG_LEDGER.md` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py -q` - PASS
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest tests/test_install_locked_python_requirements.py::test_repo_ci_lite_main_mirror_lag_emergency_wheels_are_selected tests/test_install_locked_python_requirements.py::test_repo_ci_lite_direct_proxy_retry_stages_protobuf_then_wrapt -q` - PASS
- `python3 scripts/orchestration/check_experiment_runner_identity.py` - PASS
- `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` - PASS
- `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH VIRTUAL_ENV=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv pre-commit run --all-files` - PASS
- `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH git push -u origin codex/main-ci-protobuf-private-index-hotfix` - PASS pre-push hooks

Full local `make verify` is deferred under the operator-approved
machine-heavy CI/tooling exception. Current-head GitHub CI parity is required
before merge readiness.

## Merge Readiness

- [ ] PR body includes `## Discussion Thread Pass`, `### Fixed in Commit Mapping`, `## Merge Readiness`
- [ ] Fixed mapping artifact exists and mirrors review dispositions
- [ ] Current-head CI is terminal green for required/touched lanes
- [ ] CodeRabbit, Sourcery, Cubic, and other bot comments have no actionables
- [ ] Strict merge wrapper passes
- [ ] Mandatory wait-window completed after latest review/bot activity
