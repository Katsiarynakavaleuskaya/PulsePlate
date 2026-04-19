# Dependabot PR #1471 Testing Group Remediation Packet

## Goal

Bring PR `#1471` (`deps(deps): bump the testing group with 2 updates`) to
current-head merge readiness under coordinator-owned orchestration without
reopening adjacent Dependabot lanes or the paused epic line.

## Current Truth

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1471>
- PR head branch: `dependabot/pip/testing-9f089b340e`
- Active remediation branch: `codex/pr1471-testing-train`
- Real current-head blockers:
  - `test-pr (3.13)` fails because the locked test install cannot resolve
    `faker==40.15.0` from the approved private index / emergency wheel path.
  - `build` fails because the PR head introduces unrelated runtime churn and the
    Docker locked install now requires `cuda-pathfinder==1.5.3`, which is not
    available on the approved private index.
- Governance-only failures (`PR Body Phase2 gates`, `Merge readiness gate`) are
  expected until the canonical artifact and PR body mirror are established.

## Mandatory Role Order

1. `agent-coordinator`
2. `security-auditor`
3. `backend-engineer`
4. `architecture-specialist` only on explicit coordinator escalation if the
   remediation collides with repo dependency / lock policy
5. `qa-engineer-agent`
6. `bug-hunter`
7. `agent-coordinator`

Rules:

- This role order is mandatory for the lane.
- The canonical post-open review pass remains
  `qa-engineer-agent -> bug-hunter`.
- No ad hoc parallel role stack may replace this order.
- `dev-operator` may assist with command execution and evidence gathering only;
  it does not replace any reviewer in the order above.

## Scope Lock

### In Scope

- Narrow remediation for `faker 40.13.0 -> 40.15.0` and
  `hypothesis 6.151.12 -> 6.152.1`
- Refreshing the PR head onto current repo truth to eliminate unrelated
  runtime / CUDA lock churn
- Updating only the dependency and fallback surfaces required to clear the two
  real current-head blockers
- Creating and maintaining the canonical governance artifact
  `docs/review/PR_1471_FIXED_MAPPING.md`
- Synchronizing the PR body mirror after the canonical artifact is correct

### Out of Scope

- PRs `#1472`, `#1473`, or `#1474`
- Epic-line work
- Broad runtime or CUDA dependency changes not strictly required for `#1471`
- Ledger cleanup beyond documenting a truly unavoidable defer
- Frontend, iOS, API, OpenAPI, or unrelated infra work

## Expected Touched Surfaces

- `requirements-dev.in`
- `requirements-dev.txt`
- `requirements-test.in`
- `requirements-test.txt`
- `requirements-lock.txt`
- `requirements.txt` only to restore current repo truth and remove unrelated
  runtime churn from the PR head
- `scripts/ci/emergency_python_wheels.json` only if it is required to restore
  deterministic install paths for `faker` / `hypothesis`
- `docs/review/PR_1471_FIXED_MAPPING.md`

## Acceptance Criteria

- The unrelated runtime / CUDA churn is removed from the PR diff
- `test-pr (3.13)` is green on the latest PR head
- `build` is green on the latest PR head
- All required checks are green with no pending required jobs on the latest PR
  head
- The post-open `qa-engineer-agent -> bug-hunter` review pass is complete
- All actionable review and bot comments are dispositioned and recorded in
  `docs/review/PR_1471_FIXED_MAPPING.md`
- The PR body mirror matches the canonical artifact
- `make verify` is green before any merge-ready claim

## Coordinator Decisions

- `architecture-specialist` is not required for the current remediation slice.
  The active fix stays within the established dependency / lock policy
  precedent from `PR #1396`: restore widened runtime surfaces to
  `origin/main` truth, then keep only the narrow `faker` / `hypothesis` bump
  and the exact emergency wheel fallback updates required by latest-head CI.
- `.secrets.baseline` is treated as generated pre-commit metadata only. For
  this lane it is restored to `origin/main` first, then minimally synchronized
  for the two updated `emergency_python_wheels.json` digests so that
  `detect-secrets` stays green without reintroducing stale branch drift.

## Local Evidence To Date

- `python3 scripts/orchestration/check_preflight.py` passed in the dedicated
  `#1471` worktree before any edits.
- `python3 scripts/orchestration/check_agent_consistency.py` passed in the
  dedicated `#1471` worktree before any edits.
- `git diff origin/main -- requirements-dev.in requirements-dev.txt
  requirements-test.in requirements-test.txt requirements-lock.txt
  scripts/ci/emergency_python_wheels.json` confirms the narrowed delta is
  limited to `faker 40.15.0` and `hypothesis 6.152.1`.
- `git diff origin/main -- requirements.txt` confirms the unrelated runtime /
  CUDA churn was removed from the working remediation head.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only
  --requirements-profile ci-test --python-executable python3
  --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json` passed
  against the approved private index / fallback path.
- `pre-commit run --files requirements-dev.in requirements-dev.txt
  requirements-test.in requirements-test.txt requirements-lock.txt
  requirements.txt scripts/ci/emergency_python_wheels.json
  docs/orchestration/DEPENDABOT_PR_1471_TESTING_GROUP_REMEDIATION_PACKET_2026-04-19.md
  docs/review/PR_1471_FIXED_MAPPING.md .secrets.baseline` passed after the
  minimal `.secrets.baseline` sync.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python
  -m pytest -q tests/test_install_locked_python_requirements.py
  tests/test_python_supply_chain_controls.py` passed.
- `make validate-min` passed in the dedicated worktree via the local `.venv`
  symlink that points to the root repo virtual environment and remains
  untracked.

## Validation Baseline

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pre-commit run --all-files
make verify
```

## Stop Conditions

- Refresh onto `origin/main` does not remove the unrelated runtime / CUDA churn
- The emergency wheel manifest proves to be a blocker but fixing it would widen
  scope beyond the testing-bump lane
- Any new required check stays red or pending on the latest PR head
- Any actionable review thread or bot comment remains unresolved / unmapped
- The remediation starts touching `#1472-#1474` surfaces or reopens the epic
  line before `#1471` is merged, synced, and cleaned up
