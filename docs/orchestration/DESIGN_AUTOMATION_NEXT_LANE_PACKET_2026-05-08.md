<!-- markdownlint-disable MD013 -->
# Design Automation Next-Lane Packet

## Summary

This packet governs the docs-only PR that selects the next PulsePlate design automation module after Design Intelligence PR-8.

- Branch: `docs/design-automation-next-lane-decision-v1`
- Title: `docs(design): select next design automation module after PR-8`
- Classification: docs/test-only decision packet
- Selected future lane: Icon Asset Validator / App Store asset guard lane

This PR does not implement the selected lane.

## Coordinator Route

Mandatory start gate:

```bash
git status --short
git checkout main
git fetch --prune origin
git merge --ff-only origin/main
git rev-list --left-right --count HEAD...origin/main
git status --short
test -x .venv/bin/python
.venv/bin/python scripts/orchestration/check_preflight.py
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python scripts/orchestration/task_bootstrap.py \
  --goal "Post-PR-8 design automation lane selection: docs-only decision packet for the next design automation module" \
  --task-class "Design" \
  --pr-phase pre_open \
  --requested-agent agent-coordinator \
  --requested-agent creative-designer \
  --requested-agent architecture-specialist \
  --requested-agent security-auditor \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter \
  --requested-agent data-scientist-agent
```

Role order:

1. `agent-coordinator`
2. `creative-designer`
3. `architecture-specialist`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`
7. `data-scientist-agent`

Post-open review repeats the route with `--pr-phase post_open_review`, then runs a second pass after bot comments and a final regression pass before merge readiness.

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
- Did it claim full local `make verify` or green main?
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
.venv/bin/python scripts/design/generate_design_md.py --check
.venv/bin/python -m pytest -q tests/test_design_automation_next_lane_docs.py
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make design-guard
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make tokens-check
PATH=.venv/bin:$PATH pre-commit run --all-files
```

Do not run full local `make verify` for this docs/test decision lane. Do not claim green main.

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

After merge:

```bash
git checkout main
git fetch origin
git merge --ff-only origin/main
git rev-list --left-right --count HEAD...origin/main
git status --short
```

Remove only this lane's local branch, worktree if used, temporary artifacts, caches, logs, and untracked symlink/worktree-only leftovers if any were created. Do not delete unrelated root changes or collaborator work.

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
