# Dependabot PR #1520 PostCSS Replacement Packet

## Goal

Create a user-owned replacement PR for Dependabot `#1520` that preserves the
narrow frontend dependency update from `postcss 8.5.8` to `8.5.10` without
editing the Dependabot bot branch or widening into frontend runtime, API,
OpenAPI, iOS, backend, or deployment behavior.

## Current Truth

- Source PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1520>
- Source head branch:
  `dependabot/npm_and_yarn/frontend/npm_and_yarn-754666cf41`
- Replacement branch: `codex/pr1520-postcss-8.5.10-replacement`
- Replacement worktree: `worktrees/pr1520-postcss-8.5.10-replacement`
- Intended dependency delta:
  - `frontend/package.json`: `postcss` spec `^8.4.38` to `^8.5.10`
  - `frontend/package-lock.json`: root `postcss` spec `^8.4.38` to `^8.5.10`
  - `frontend/package-lock.json`: locked `node_modules/postcss` package
    `8.5.8` to `8.5.10`
- Observed source-PR blocker: current-head runtime checks were green for the
  frontend dependency surface, while `PR Body Phase2 gates` and
  `Merge readiness gate` failed because the canonical review mapping artifact
  `docs/review/PR_1523_FIXED_MAPPING.md` was absent.
- Start-gate override: live `main` health was not fully settled when this lane
  started, so the replacement PR must open as draft and must not claim
  merge-readiness until current-head `main` health is rechecked.

## Mandatory Role Order

1. `agent-coordinator`
2. `frontend-engineer`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`
6. `agent-coordinator`

Rules:

- This role order is mandatory for the lane.
- `dev-operator` may assist with command execution and evidence gathering only.
- No ad hoc parallel role stack may replace this order.
- The post-open review pass remains `qa-engineer-agent -> bug-hunter`.

## Scope Lock

### In Scope

- Reproduce the exact Dependabot `postcss 8.5.8 -> 8.5.10` frontend dependency
  update on a user-owned replacement branch.
- Create and maintain the canonical PR fixed-mapping artifact after the
  replacement PR number exists.
- Keep the replacement PR body mirror aligned with the canonical Phase2
  governance headings and checklist labels.
- Disposition source PR `#1520` as superseded by the replacement PR.

### Out of Scope

- Editing the Dependabot bot branch directly.
- Frontend UI, API client, OpenAPI, backend, iOS, deployment, Docker, or
  product behavior changes.
- Broad dependency-governance redesign.
- Any merge-ready claim while current-head `main`, replacement PR CI, review
  threads, bot actionables, or the mandatory wait-window remain unresolved.

## Validation Baseline

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
cd frontend && npm install
cd frontend && npm run build
pre-commit run --all-files
```

Merge-readiness also requires the strict current-head wrapper:

```bash
GH_TOKEN="$(gh auth token)" GITHUB_TOKEN="$(gh auth token)" \
  python3 scripts/orchestration/check_merge_ready.py \
  --pr-number <replacement-pr-number> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --require-auth
```

## Stop Conditions

- The diff expands beyond the three intended `postcss` dependency lines plus
  governance artifacts.
- `npm install` introduces unrelated lockfile churn.
- Current-head `main` remains unstable when moving out of draft.
- Any actionable CodeRabbit, Sourcery, Cubic, or human review item remains
  unmapped or unresolved.
