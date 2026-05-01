# PR #1615 Fixed Mapping

## Scope

CI hygiene and coverage PR: Bandit/nosec policy alignment, targeted test and small
production-path fixes, VS Code extension allowlist sync (`sst-dev.opencode`),
and detect-secrets baseline refresh (head `cf5cda5d9`).

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- Status: Bot summaries present on the PR body; no unresolved actionable review
  threads requiring SHA-mapped disposition at artifact publish time. Re-check
  CodeRabbit / Sourcery / Cubic comment threads before merge.

## Fixed in Commit Mapping

- No actionable review comments

## Validation

- Canonical artifact validated via `python3 scripts/ci/check_pr_body_phase2_gates.py`
  after commit (local).

## Merge Readiness

- Required current-head CI must be green before merge.
- `check_merge_ready.py --require-auth` remains operator-gated before merge.
- If actionable bot comments appear, replace the N/A mapping with disposition lines
  and `https://github.com/.../pull/1615#... -> <sha>` entries per `AGENTS.md`.

## Out of Scope

- Coverage threshold changes, workflow weakening, or unrelated product features.
