# Dependabot PR #1472 Quality Group Remediation Packet

## Goal

Bring PR `#1472` (`deps(deps): bump the quality group with 2 updates`) to
current-head merge readiness under coordinator-owned orchestration without
reopening adjacent Dependabot lanes or widening into runtime dependency policy
work beyond the narrow portability fix already established by repo precedent.

## Current Truth

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1472>
- PR head branch: `dependabot/pip/quality-f9441223f4`
- Active remediation branch: `codex/pr1472-quality-train`
- Real current-head blockers:
  - The PR head introduces unconditional `cuda-*`, `nvidia-*`, and `triton`
    pins into `requirements.txt` / `requirements-lock.txt`, making the default
    install path non-portable on macOS.
  - The canonical governance artifacts are missing, so `PR Body Phase2 gates`
    and `Merge readiness gate` fail by design until the packet, fixed mapping,
    and PR body mirror are established.
- Current-head nuance:
  - Latest visible checks already include fresh `build` pass and
    `test-pr (3.13)` pass on the live PR head; older `build` / `test-pr`
    failures are stale historical noise and must not drive remediation scope.

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

- Narrow remediation for `mypy 1.20.0 -> 1.20.1` and `ruff 0.15.10 -> 0.15.11`
- Restoring Linux / `x86_64` platform markers on the CUDA / Triton wheels that
  Dependabot regeneration made unconditional
- Updating only the dependency and governance surfaces required to clear the
  real current-head blockers
- Creating and maintaining the canonical governance artifact
  `docs/review/PR_1472_FIXED_MAPPING.md`
- Synchronizing the PR body mirror after the canonical artifact is correct

### Out of Scope

- PRs `#1473` or `#1474`
- Broad runtime dependency redesign
- CI-lite / install-profile restructuring that belongs to a separate policy lane
- Epic-line work
- Frontend, iOS, API, OpenAPI, or unrelated infra work

## Expected Touched Surfaces

- `requirements-dev.in`
- `requirements-dev.txt`
- `requirements-lock.txt`
- `requirements.txt`
- `docs/orchestration/DEPENDABOT_PR_1472_QUALITY_GROUP_REMEDIATION_PACKET_2026-04-19.md`
- `docs/review/PR_1472_FIXED_MAPPING.md`

## Acceptance Criteria

- `mypy` and `ruff` bumps remain the only intended quality-group updates
- CUDA / Triton wheels are constrained to the established Linux / `x86_64`
  portability boundary in both `requirements.txt` and `requirements-lock.txt`
- No unrelated dependency churn is introduced beyond the quality bump and the
  narrow portability repair
- All required checks are green with no pending required jobs on the latest PR
  head
- The post-open `qa-engineer-agent -> bug-hunter` review pass is complete
- All actionable review and bot comments are dispositioned and recorded in
  `docs/review/PR_1472_FIXED_MAPPING.md`
- The PR body mirror matches the canonical artifact
- `make verify` is green before any merge-ready claim

## Coordinator Decisions

- `architecture-specialist` is not required at lane entry. The active fix stays
  within established repo precedent from `PR #1275` and `PR #1401`: restore
  platform markers for accidental GPU wheel drift without broadening dependency
  policy.
- The Dependabot assignee warning on `#1472` is the same repo-wide
  `.github/dependabot.yml` defect already deferred from `#1471`; it remains
  out of scope for this narrow remediation slice and must stay mapped as
  deferred.
- The Phase 2 discussion/mapping completion checkboxes must remain unchecked
  until the mandatory post-open `qa-engineer-agent -> bug-hunter` lane is
  finished and the final current-head merge-readiness pass is complete.

## Local Evidence To Date

- `python3 scripts/orchestration/check_preflight.py` passed in the dedicated
  `#1472` worktree before any edits.
- `python3 scripts/orchestration/check_agent_consistency.py` passed in the
  dedicated `#1472` worktree before any edits.
- `gh pr view 1472 --json ...` confirms the current PR head SHA is
  `d6405f002bd057e6c0ee88ef7807b61a785a6425`.
- `gh api graphql` for `reviewThreads` confirms an unresolved cubic thread on
  `requirements.txt` identifying unconditional CUDA pins as the live actionable
  review item.
- `git diff origin/main...HEAD -- requirements.txt requirements-lock.txt`
  shows the PR head adds unconditional `cuda-bindings`, `cuda-pathfinder`,
  `nvidia-*`, and `triton` entries beyond the intended `mypy` / `ruff` bump.
- `pre-commit run --all-files` passed after the narrow marker restoration and
  canonical artifact creation.
- `make verify` passed end-to-end in the dedicated `#1472` worktree after
  attaching the local `.venv` symlink to the root repo virtual environment;
  `verify-env`, `lint`, `typecheck`, `test-fast`, and `diff-cov` all completed
  successfully on the remediation head.

## Validation Baseline

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pre-commit run --all-files
make verify
```

## Stop Conditions

- The portability fix starts expanding beyond CUDA / Triton marker restoration
- Any remediation would require changing repo-wide dependency policy rather than
  applying the existing Linux / `x86_64` marker precedent
- Any new required check stays red or pending on the latest PR head
- Any actionable review thread or bot comment remains unresolved / unmapped
- The remediation starts touching `#1473` / `#1474` surfaces or reopens the
  paused epic line before `#1472` is merged, synced, and cleaned up
