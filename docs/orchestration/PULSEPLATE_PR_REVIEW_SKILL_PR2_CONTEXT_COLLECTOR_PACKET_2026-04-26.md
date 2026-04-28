# PulsePlate PR Review Skill PR2 Context Collector Packet

## Purpose

Implement the PR2 slice for `pulseplate-pr-review`: create a read-only review-context
collector and mirror synchronization step for deterministic Codex review runs.

## Scope

### IN

- Add deterministic skill mirror sync step:
  `python3 scripts/orchestration/sync_skill_mirror.py --name pulseplate-pr-review --force`
- Add/extend `scripts/orchestration/pr_review_context.py` as a read-only collector with stable JSON output.
- Add tests for:
  - collector behavior (diff parse, scoped `AGENTS.md` discovery, mapping absence, metadata miss path)
  - `sync_skill_mirror.py` copy/replace path.
- Keep collector as advisory and side-effect free.

### OUT

- Automatic GitHub comment posting.
- PR-thread resolution.
- Merge automation.
- Any change to canonical mapping artifact schema.

## Files

- `scripts/orchestration/sync_skill_mirror.py`
- `scripts/orchestration/pr_review_context.py`
- `tests/test_sync_skill_mirror.py`
- `tests/test_pr_review_context.py`
- `tests/test_install_codex_skills.py`
- `docs/orchestration/PULSEPLATE_PR_REVIEW_SKILL_PR2_CONTEXT_COLLECTOR_PACKET_2026-04-26.md`
- `docs/review/PR_<N>_FIXED_MAPPING.md` after PR number is assigned
- `.agents/skills/pulseplate-pr-review`

## Role Order

1. `agent-coordinator`
2. `architecture-specialist`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`

## Validation Plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/sync_skill_mirror.py --name pulseplate-pr-review --force`
- `python3 -m pytest tests/test_sync_skill_mirror.py tests/test_pr_review_context.py tests/test_install_codex_skills.py -q`
- `make validate-min` (or `make validate-changed` when scope widens)

## Merge Discipline

- Open PR as draft.
- create `docs/review/PR_<N>_FIXED_MAPPING.md` only after PR number is known.
- sync PR-body mirror section after required dispositions are present.
- run mandatory post-open review lane: `qa-engineer-agent -> bug-hunter`.
- finish with `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth` and required current-head checks.
