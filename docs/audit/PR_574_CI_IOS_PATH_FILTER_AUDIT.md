# PR-574 — CI hardening: iOS path-filter (P1 foundation)

## Scope
- CI-only change.
- Touch files:
  - `.github/workflows/ci.yml`
  - `docs/audit/PR_574_CI_IOS_PATH_FILTER_AUDIT.md`
- No runtime/product changes (`app/`, `core/`, `ios/` sources unchanged).
- No new quality gates / thresholds / refactors-for-beauty.

## Problem
The iOS job (`ios-tests`) runs on PRs even when changes are docs-only or backend-only, creating CI noise
and exposing the PR pipeline to unrelated iOS flakiness.

## Audit (facts before change)
- iOS unit tests run as a job inside `.github/workflows/ci.yml` (`ios-tests`, macos-15).
- The workflow triggers on `pull_request` and `push` to `main` / `feat/**` / `fix/**`.
- iOS job should still run when:
  - `ios/**` changes (obvious iOS impact)
  - CI workflow changes that can affect iOS execution (e.g., `.github/workflows/**`, `.github/actions/**`)

## Proposal
Add a minimal, job-level path filter:
- Add a small `changes` job using `dorny/paths-filter`.
- Gate `ios-tests` behind `needs.changes.outputs.ios == 'true'`.

This avoids altering workflow-level triggers (which would risk skipping non-iOS CI jobs).

## DoD
- On docs-only PRs (e.g., `docs/**`, `AGENTS.md`, `.cursor/agents/**`), iOS job does **not** run.
- On PRs touching `ios/**` or CI workflow/actions paths, iOS job **does** run.
- `pre-commit run --all-files` passes locally.
