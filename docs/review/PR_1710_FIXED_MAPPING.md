<!-- markdownlint-disable MD013 -->
# PR 1710 Fixed In Commit Mapping

## Scope

PR: `docs(orchestration): add design-epic PR prompt protocol v2026-05-08`

Branch: `codex/design-epic-pr-prompt-protocol-v2026-05-08`

This artifact records evidence after fixes or formal decisions. It is not a substitute for fixing real defects.

## Discussion Thread Pass

Pre-open role-agent and premortem review found actionable docs/test issues before PR opening. They were fixed before this mapping file was created.

## Fixed In Commit Mapping

- Pre-open finding: future prompt guard scanned the full backlog ledger and matched unrelated historical `draft PR` text.
  - Disposition: FIXED
  - Commit: `5a3ced20a22bf2757bc525c7e6eb9ec2ecd6dc42`
  - Evidence: `tests/test_design_automation_next_lane_docs.py` now scopes `_future_prompt_corpus()` to the actual future prompt surface.

- Pre-open finding: review-chain guard used brittle exact casing instead of the governing protocol/template wording.
  - Disposition: FIXED
  - Commit: `5a3ced20a22bf2757bc525c7e6eb9ec2ecd6dc42`
  - Evidence: `tests/test_design_automation_next_lane_docs.py` now checks the post-open and post-first-bot-review chain phrases as written in the docs.

- Pre-open finding: generic design PR template gates were weakened by removing `make design-guard` and `make tokens-check`.
  - Disposition: FIXED
  - Commit: `5a3ced20a22bf2757bc525c7e6eb9ec2ecd6dc42`
  - Evidence: `docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md` keeps the generic design gates and points generated future design-epic PR prompts to the narrower protocol bundle.

- Pre-open finding: protocol wording allowed PR body text to supersede coordinator-declared role order.
  - Disposition: FIXED
  - Commit: `5a3ced20a22bf2757bc525c7e6eb9ec2ecd6dc42`
  - Evidence: `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md` now requires coordinator updates to the lane packet or runbook; the PR body may mirror but cannot replace that decision.

- Pre-open finding: workflow generic gates and generated prompt protocol were ambiguous.
  - Disposition: FIXED
  - Commit: `5a3ced20a22bf2757bc525c7e6eb9ec2ecd6dc42`
  - Evidence: `docs/orchestration/DESIGN_AGENT_WORKFLOW.md` separates general merge-readiness evidence from the narrower generated prompt bundle, and `tests/test_design_automation_next_lane_docs.py` asserts that boundary.

- Pre-open finding: copied worktree-local venv setup omitted dependency sync.
  - Disposition: FIXED
  - Commit: `5a3ced20a22bf2757bc525c7e6eb9ec2ecd6dc42`
  - Evidence: `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md` includes startup-only `make venv-sync`.

- Pre-open finding: final validation preflight did not name execute mode.
  - Disposition: FIXED
  - Commit: `5a3ced20a22bf2757bc525c7e6eb9ec2ecd6dc42`
  - Evidence: `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md` requires `check_preflight.py --mode execute --path <path>` for final pre-open validation.

## Premortem Evidence

Premortem mode: `pr-premortem`, pre-open.

Frame: It is six months from now. The design epic failed because future PR prompts skipped coordinator-expanded role order, actual-diff premortem, dependency setup, post-open reviews, or fixed-mapping-after-fix governance.

Decision: proceed with changes. The required changes were applied before PR opening and validated locally.

Pre-merge checklist for this PR:

- Confirm the protocol is framed as design-epic support docs, not a standalone prompt-canon lane.
- Confirm PR #1707 historical next-lane truth remains intact.
- Confirm generated prompt command blocks reject root checkout switching, provisional PR-state wording, full local root verification bundle commands, and stale prompt make targets.
- Confirm generic design workflow gates remain separate from generated prompt protocol commands.
- Confirm mapping remains evidence after fix/decision.
- Confirm no runtime, token, generated mirror, Figma, Canva, Storybook, asset, web, iOS, or backend files are changed.

## Agent Run Summary

Coordinator bootstrap evidence:

- `.venv/bin/python scripts/orchestration/check_preflight.py --path ...` passed with scoped AGENTS resolved.
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py` passed.
- `.venv/bin/python scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open --path ... --requested-agent ...` passed and emitted task packet `fe672e424219`.

Declared pre-open role order:

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `security-auditor`
5. `creative-designer`
6. `qa-engineer-agent`
7. `bug-hunter`

## Security Review

Codex Security plugin diff-scoped review found no reportable runtime candidate. The diff changes docs/tests/governance only and introduces no auth, secret, subprocess, network, CI workflow, suppression, or fail-open runtime path.

## Validation Evidence

- `.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py` passed: 14 passed.
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` passed; command output reported no changed Python files, so targeted pytest is the primary guard evidence for the changed test file.
- `PATH=.venv/bin:$PATH pre-commit run --all-files` passed.
- `.venv/bin/python scripts/orchestration/check_preflight.py --mode execute --primary agent-coordinator --secondary cursor-specialist-agent --reviewer architecture-specialist --path ...` passed after staging.
- Commit and push hooks passed, including pre-push backend tests and full-repo Bandit.

## Merge Readiness

Not claimed. Merge readiness still depends on current-head CI, post-open role passes, post-first-bot-review passes, review dispositions, this mapping artifact, wait-window, and strict merge wrapper.
