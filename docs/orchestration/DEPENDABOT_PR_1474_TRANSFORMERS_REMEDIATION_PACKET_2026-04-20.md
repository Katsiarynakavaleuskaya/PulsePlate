# Dependabot PR #1474 Transformers Remediation Packet

## Goal

Bring PR `#1474` (`deps(deps): bump transformers from 5.5.3 to 5.5.4`)
to current-head merge readiness under coordinator-owned orchestration without
reopening adjacent Dependabot lanes, widening into repo-wide dependency policy
work, or accepting unrelated GPU/CUDA lock churn on the optional RAG vector
profile.

## Current Truth

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1474>
- PR head branch: `dependabot/pip/transformers-5.5.4`
- Replacement remediation branch:
  `codex/pr1474-transformers-5.5.4-replacement`
- Replacement remediation worktree:
  `/Users/katsiaryna_kavaleuskaya/.codex/worktrees/pr1474r/BMI-App_2025_clean`
- Real current-head blockers observed on `19 April 2026`:
  - The canonical governance artifacts are missing, so `PR Body Phase2 gates`
    and `Merge readiness gate` fail by design until the packet, fixed mapping,
    and PR body mirror are established.
  - The source Dependabot head updates `requirements-rag-vector.in/.txt`, but
    the generated `requirements-rag-vector.txt` also introduces unrelated
    `cuda-*`, `nvidia-*`, and `triton` churn that widens the lane beyond a
    patch-level `transformers` bump.
  - The active emergency wheel manifest still points at
    `transformers==5.5.3`, so the optional RAG vector install contract would
    drift away from the newly pinned `5.5.4` surface unless the fallback is
    rotated in the same PR.
- Current-head nuance:
  - Canonical CI installs `ci-lite`, not the optional `rag-vector` profile, but
    `requirements-rag-vector.txt` is still part of the security / dependency
    governance surface and must remain internally consistent.
  - The live bot review surface currently includes the invalid Dependabot
    assignee warning plus a cubic no-issues review; both must be dispositioned
    in the replacement PR governance artifact.
  - Runtime / validation checks on the live Dependabot head are green; the
    remaining red checks are governance-only and must stay red until the
    canonical artifact + PR body mirror exist on the replacement lane.
  - Post-open current-head CI for replacement PR `#1485` exposed an inherited
    mainline blocker alongside the narrow transformers lane: `build-and-test`
    fails during locked backend dependency install because
    `requirements-dev.txt` pins `ruff==0.15.11` while the approved index lacks
    a matching distribution for the CI environment. On `20 April 2026`, the
    user explicitly approved fixing this blocker inside the replacement PR as a
    narrow manifest/test/docs follow-up instead of widening into a broader
    dependency-policy lane.

## Mandatory Role Order

1. `agent-coordinator`
2. `security-auditor`
3. `backend-engineer`
4. `architecture-specialist` only on explicit coordinator escalation if the
   remediation collides with repo dependency / fallback policy
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

- Narrow remediation for `transformers 5.5.3 -> 5.5.4` on the optional RAG
  vector dependency profile
- Restoring `requirements-rag-vector.txt` to the CPU-neutral baseline already
  proven on `origin/main`, with only the intended `transformers` version bump
  preserved
- Rotating the temporary emergency wheel fallback from
  `transformers==5.5.3` to `transformers==5.5.4`
- Rotating the temporary emergency wheel fallback for `ruff` from `0.15.10` to
  `0.15.11` so the current `requirements-dev.txt` pin remains installable on
  current-head CI while the approved proxy catches up
- Updating the narrow documentation surfaces that explicitly encode the active
  fallback version
- Refreshing `.secrets.baseline` only if `detect-secrets` requires a hashed
  fingerprint update for the new pinned wheel `sha256`
- Creating and maintaining the canonical governance artifact for the
  replacement PR
- Synchronizing the replacement PR body mirror after the canonical artifact is
  correct

### Out of Scope

- Fixing `.github/dependabot.yml` invalid-assignee configuration in this lane
- Repo-wide dependency redesign
- CI-lite / install-profile restructuring beyond the already-established
  optional-rag-vector boundary
- Broad GPU/CUDA enablement policy work
- Frontend, iOS, API, OpenAPI, Cloudflare, Sentry, or unrelated infra work
- Pulling unrelated `origin/main` history into this branch purely for sync
  hygiene; PR current-head checks already evaluate against the live base branch

## Expected Touched Surfaces

- `requirements-rag-vector.in`
- `requirements-rag-vector.txt`
- `scripts/ci/emergency_python_wheels.json`
- `.secrets.baseline` only if required by `detect-secrets` after the wheel
  manifest `sha256` rotation
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/orchestration/DEPENDABOT_PR_1474_TRANSFORMERS_REMEDIATION_PACKET_2026-04-20.md`
- `docs/review/PR_<NEW_PR_NUMBER>_FIXED_MAPPING.md`
- `tests/test_install_locked_python_requirements.py`

## Acceptance Criteria

- `transformers==5.5.4` is the only intended dependency bump in the optional
  RAG vector profile
- `requirements-rag-vector.txt` does not carry unrelated `cuda-*`, `nvidia-*`,
  or `triton` churn from the source Dependabot regeneration
- The emergency wheel fallback now matches `transformers==5.5.4` exactly with
  pinned `sha256` evidence
- No unrelated dependency churn is introduced beyond the patch bump and the
  fallback rotations
- All required checks are green with no pending required jobs on the latest
  replacement PR head
- The post-open `qa-engineer-agent -> bug-hunter` review pass is complete
- All actionable review and bot comments are dispositioned and recorded in the
  replacement PR fixed mapping
- The replacement PR body mirror matches the canonical artifact
- `make verify` is green before any merge-ready claim

## Coordinator Decisions

- `architecture-specialist` is not required at lane entry. The remediation
  stays within established repo precedent from `PR #1400`, `PR #1401`, and
  `PR #1473`: refresh the narrow dependency bump, remove unrelated
  runtime/CUDA lock churn, and rotate the temporary emergency wheel fallback
  while the approved proxy catches up.
- The Dependabot assignee warning on `#1474` is the same repo-wide
  `.github/dependabot.yml` defect already treated as deferred on adjacent
  Dependabot lanes; it remains out of scope for this narrow remediation slice
  and must stay mapped as deferred.
- The Phase 2 discussion/mapping completion checkboxes must remain unchecked
  until the mandatory post-open `qa-engineer-agent -> bug-hunter` lane is
  finished and the final current-head merge-readiness pass is complete.
- Replacement PR strategy is locked: do not merge directly from the Dependabot
  branch.

## Local Evidence To Date

- `origin/main` currently resolves to `bbad8d557`
  (`fix(deps): restore mypy 1.20.0 for frontend CI (#1480)`), and the
  replacement worktree was created directly from that current head.
- `python3 scripts/orchestration/check_preflight.py` passed in the dedicated
  `#1474` replacement worktree before any edits.
- `python3 scripts/orchestration/check_agent_consistency.py` passed in the
  dedicated `#1474` replacement worktree before any edits.
- `gh pr view 1474 --json mergeStateStatus,statusCheckRollup` confirmed the
  live Dependabot head is `UNSTABLE` only because governance checks are red:
  runtime validation (`lint`, `security`, `test-pr (3.13)`, `coverage-pr`,
  `diff-coverage`) is green on the latest head.
- `git diff origin/main...origin/dependabot/pip/transformers-5.5.4 -- requirements-rag-vector.in requirements-rag-vector.txt`
  showed that the source Dependabot head widens the lane with unrelated
  `cuda-*`, `nvidia-*`, and `triton` churn inside
  `requirements-rag-vector.txt`.
- `scripts/ci/emergency_python_wheels.json` still pinned
  `transformers==5.5.3`, so the active fallback contract must rotate together
  with the dependency bump.
- `origin/main` and current `#1485` current-head CI both carry
  `requirements-dev.txt:229` as `ruff==0.15.11` while
  `scripts/ci/emergency_python_wheels.json:107-112` originally still pinned
  `ruff==0.15.10`, so the replacement PR must also rotate the active `ruff`
  fallback to restore locked-install parity on current head.
- PyPI JSON metadata for `transformers==5.5.4` confirmed the canonical wheel
  filename / URL / `sha256` used for the temporary fallback entry:
  - filename: `transformers-5.5.4-py3-none-any.whl`
  - sha256: `0bd6281b82966fe5a7a16f553ea517a9db1dee6284d7cb224dfd88fc0dd1c167`

## Validation Baseline

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pytest -q tests/test_install_locked_python_requirements.py
pytest -q tests/test_python_supply_chain_controls.py
pre-commit run --all-files
make verify
```

## Stop Conditions

- The remediation starts expanding beyond the narrow `transformers` patch bump
  and fallback rotation
- Any fix would require repo-wide dependency policy work instead of applying the
  existing narrow dependency / fallback precedent
- Any new required check stays red or pending on the latest replacement PR head
- Any actionable review thread or bot comment remains unresolved / unmapped
- The remediation starts touching unrelated dependency lanes or reopening
  unrelated epic work before `#1474` is closed
