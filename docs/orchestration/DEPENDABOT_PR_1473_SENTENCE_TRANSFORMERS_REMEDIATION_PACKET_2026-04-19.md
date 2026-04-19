# Dependabot PR #1473 Sentence-Transformers Remediation Packet

## Goal

Bring PR `#1473` (`deps(deps): bump sentence-transformers from 5.4.0 to 5.4.1`)
to current-head merge readiness under coordinator-owned orchestration without
reopening adjacent Dependabot lanes, widening into repo-wide dependency policy
work, or accepting unrelated GPU/CUDA lock churn on the optional RAG vector
profile.

## Current Truth

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1473>
- PR head branch: `dependabot/pip/sentence-transformers-5.4.1`
- Active remediation branch: `codex/pr1473-dependabot-train`
- Real current-head blockers:
  - The canonical governance artifacts are missing, so `PR Body Phase2 gates`
    and `Merge readiness gate` fail by design until the packet, fixed mapping,
    and PR body mirror are established.
  - The source Dependabot head updates `requirements-rag-vector.in/.txt`, but
    the generated `requirements-rag-vector.txt` also introduces unrelated
    `cuda-*`, `nvidia-*`, and `triton` churn that widens the lane beyond a
    patch-level `sentence-transformers` bump.
  - The active emergency wheel manifest still points at
    `sentence-transformers==5.4.0`, so the optional RAG vector install contract
    would drift away from the newly pinned `5.4.1` surface unless the fallback
    is rotated in the same PR.
- Current-head nuance:
  - Canonical CI installs `ci-lite`, not the optional `rag-vector` profile, but
    `requirements-rag-vector.txt` is still part of the security / dependency
    governance surface and must remain internally consistent.
  - There are no unresolved review threads on the live PR head.
  - The live Dependabot invalid-assignee bot warning is a repo-wide deferred
    config defect, not a lane-local blocker to be fixed inside `#1473`.

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

- Narrow remediation for `sentence-transformers 5.4.0 -> 5.4.1` on the
  optional RAG vector dependency profile
- Restoring `requirements-rag-vector.txt` to the CPU-neutral baseline already
  proven on `origin/main`, with only the intended `sentence-transformers`
  version bump preserved
- Rotating the temporary emergency wheel fallback from
  `sentence-transformers==5.4.0` to `sentence-transformers==5.4.1`
- Updating the narrow test / documentation surfaces that explicitly encode the
  active fallback version
- Creating and maintaining the canonical governance artifact
  `docs/review/PR_1473_FIXED_MAPPING.md`
- Synchronizing the PR body mirror after the canonical artifact is correct

### Out of Scope

- PR `#1474`
- Repo-wide dependency redesign
- CI-lite / install-profile restructuring beyond the already-established
  optional-rag-vector boundary
- Broad GPU/CUDA enablement policy work
- Frontend, iOS, API, OpenAPI, or unrelated infra work

## Expected Touched Surfaces

- `requirements-rag-vector.in`
- `requirements-rag-vector.txt`
- `scripts/ci/emergency_python_wheels.json`
- `tests/test_install_locked_python_requirements.py`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/orchestration/DEPENDABOT_PR_1473_SENTENCE_TRANSFORMERS_REMEDIATION_PACKET_2026-04-19.md`
- `docs/review/PR_1473_FIXED_MAPPING.md`

## Acceptance Criteria

- `sentence-transformers==5.4.1` is the only intended dependency bump in the
  optional RAG vector profile
- `requirements-rag-vector.txt` does not carry unrelated `cuda-*`, `nvidia-*`,
  or `triton` churn from the source Dependabot regeneration
- The emergency wheel fallback now matches
  `sentence-transformers==5.4.1` exactly with pinned `sha256` evidence
- No unrelated dependency churn is introduced beyond the patch bump and the
  fallback rotation
- All required checks are green with no pending required jobs on the latest PR
  head
- The post-open `qa-engineer-agent -> bug-hunter` review pass is complete
- All actionable review and bot comments are dispositioned and recorded in
  `docs/review/PR_1473_FIXED_MAPPING.md`
- The PR body mirror matches the canonical artifact
- `make verify` is green before any merge-ready claim

## Coordinator Decisions

- `architecture-specialist` is not required at lane entry. The remediation
  stays within established repo precedent from `PR #1400` and `PR #1401`:
  refresh the narrow dependency bump, remove unrelated runtime/CUDA lock churn,
  and rotate the temporary emergency wheel fallback while the approved proxy
  catches up.
- The Dependabot assignee warning on `#1473` is the same repo-wide
  `.github/dependabot.yml` defect already deferred from `#1471` and `#1472`;
  it remains out of scope for this narrow remediation slice and must stay
  mapped as deferred.
- The Phase 2 discussion/mapping completion checkboxes must remain unchecked
  until the mandatory post-open `qa-engineer-agent -> bug-hunter` lane is
  finished and the final current-head merge-readiness pass is complete.

## Local Evidence To Date

- `python3 scripts/orchestration/check_preflight.py` passed in the dedicated
  `#1473` worktree before any edits.
- `python3 scripts/orchestration/check_agent_consistency.py` passed in the
  dedicated `#1473` worktree before any edits.
- `gh pr view 1473 --json headRefOid,mergeStateStatus` confirmed the dedicated
  remediation worktree is aligned to the live PR head before edits.
- `gh api graphql` for `reviewThreads` confirmed there are zero unresolved
  review threads on the current PR head.
- `git diff origin/main...origin/dependabot/pip/sentence-transformers-5.4.1 -- requirements-rag-vector.in requirements-rag-vector.txt`
  showed that the source Dependabot head widens the lane with unrelated
  `cuda-*`, `nvidia-*`, and `triton` churn inside
  `requirements-rag-vector.txt`.
- `scripts/ci/emergency_python_wheels.json` still pins
  `sentence-transformers==5.4.0`, so the active fallback contract must rotate
  together with the dependency bump.
- PyPI JSON metadata for `sentence-transformers==5.4.1` confirms the canonical
  wheel filename / URL / `sha256` used for the temporary fallback entry.

## Validation Baseline

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pytest -q tests/test_install_locked_python_requirements.py
pre-commit run --all-files
make verify
```

## Stop Conditions

- The remediation starts expanding beyond the narrow `sentence-transformers`
  patch bump and fallback rotation
- Any fix would require repo-wide dependency policy work instead of applying the
  existing narrow dependency / fallback precedent
- Any new required check stays red or pending on the latest PR head
- Any actionable review thread or bot comment remains unresolved / unmapped
- The remediation starts touching `#1474` surfaces or reopening unrelated epic
  work before `#1473` is closed
