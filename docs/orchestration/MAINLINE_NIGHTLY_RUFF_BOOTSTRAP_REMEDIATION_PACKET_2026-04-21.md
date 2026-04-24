# Mainline Nightly Ruff Bootstrap Remediation Packet

## Goal

Bring a new remediation PR to current-head merge readiness under
coordinator-owned orchestration by fixing the live `main` nightly bootstrap
failures caused by `ruff` version drift between the dev requirement sources and
the active emergency wheel fallback contract.

## Current Truth

- Base branch: `main`
- Synced local state at lane start:
  - `git status --short --branch` -> clean
  - `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- Active remediation branch: `codex/fix-main-nightly-ruff-bootstrap`
- Live failures observed on `21 April 2026`:
  - `Nightly Full Tests` run `24704500078`
    (`tests` job `72254565349`) fails in `Install dependencies`
  - `Nightly Tests` run `24704528938`
    (`test (1)` job `72254656999` and sibling shards) fails in
    `Setup Python environment`
- Shared current-head failure signature:
  - locked install reaches `requirements-dev.txt`
  - resolver reports `The user requested ruff==0.15.10`
  - the active emergency wheel manifest already pins `ruff 0.15.11`
- Current-head nuance:
  - canonical PR `CI` on the same `main` head SHA is green; this is a
    nightly/bootstrap regression, not a repo-wide red-main event
  - workflow Python setup is already explicit on the failing lanes, so the
    narrow remediation target is dependency truth, not workflow YAML drift

## Mandatory Role Order

1. `agent-coordinator`
2. `security-auditor`
3. `backend-engineer`
4. `architecture-specialist` only on explicit coordinator escalation if the
   `ruff 0.15.11` alignment collides with the approved private-index fallback
   contract
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

- Narrow remediation for `ruff 0.15.10 -> 0.15.11` on the dev/runtime-dev
  locked install surfaces
- Regenerating only the generated lock surfaces required to keep repo truth
  aligned after the source pin change
- Adding one narrow regression guard that fails when the active `ruff`
  emergency wheel fallback drifts away from the dev requirement source/locks
- Creating and maintaining the canonical governance artifact for the new PR
- Synchronizing the PR body mirror after the canonical artifact is correct

### Out of Scope

- Generic workflow hardening or Python-version policy changes
- Repo-wide dependency redesign
- Broad private-index policy work beyond the already-established emergency
  fallback contract
- Frontend, iOS, API, OpenAPI, Docker, Cloudflare, Sentry, or unrelated infra
  work
- Any change to public product behavior

## Expected Touched Surfaces

- `requirements-dev.in`
- `requirements-dev.txt`
- `requirements-lock.txt`
- `tests/test_install_locked_python_requirements.py`
- `docs/orchestration/MAINLINE_NIGHTLY_RUFF_BOOTSTRAP_REMEDIATION_PACKET_2026-04-21.md`
- `docs/review/PR_<NEW_PR_NUMBER>_FIXED_MAPPING.md`
- `docs/roadmap/BACKLOG_LEDGER.md` only if needed to attach the new PR to the
  existing fallback ledger item

## Acceptance Criteria

- `ruff 0.15.11` is the only intended dependency change in the remediation diff
- `requirements-dev.in`, `requirements-dev.txt`, `requirements-lock.txt`, and
  `scripts/ci/emergency_python_wheels.json` are aligned on the active `ruff`
  version contract
- No unrelated dependency churn is introduced beyond the required lockfile
  regeneration
- Local regression checks for locked install and supply-chain workflow policy
  pass
- `pre-commit run --all-files` passes
- `make verify` passes before any merge-ready claim
- Both nightly workflows advance past the current `ruff` bootstrap failure on
  the remediation branch
- The post-open `qa-engineer-agent -> bug-hunter` review pass is complete
- All actionable review and bot comments are dispositioned and recorded in the
  fixed mapping artifact

## Coordinator Decisions

- Existing backlog truth is sufficient at lane start: the active private-index
  fallback ledger entry already covers `ruff 0.15.11`, so a new broad ledger
  item is not required unless a genuine defer appears during remediation.
- `architecture-specialist` is not required at lane entry. Escalate only if
  `ruff 0.15.11` alignment proves insufficient and a wider policy/design change
  is needed.
- Workflow YAML remains unchanged unless branch validation proves the lock/pin
  alignment alone does not clear the failing bootstrap steps.
- The PR should stay draft until the code change, local validation, and the
  initial governance artifact are ready.

## Validation Baseline

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pytest -q tests/test_install_locked_python_requirements.py
pytest -q tests/test_python_supply_chain_controls.py
pre-commit run --all-files
make verify
python3 scripts/ci/install_locked_python_requirements.py \
  --preflight-only \
  --requirements-profile runtime-dev \
  --python-executable python3 \
  --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json \
  --index-url "$PULSEPLATE_PYTHON_INDEX_URL"
```

## Governance Timing

- Before PR open:
  - create the remediation branch
  - land the narrow dependency/test/packet changes
  - run local validation
- After PR open:
  - create `docs/review/PR_<N>_FIXED_MAPPING.md`
  - mirror the PR body Phase 2 sections from the canonical artifact
  - complete the mandatory post-open review lane
  - run current-head merge-readiness checks only after the latest review/bot
    activity is dispositioned

## Stop Conditions

- The fix starts widening beyond `ruff` version alignment and the associated
  regression guard
- Lock regeneration introduces unrelated dependency churn that cannot be
  explained by the narrow `ruff` bump
- The active private-index fallback contract cannot support `ruff 0.15.11`
  without broader policy work
- Any new required check stays red or pending on the latest PR head
- Any actionable review thread or bot comment remains unresolved / unmapped
