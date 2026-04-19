# UI Epic PR-1 Bootstrap Packet

**Version:** 2026-04-18 (`America/New_York`)
**Branch:** `codex/ui-epic-runbook-bootstrap`
**PR:** `#1463`
**Title:** `docs(ui-ux): add post-bridge UI epic runbook and lane packet`

## Summary

This packet is the branch-scoped field contract for the first PR in the
post-bridge UI epic line.

The merged bridge baseline already exists on `main` through PR `#1386` and
PR `#1391`. This PR does not reopen that work. It bootstraps the follow-on UI
lane by adding the governing runbook and the explicit backlog anchor that the
next executable slices will reference.

Evidence:
- `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md:44-72`
- `docs/roadmap/BACKLOG_LEDGER.md:860-876`
- `docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md:14-23`

## Scope

### IN
- add the post-bridge UI epic series runbook
- add one explicit backlog anchor for the post-bridge UI line
- lock PR order, role order, worktree isolation, and evidence rules for the
  UI series
- keep the packet minimal and process-level for PR-1 only

### OUT
- runtime, API, OpenAPI, or client behavior changes
- reopening the merged design-bridge parity lane
- billing, entitlement, provider modernization, pricing, or deploy/runtime
  infrastructure changes
- implementation work for PR-2 through PR-5

## Files

- `docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/UI_EPIC_PR1_BOOTSTRAP_PACKET_2026-04-18.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_1463_FIXED_MAPPING.md`

## Role Order

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `cursor-specialist-agent`
5. optional `architecture-specialist`
6. post-open mandatory `qa-engineer-agent -> bug-hunter`

This order is fixed for the lane unless a later packet explicitly updates it.

## Evidence Rules

- Web review is Storybook-first for later web slices.
- iOS evidence is simulator-first for later iOS slices.
- This PR is docs-only, so evidence is repo-artifact validation plus current-head
  PR governance checks.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1463 --body "$(gh pr view 1463 --json body -q .body)"`
- `make verify` remains required before merge-readiness claims on the latest
  head, even though it is environment-heavy for this docs-only slice

## DoD

- the runbook exists and is consistent with merged bridge baseline state
  (`docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md:1-241`;
  `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md:44-72`;
  `docs/roadmap/BACKLOG_LEDGER.md:860-876`)
- PR-1 has a real branch-scoped packet file, not only a runbook
  (`docs/orchestration/UI_EPIC_PR1_BOOTSTRAP_PACKET_2026-04-18.md:1-66`)
- the runbook no longer implies the whole series runs from the PR-1 worktree
  (`docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md:4-7`;
  `docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md:95-149`)
- the backlog anchor points to PR `#1463` instead of a placeholder
  (`docs/roadmap/BACKLOG_LEDGER.md:900-939`)
- the canonical review artifact for PR `#1463` is parser-valid
  (`docs/review/PR_1463_FIXED_MAPPING.md:1-19`;
  `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-125`;
  `scripts/orchestration/check_merge_ready.py:20-24`)
- no runtime or client behavior changes are introduced
