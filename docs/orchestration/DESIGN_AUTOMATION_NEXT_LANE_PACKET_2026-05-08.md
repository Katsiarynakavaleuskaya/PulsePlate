<!-- markdownlint-disable MD013 -->
# Design Automation Next-Lane Packet

## Summary

This packet governs the docs/test-only PR that codifies `PulsePlate Canonical PR Execution Prompt v2026-05-08` after the merged post-PR-8 design automation decision.

- Branch: `codex/canonical-pr-execution-prompt-v2026-05-08`
- Title: `docs(orchestration): codify canonical PR execution prompt v2026-05-08`
- Classification: docs/test-only governance packet
- Canonical name: `PulsePlate Canonical PR Execution Prompt v2026-05-08`

This PR does not implement runtime, token, generated mirror, Figma, Canva, asset, screenshot, Storybook, web, iOS, backend, or selected future design automation work.

## Coordinator Route

Mandatory start gate:

```bash
git status --short
git fetch --prune origin
git rev-list --left-right --count HEAD...origin/main
git worktree add -b codex/canonical-pr-execution-prompt-v2026-05-08 <worktree-path> origin/main
cd <worktree-path>
python3.13 -m venv .venv --copies
git status --short
test -x .venv/bin/python
.venv/bin/python scripts/orchestration/check_preflight.py \
  --path docs/orchestration/PULSEPLATE_CANONICAL_PR_EXECUTION_PROMPT_2026_05_08.md \
  --path docs/orchestration/DESIGN_AUTOMATION_NEXT_LANE_PACKET_2026-05-08.md \
  --path docs/orchestration/DESIGN_AGENT_WORKFLOW.md \
  --path docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md \
  --path docs/roadmap/BACKLOG_LEDGER.md \
  --path tests/test_design_automation_next_lane_docs.py
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python scripts/orchestration/task_bootstrap.py \
  --goal "Codify PulsePlate Canonical PR Execution Prompt v2026-05-08 as a docs/test-only design orchestration governance lane" \
  --task-class "Orchestration" \
  --pr-phase pre_open \
  --path docs/orchestration/PULSEPLATE_CANONICAL_PR_EXECUTION_PROMPT_2026_05_08.md \
  --path docs/orchestration/DESIGN_AUTOMATION_NEXT_LANE_PACKET_2026-05-08.md \
  --path docs/orchestration/DESIGN_AGENT_WORKFLOW.md \
  --path docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md \
  --path docs/roadmap/BACKLOG_LEDGER.md \
  --path tests/test_design_automation_next_lane_docs.py \
  --requested-agent agent-coordinator \
  --requested-agent cursor-specialist-agent \
  --requested-agent architecture-specialist \
  --requested-agent security-auditor \
  --requested-agent creative-designer \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter
```

Role order:

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `security-auditor`
5. `creative-designer`
6. `qa-engineer-agent`
7. `bug-hunter`

Post-open review repeats the route with `--pr-phase post_open_review`, then runs a second pass after bot comments and a final regression pass before merge readiness.

Prompt wording is governed by `docs/orchestration/PULSEPLATE_CANONICAL_PR_EXECUTION_PROMPT_2026_05_08.md`. Post-merge local main synchronization is operator-owned and must not be printed as a generated agent PR prompt.

## Source Precedence

Canonical:

1. Repo code/docs/tests.
2. `/tokens` as token authoring truth.
3. Generated mirrors as derived artifacts.
4. UI vocabulary and component contracts.
5. Backend/OpenAPI contracts and runtime code.

Non-canonical evidence/reference/process layers:

- DESIGN.md.
- Design decision packets.
- Research docs.
- Figma.
- Canva.
- Storybook.
- Evidence packs.
- Scorecards.
- Templates.
- Prompt outputs.

This packet must not create a second source of truth.

## Touched Paths

Expected:

- `docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md`
- `docs/orchestration/DESIGN_AUTOMATION_NEXT_LANE_PACKET_2026-05-08.md`
- `tests/test_design_automation_next_lane_docs.py`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_<N>_FIXED_MAPPING.md` after PR number exists

Forbidden:

- `frontend/`
- `ios/`
- `app/`
- `core/`
- `tokens/`
- generated token mirrors
- Storybook config
- Figma writes
- Canva writes
- screenshots, videos, traces, binary assets

## Required Skills And Review Inputs

Use as advisory helpers only:

- `pulseplate-design-launch-system`
- `pulseplate-pr-review`
- `pulseplate-premortem-risk-review`
- Chronicle for prior PR body and mapping patterns
- GitHub / CodeRabbit for PR truth and review comments
- Codex Security for diff-scoped security wording review

Do not use these helpers as substitutes for root `AGENTS.md`, scoped `AGENTS.md`, `RUNBOOK_AGENT.md`, `check_preflight.py`, `check_agent_consistency.py`, `task_bootstrap.py`, fixed mapping, or strict merge readiness.

## Premortem Checklist

Premortem must inspect the actual docs/test diff. Real findings must be fixed in docs/tests before mapping.

Check:

- Did the PR accidentally create an automatic undocumented PR-9 implementation scope?
- Did the decision packet create a second source of truth?
- Did it allow Figma, Canva, Storybook, research, scorecards, or prompt outputs to override repo truth?
- Did it forget `.venv/bin/python` policy?
- Did it add tracked symlink or worktree assumptions?
- Did it drift into Icon Asset Validator implementation instead of selection?
- Did it claim the full local root verification bundle or green main?
- Did it fail to define clear deferred lanes?
- Did it fail to define the future implementation boundary?

If any finding is real, fix the document or test first, rerun targeted checks, then record evidence in `docs/review/PR_<N>_FIXED_MAPPING.md`.

## Bug-Hunter Checklist

Bug-hunter must inspect the actual diff.

Check:

- docs/test-only diff,
- no runtime diff,
- no generated mirror diff,
- no Figma/Canva writes,
- no implicit implementation lane start,
- no tracked symlink/worktree artifacts,
- `.venv/bin/python` policy present,
- premortem-as-real-fix rule present,
- selected next lane explicit,
- deferred lanes explicit.

## Codex Security Checklist

Codex Security review is diff-scoped.

Check:

- no secrets or credentials,
- no external write authority,
- no live design-tool mutation,
- no hidden production autonomy,
- no App Store upload or release activation permission,
- no runtime prompt or GEPA self-modification path,
- no weakened repo guard or merge-readiness language.

## Bounded Checks

Use repo `.venv` only:

```bash
.venv/bin/python scripts/orchestration/check_preflight.py
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed
PATH=.venv/bin:$PATH pre-commit run --all-files
```

For this docs/test-only lane, if `PATH=.venv/bin:$PATH pre-commit run --all-files`
hangs or is terminated in the repo-wide `check-added-large-files` scan, the
accepted bounded substitute is:

```bash
PATH=.venv/bin:$PATH pre-commit run --from-ref origin/main --to-ref HEAD
git push
```

The substitute is valid only if pre-push hooks complete, changed-file large-file
checks pass, the failure is documented in the PR body and fixed mapping, and no
runtime, token, generated mirror, binary asset, screenshot, video, trace,
Figma, Canva, or Storybook config path appears in the diff.

Do not run the full local root verification bundle for this docs/test decision lane. Do not claim green main.

## Merge Readiness

Do not claim merge readiness until:

- current-head PR checks complete,
- CodeRabbit/Sourcery/Cubic/Codex/human actionables are dispositioned,
- no unresolved review threads remain,
- PR body mirrors `docs/review/PR_<N>_FIXED_MAPPING.md`,
- mandatory wait-window completes,
- strict wrapper passes:

```bash
GH_TOKEN=$(gh auth token) GITHUB_TOKEN=$(gh auth token) \
.venv/bin/python scripts/orchestration/check_merge_ready.py \
  --pr-number <PR_NUMBER> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --require-auth
```

## Rollback

Revert this docs/test PR. No runtime rollback is required.

## Post-Merge Cleanup

Post-merge local main synchronization is operator-owned and must not be printed as a generated agent PR prompt. The agent should report PR status, current evidence, and lane-local cleanup needs only.

Remove only this lane's local branch, worktree if used, temporary artifacts, caches, logs, and untracked symlink/worktree-only leftovers if the operator asks for cleanup after merge. Do not delete unrelated root changes or collaborator work.

## DoD

- Next design automation lane is explicitly selected.
- Deferred lanes are explicitly recorded.
- Future implementation boundary is explicit.
- No runtime files changed.
- No token or generated mirror files changed.
- No Figma/Canva writes.
- `.venv/bin/python` policy is preserved.
- Premortem fixes real docs/test defects before mapping.
- Bug-hunter and Codex Security passes find no unresolved blockers.
- Bounded checks pass.
