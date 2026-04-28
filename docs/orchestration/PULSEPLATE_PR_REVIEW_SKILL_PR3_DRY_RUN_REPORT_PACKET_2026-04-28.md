# PulsePlate PR Review Skill PR3 Dry-Run Report Packet

## Purpose

Implement PR3 for `pulseplate-pr-review`: a side-effect-free dry-run report runner
that consumes `scripts/orchestration/pr_review_context.py` JSON and emits stable
Markdown or JSON review reports.

## Scope

### IN

- Add `scripts/orchestration/pr_review_report.py`.
- Render `dry-run-report` output in Markdown and JSON.
- Preserve coordinator-first role order:
  `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> data-scientist-agent`.
- Update the skill documentation and discovery mirror.
- Close out the merged PR2 collector ledger item for PR #1539.

### OUT

- GitHub review comment posting.
- PR thread resolution.
- Merge automation or merge-readiness claims.
- Runtime dependency on Browser Use, Computer Use, Expo, Hugging Face, Life Science Research, CodeRabbit, Sourcery, or Cubic.

## Role Order

1. `agent-coordinator`
2. `architecture-specialist`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`
6. `data-scientist-agent`

## Validation Plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/sync_skill_mirror.py --name pulseplate-pr-review --force`
- `python3 -m pytest tests/test_pr_review_context.py tests/test_pr_review_report.py tests/test_sync_skill_mirror.py tests/test_install_codex_skills.py -q`
- `pre-commit run --all-files`
- `make validate-min`
- `make validate-changed` if touched scope widens

## Decision Log

- The runner is advisory only and mutates nothing unless `--output` is explicitly
  used to write the generated report.
- Report output does not replace fixed-mapping governance, CodeRabbit/Sourcery/Cubic
  review signals, `make verify`, or `check_merge_ready.py`.
- Plugin evidence channels remain optional and documented; no external plugin is a
  hard runtime dependency for ordinary PR review.
