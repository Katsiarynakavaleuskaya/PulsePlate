# PR #1790 - Fixed in Commit Mapping

## Scope

Experiment Runner Evidence configurable hard-gate mode and repo Python bootstrap
parity for coordinator-owned PR lanes.

## Implementation Commits

- `190577d0e` - `feat(orchestration): gate experiment runner evidence mode`
- `10668b0a` - `fix(orchestration): close evidence mode review findings`
- `b5133c5` - `fix(orchestration): harden bootstrap python parity`
- `b50ab6e` - `docs(review): normalize pr 1790 mapping format`
- `a978b76` - `fix(ci): forward experiment evidence mode directly`
- `9acd01a` - `fix(orchestration): avoid false evidence and startup blocks`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Lane Start Provenance

Packet: artifacts/orchestration/task_packets/dfe90fc15aa0.json
Starter: scripts/orchestration/start_pr_lane.sh

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/evidence-hard-gate-switch.json

Local oracle-only result, gitignored and not committed. Runner mode:
`oracle_only_governance_reviewer`; `mutated_paths: []`; `promotion_ready: false`;
`contribution_kind: commit_decision`; `coauthor_required: true`. Commits
`190577d0e`, `10668b0a`, `b5133c5`, `b50ab6e`, `a978b76`, and `9acd01a`
include the canonical Experiment Runner co-author trailer.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 10668b0a
Evidence: fixed Sourcery evidence-mode parsing and bootstrap Python test coverage findings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#pullrequestreview-4340694578 -> 10668b0a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284313517 -> 10668b0a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284313523 -> 10668b0a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284313533 -> 10668b0a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284339562 -> 10668b0a

Disposition: FIXED
Commit: b5133c5
Evidence: fixed CodeRabbit and Codex bootstrap Python parity findings for parent venv scope, dry-run validation, absolute VENV guidance, and typed test doubles.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#pullrequestreview-4340732615 -> b5133c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284339492 -> b5133c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284339531 -> b5133c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284339552 -> b5133c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#pullrequestreview-4340748415 -> b5133c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284350079 -> b5133c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284350084 -> b5133c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284350085 -> b5133c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284350088 -> b5133c5

Disposition: FIXED
Commit: b50ab6e
Evidence: normalized the canonical mapping artifact into parser-compatible disposition blocks with single-line URL-to-SHA mappings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284439459 -> b50ab6e

Disposition: FIXED
Commit: a978b76
Evidence: forwarded the configured Experiment Runner evidence mode directly into artifact/body evidence validation instead of relying on diagnostic post-processing.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#pullrequestreview-4340867011 -> a978b76

Disposition: FIXED
Commit: 9acd01a
Evidence: fixed Codex review findings by combining body/artifact evidence before required-mode failure and by allowing clean origin/main starts without a local main branch.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#pullrequestreview-4340959547 -> 9acd01a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284523232 -> 9acd01a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1790#discussion_r3284523235 -> 9acd01a

## Pre-Open Role-Agent Findings

- agent-coordinator finding: this lane must remain a narrow governance/tooling
  PR and must not grant Experiment Runner mutation authority to `scripts/ci/**`.
  - Disposition: FIXED
  - Commit: `190577d0e`
  - Evidence: `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md` and
    `docs/roadmap/BACKLOG_LEDGER.md` keep validator-script mutation deferred;
    no Experiment Runner implementation mutation authority was added.
- security-auditor finding: dirty launcher state was initially allowed too
  broadly for fresh `origin/main` lane starts.
  - Disposition: FIXED
  - Commit: `190577d0e`
  - Evidence: `scripts/orchestration/start_pr_lane.sh` requires explicit
    `--allow-dirty-launcher`, only for synced `origin/main` lanes; tests cover
    dirty-without-flag, non-`origin/main`, and unsynced-main failures.
- security-auditor finding: `VENV_PYTHON` initially accepted relative
  executables.
  - Disposition: FIXED
  - Commit: `190577d0e`
  - Evidence: `scripts/orchestration/start_pr_lane.sh` and
    `scripts/orchestration/local_session_bootstrap.sh` require absolute
    executable `VENV_PYTHON`; tests cover relative-path rejection.
- qa-engineer-agent finding: CI/event-path wrapper mode lacked required-mode
  forwarding coverage.
  - Disposition: FIXED
  - Commit: `190577d0e`
  - Evidence: `tests/test_orchestration_merge_ready.py` covers event-path
    required-mode forwarding.
- qa-engineer-agent finding: dirty-launcher exception needed negative coverage.
  - Disposition: FIXED
  - Commit: `190577d0e`
  - Evidence: `tests/test_start_pr_lane.py` covers non-`origin/main` and
    unsynced-main failure cases.
- Experiment Runner finding: oracle-only review materially shaped the hard-gate
  mode rollout and commit decision.
  - Disposition: FIXED
  - Commit: `190577d0e`
  - Evidence: local artifact
    `artifacts/orchestration/experiments/results/evidence-hard-gate-switch.json`
    recorded `mutated_paths: []`, `promotion_ready: false`,
    `contribution_kind: commit_decision`, and `coauthor_required: true`; commit
    `190577d0e` includes
    `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path <changed paths>` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/orchestration/check_experiment_runner_identity.py` - PASS
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_orchestration_merge_ready.py tests/test_start_pr_lane.py tests/test_local_session_bootstrap.py tests/test_pr_body_phase2_gates.py tests/test_render_codex_start_prompt.py tests/test_experiment_runner.py tests/test_experiment_runner_identity_policy.py` - PASS
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python DEV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` - PASS
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python DEV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python pre-commit run --all-files` - PASS
- Pre-push hook - PASS: changed-file mypy, pip-audit, backend pytest,
  full-repo Bandit, docker build test
- GraphMap non-mutating `/tmp` check - PASS:
  `/tmp/pulseplate_graphmap_evidence_hard_gate_switch.json`, sha256
  `a052652f56a63399b32048aea9cbe74d0031c7d12851f9e5649f19073efbb485`

## Deferred / Follow-ups

- Future separate PR: controlled Experiment Runner mutation access to
  `scripts/ci/**` validator scripts remains deferred and threat-model gated.
  Backlog:
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-experiment-runner-validator-mutation-threat-model`

## Merge Readiness

Not claimed. Current-head PR CI, bot review, post-open review-thread
disposition, wait-window, PR body mirror, and strict merge wrapper remain
required before merge readiness.
