<!-- markdownlint-disable MD013 -->
# PR 1710 Fixed in Commit Mapping

## Scope

PR: `docs(orchestration): add design-epic PR prompt protocol v2026-05-08`

Branch: `codex/design-epic-pr-prompt-protocol-v2026-05-08`

This artifact records evidence after fixes or formal decisions. It is not a substitute for fixing real defects.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1710#discussion_r3209064923 -> 320e257471ec5af546391bfdd8ad4d507fcbb4d5
Disposition: FIXED
Commit: 320e257471ec5af546391bfdd8ad4d507fcbb4d5
Evidence: `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md` requires execute-mode `check_preflight.py` with `--primary`, `--reviewer`, and scoped `--path`; `tests/test_design_automation_next_lane_docs.py` asserts the command wording.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1710#discussion_r3209085108 -> 320e257471ec5af546391bfdd8ad4d507fcbb4d5
Disposition: FIXED
Commit: 320e257471ec5af546391bfdd8ad4d507fcbb4d5
Evidence: same execute-mode routing fix as above; Cubic marked the finding addressed in commit `320e257`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1710#discussion_r3209166947 -> c9f2427890dc2b3f95b6ddf1b8f5f41b6be252dd
Disposition: FIXED
Commit: c9f2427890dc2b3f95b6ddf1b8f5f41b6be252dd
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` now uses `Target PR: #1710` for the design-epic PR-prompt protocol tracking entry.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1710#pullrequestreview-4252800795 -> c9f2427890dc2b3f95b6ddf1b8f5f41b6be252dd
Disposition: FIXED
Commit: c9f2427890dc2b3f95b6ddf1b8f5f41b6be252dd
Evidence: CodeRabbit review summary reported one actionable ledger finding, mapped above at `discussion_r3209166947` and fixed by the same commit.

## Internal Findings Closed Before Mapping

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

- Post-open finding: external-tool authority wording allowed a coordinator packet alone to grant stronger authority.
  - Disposition: FIXED
  - Commit: `8fb9e62e27f096390aa76f700ecc7aa91ad7a2a1`
  - Evidence: `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md` now requires a separate repo-reviewed contract to promote any narrower authority, and `tests/test_design_automation_next_lane_docs.py` guards against the old wording.

- Post-open finding: final execute-mode preflight command was not copy-paste runnable because it omitted the required routing flags.
  - Disposition: FIXED
  - Commit: `320e257471ec5af546391bfdd8ad4d507fcbb4d5`
  - Evidence: `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md` now requires `--primary`, `--reviewer`, `--path`, and `--secondary` for coordinator-declared secondary agents; `.venv/bin/python scripts/orchestration/check_preflight.py --mode execute --primary agent-coordinator --secondary cursor-specialist-agent --reviewer architecture-specialist --path docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md --path docs/orchestration/DESIGN_AGENT_WORKFLOW.md --path docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md --path tests/test_design_automation_next_lane_docs.py --path docs/roadmap/BACKLOG_LEDGER.md` passed after staging.

- Post-open finding: canonical mapping artifact used an invalid heading and mixed prose bullets inside the parser-owned mapping section.
  - Disposition: FIXED
  - Commit: `320e257471ec5af546391bfdd8ad4d507fcbb4d5`
  - Evidence: this file now uses the exact `## Fixed in Commit Mapping` heading and keeps internal non-GitHub findings outside the parser-owned section.

## Premortem Evidence

Premortem mode: `pr-premortem`, pre-open.

Frame: It is six months from now. The design epic failed because future PR prompts skipped coordinator-expanded role order, actual-diff premortem, dependency setup, post-open reviews, or fixed-mapping-after-fix governance.

Decision: proceed with changes. The required changes were applied before PR opening and validated locally.

Pre-merge checklist for this PR:

- [ ] Confirm the protocol is framed as design-epic support docs, not a standalone prompt-canon lane.
- [ ] Confirm PR #1707 historical next-lane truth remains intact.
- [ ] Confirm generated prompt command blocks reject root checkout switching, provisional PR-state wording, full local root verification bundle commands, and stale prompt make targets.
- [ ] Confirm generic design workflow gates remain separate from generated prompt protocol commands.
- [ ] Confirm mapping remains evidence after fix/decision.
- [ ] Confirm no runtime, token, generated mirror, Figma, Canva, Storybook, asset, web, iOS, or backend files are changed.

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
