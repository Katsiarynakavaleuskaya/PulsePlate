# PulsePlate PR Review Skill PR4 Calibration Packet

## Purpose

Calibrate the `pulseplate-pr-review` dry-run report runner before any future
GitHub posting path. PR4 adds a deterministic false-positive rubric and fixture
coverage while keeping the runner advisory and side-effect free.

## Scope

### IN

- Close the merged PR3 ledger item for PR #1558.
- Add PR4 calibration metadata to `scripts/orchestration/pr_review_report.py`.
- Add deterministic tests for clean context, governance findings,
  warning-bearing context, benign fixed-mapping patterns, and large diff risk.
- Update the skill documentation and discovery mirror.

### OUT

- GitHub review comment posting.
- PR thread resolution.
- Auto-merge or merge-readiness claims.
- Runtime dependency on Browser Use, Computer Use, Expo, Hugging Face, Life
  Science Research, CodeRabbit, Sourcery, or Cubic.
- LLM scoring, model calls, or automatic disposition decisions.

## Role Order

1. `agent-coordinator`
2. `architecture-specialist`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`
6. `data-scientist-agent`

## Required Skills

- `pulseplate-workflow`
- `pulseplate-gates`
- `pulseplate-guards`
- `pulseplate-ledger`
- `pulseplate-pr-review`
- `bug-triage`
- `agents-md`
- `code-review-expert`

## Calibration Contract

- Clean context with PR metadata, fixed mapping, scoped `AGENTS.md`, no warnings,
  and a small diff must produce zero findings.
- Missing or malformed fixed mapping remains a governance finding owned by
  `qa-engineer-agent`.
- Context warnings remain `NEEDS-HUMAN` advisory findings and are not eligible
  for automatic posting.
- Large diff risk remains a review-planning signal owned by `bug-hunter`, not a
  merge-readiness claim.
- `NOT-A-BUG` fixed-mapping patterns must not create findings when the rest of
  the context is complete.

## Validation Plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/sync_skill_mirror.py --name pulseplate-pr-review --force`
- `python3 -m pytest tests/test_pr_review_context.py tests/test_pr_review_report.py tests/test_install_codex_skills.py -q`
- `pre-commit run --all-files`
- `make validate-min`
- `make validate-changed`

## Decision Log

- PR4 calibrates report quality before any future dry-run-to-comment path.
- The calibration metadata is advisory; it does not make posting eligible.
- External reviewer tools remain governance signals, not runtime dependencies.
