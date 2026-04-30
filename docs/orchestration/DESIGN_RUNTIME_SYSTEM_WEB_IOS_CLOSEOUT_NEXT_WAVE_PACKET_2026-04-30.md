# Design Runtime System Web+iOS Closeout And Next-Wave Packet

- Date: 2026-04-30
- Branch: `codex/design-runtime-train-closeout-next-wave`
- Worktree: `worktrees/design-runtime-train-closeout`
- PR series: Design Runtime System Web+iOS
- Phase: docs/governance closeout after PR-8

## Summary

This docs-only lane closes the completed design runtime system web+iOS train
after PR-8 merged in PR #1606. It reconciles the backlog and runbook so the
repo no longer presents PR-8 as active and does not imply an undocumented PR-9.

The lane does not start a new implementation wave. Any future design runtime
work must begin with a new coordinator packet or runbook update from synced
`origin/main`.

## Coordinator Scope Lock

Role order:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `cursor-specialist-agent`
5. reviewer `architecture-specialist`
6. mandatory post-open `qa-engineer-agent -> bug-hunter`

In scope:

- Mark PR-8 / PR #1606 as merged in the backlog ledger.
- Record the PR-0 through PR-8 train as complete.
- Add a runbook closeout note that no PR-9 is canonically defined.
- Preserve the existing source-precedence, token, Storybook, and Figma
  read-only governance contracts.

Out of scope:

- Web, iOS, backend, OpenAPI, billing, token generation, Storybook parity
  expansion, Figma writes, design asset export, deploy, App Store, Cloudflare,
  or product-screen migration work.
- Claiming ownership of a new design runtime wave without a fresh packet.
- Changing CI, scripts, tests, runtime configuration, or generated artifacts.

## Skills And Plugins

Required PulsePlate skills:

- `pulseplate-workflow`
- `pulseplate-design-launch-system`
- `pulseplate-gates`
- `pulseplate-guards`
- `pulseplate-ledger`
- `pulseplate-pr-review`

Advisory only if discovery requires it:

- `pulseplate-frontend-ui` for Storybook/review-lane context only.
- `pulseplate-graphmap` for dependency evidence only.

Required external capabilities:

- GitHub for draft PR creation, current-head checks, review threads, and merge
  lifecycle.
- CodeRabbit for post-open review input and disposition lifecycle when
  available.

Read-only provenance only:

- Figma canonical file `2JDwOByQIbcPgp93FDzHii` remains design intent only.

Not used for this closeout:

- Canva, Cloudflare, Netlify, Remotion, LaTeX, Hugging Face, Jam, Life Science,
  Expo, Build iOS Apps, Build macOS Apps, backend/OpenAPI tooling, token
  generation tooling.

## Implementation Plan

1. Update `docs/roadmap/BACKLOG_LEDGER.md`:
   - record PR-8 / PR #1606 as merged
   - mark the design runtime web+iOS PR-0 through PR-8 train complete
   - state that no next implementation PR is active until a new coordinator
     packet opens a next wave
2. Update `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR_SERIES_RUNBOOK.md`
   with a closeout section and next-wave start gate.
3. Keep changes docs-only and limited to Markdown governance artifacts.
4. Open the PR as draft first, then add the canonical
   `docs/review/PR_<N>_FIXED_MAPPING.md` artifact after the PR number exists.

## Validation

Start gates:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- coordinator bootstrap via `scripts/orchestration/task_bootstrap.py`

Local docs-only gates before push:

- `git diff --name-only origin/main...HEAD | rg -v "\\.md$|README\\.md$|AGENTS\\.md$|RUNBOOK_AGENT\\.md$|DEPLOYMENT\\.md$"`
- `pytest -q tests/test_repo_policy_guards.py`
- `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json`
- `pre-commit run --all-files`

Full local `make verify` is intentionally deferred for this docs/governance
closeout because the operator has repeatedly disallowed machine-heavy full-suite
runs on this design train. The PR body and fixed mapping must record the
deferral and use GitHub current-head CI as the heavy signal before any
merge-ready claim.

## Review Governance

Open the PR as draft first. After the PR number exists:

- create `docs/review/PR_<N>_FIXED_MAPPING.md`
- mirror local gates and the `make verify` deferral in the PR body
- run CodeRabbit/review disposition workflow
- run mandatory `qa-engineer-agent -> bug-hunter`
- mark ready only after strict merge-readiness checks pass, current-head CI is
  green, review actionables are mapped or resolved, and the wait-window is
  observed

## Merge And Cleanup

After merge:

1. checkout root `main`
2. `git fetch --prune origin`
3. `git merge --ff-only origin/main`
4. confirm PR state `MERGED`
5. confirm `HEAD...origin/main = 0 0`
6. remove only this closeout worktree, local branch, and temp artifacts
7. run `git worktree prune`

## Decision Log

- PR #1606 is the final implementation slice currently defined by the
  PR-series runbook.
- The next logical action is closeout reconciliation, not an implementation
  PR-9.
- Any next design wave needs a new coordinator-owned packet before branch or
  implementation work begins.
