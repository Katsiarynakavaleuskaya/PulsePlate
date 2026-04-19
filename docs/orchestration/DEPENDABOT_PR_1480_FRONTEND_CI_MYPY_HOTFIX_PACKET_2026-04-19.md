# Dependabot PR #1480 Frontend CI mypy hotfix packet

## Goal

Bring PR `#1480` (`fix(deps): restore mypy 1.20.0 for frontend CI`) to
current-head merge readiness under coordinator-owned orchestration without
widening beyond the narrow dependency hotfix and its mandatory governance
artifacts.

## Current Truth

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480>
  - Evidence: `docs/review/PR_1480_FIXED_MAPPING.md:58-92`
- PR head branch: `codex/hotfix-mypy-1.20.0-main`
  - Evidence: `docs/review/PR_1480_FIXED_MAPPING.md:58-92`
- Current head SHA before this packet: `2ca096a1354990976f450da9d32d27ea15b11147`
  - Evidence: `docs/review/PR_1480_FIXED_MAPPING.md:58-92`
- Real current-head code blocker:
  - `requirements-dev.in` still used `mypy~=1.20.0`, which permits `1.20.1`
    and can reintroduce the same Frontend CI install failure on the next lock
    refresh.
  - Evidence: `requirements-dev.in:29`; `docs/review/PR_1480_FIXED_MAPPING.md:68-92`
- Real current-head governance blockers:
  - PR is now non-draft, but the canonical artifact
    `docs/review/PR_1480_FIXED_MAPPING.md` still reflects bootstrap state rather
    than the live bot/review surface.
    - Evidence: `docs/review/PR_1480_FIXED_MAPPING.md:16-92`
  - `sourcery-ai`, `cubic-dev-ai`, and Codex posted review feedback after the
    PR left draft; those dispositions are not yet recorded in the canonical
    artifact.
    - Evidence: `docs/review/PR_1480_FIXED_MAPPING.md:16-92`
  - Current-head CI is noisy with superseded cancelled runs; only the latest
    head run may be used for merge truth.
    - Evidence: `docs/review/PR_1480_FIXED_MAPPING.md:58-92`

## Mandatory Role Order

1. `agent-coordinator`
2. `backend-engineer`
3. `security-auditor`
4. `architecture-specialist` only on explicit coordinator escalation if the
   hotfix collides with dependency / lock policy
5. `qa-engineer-agent`
6. `bug-hunter`
7. `agent-coordinator`

Rules:

- This role order is mandatory for the lane.
- `dev-operator` may assist with command execution and evidence gathering only;
  it does not replace any reviewer in the order above.
- The primary CI/CD lane canon remains
  `agent-coordinator -> backend-engineer -> security-auditor`; this packet now
  matches that ordering.
- The canonical post-open review pass remains
  `qa-engineer-agent -> bug-hunter`.

## Scope Lock

### In Scope

- `requirements-dev.in`
- `requirements-dev.txt`
- `requirements-lock.txt`
- `docs/review/PR_1480_FIXED_MAPPING.md`
- PR body mirror for `#1480`
- This packet

### Out of Scope

- Broad dependency policy redesign
- New install-profile or CI topology work
- Adjacent Dependabot lanes
- Runtime, frontend, iOS, OpenAPI, or infra changes unrelated to the mypy hotfix

## Acceptance Criteria

- `requirements-dev.in` blocks the broken `mypy 1.20.1` patch rather than
  merely preferring `1.20.0`
  - Evidence target: `requirements-dev.in:29`
- Generated requirement artifacts remain aligned to `mypy==1.20.0`
  - Evidence target: `requirements-dev.txt:110`; `requirements-lock.txt:227`
- `pre-commit run --all-files` is green on the latest local head
  - Evidence target: `docs/review/PR_1480_FIXED_MAPPING.md:87-92`
- `make verify` is green on the latest local head
  - Evidence target: `docs/review/PR_1480_FIXED_MAPPING.md:87-92`
- All actionable review/bot comments are dispositioned in
  `docs/review/PR_1480_FIXED_MAPPING.md`
  - Evidence target: `docs/review/PR_1480_FIXED_MAPPING.md:16-92`
- PR body mirror matches the canonical artifact
  - Evidence target: `docs/review/PR_1480_FIXED_MAPPING.md:85-92`
- Latest current-head required checks are green with no pending required jobs
  - Evidence target: `docs/review/PR_1480_FIXED_MAPPING.md:39-92`
- CodeRabbit, Sourcery, and Cubic are explicitly pass / no-actionables before
  any merge-ready claim
  - Evidence target: `docs/review/PR_1480_FIXED_MAPPING.md:39-92`

## Validation Baseline

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pre-commit run --all-files
make verify
GH_TOKEN=$(gh auth token) python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1480 --require-auth
GITHUB_TOKEN=$(gh auth token) python3 scripts/ci/check_pr_merge_readiness.py --pr-number 1480 --repo Katsiarynakavaleuskaya/PulsePlate
```

## Stop Conditions

- Any fix widens beyond the exact mypy pin / regenerated requirement artifacts
- Any new required check stays red or pending on the latest PR head
- Any actionable review thread or bot comment remains unresolved or unmapped
- The lane starts changing adjacent Dependabot or CI-policy surfaces instead of
  finishing the narrow hotfix
