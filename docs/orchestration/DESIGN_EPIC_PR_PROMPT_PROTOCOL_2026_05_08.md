<!-- markdownlint-disable MD013 -->
# Design Epic PR Prompt Protocol v2026-05-08

## Summary

This protocol governs future PulsePlate design-epic PR prompts after the merged post-PR-8 design automation decision.

It is support infrastructure for the design epic. It does not replace `docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md`, does not rewrite the post-PR-8 next-lane packet, and does not make prompt outputs a product or design source of truth.

## Prompt Contract

Future design-epic PR prompts must:

- start from a clean worktree created directly from `origin/main`;
- open a normal review PR only after local narrow evidence exists;
- create a worktree-local virtual environment with `python3.13 -m venv .venv --copies`;
- refresh locked repo dependencies inside that environment with `make venv-sync`;
- use repo-local Python commands through `.venv/bin/python`;
- include all touched paths as repeated `--path` arguments in preflight and bootstrap commands;
- list `make validate-changed` as the only default `make` target in generated prompt command blocks;
- state that bounded local checks are evidence only and do not prove merge readiness;
- require PR body, checkbox, fixed-mapping, review-governance, and merge-readiness docs to be read before PR opening;
- keep Figma, Canva, Storybook, Browser Use, Slack, Hugging Face, Supabase, and research connectors as evidence or reference layers unless a separate repo-reviewed contract promotes a narrower authority.

Future design-epic PR prompts must not:

- instruct agents to switch the root checkout;
- include provisional PR-state wording;
- include the full local root verification bundle as a prompt command;
- list stale design-lane `make` targets in generated prompt command blocks;
- delegate post-merge local main synchronization to the agent prompt;
- treat skills, plugins, browser state, design files, prompt outputs, scorecards, or evidence packs as source of truth.

## Required Startup Flow

The generated prompt must require this order before edits:

```bash
git fetch --prune origin
git worktree add -b <branch> <worktree-path> origin/main
cd <worktree-path>
python3.13 -m venv .venv --copies
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make venv-sync
.venv/bin/python scripts/orchestration/check_preflight.py --path <path>
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python scripts/orchestration/task_bootstrap.py \
  --goal "<goal>" \
  --task-class "<class>" \
  --pr-phase pre_open \
  --path <path> \
  --requested-agent agent-coordinator \
  --requested-agent cursor-specialist-agent \
  --requested-agent architecture-specialist \
  --requested-agent security-auditor \
  --requested-agent creative-designer \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter
```

Use repeated `--path` arguments for every touched file or directory that matters for scoped `AGENTS.md` resolution.

## Required Execution Chain

The minimum pre-open execution chain is:

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `security-auditor`
5. `creative-designer`
6. `qa-engineer-agent`
7. `bug-hunter`

If `task_bootstrap.py` or `agent-coordinator` expands the role order, the expanded order becomes mandatory for the lane. No declared role agent may be skipped without a coordinator update to the lane packet or runbook; the PR body may mirror that decision but cannot replace it.

## Premortem Requirement

Premortem is mandatory before PR opening and again after the first bot-review cycle.

The premortem must inspect the actual diff across docs, tests, scripts, and code in scope. Reviewing only the PR body, checkboxes, or fixed-mapping artifact is insufficient.

Every premortem finding must close before readiness:

- `FIXED`: change docs, tests, scripts, or code and cite file plus command evidence.
- `NOT-A-BUG`: coordinator records why the finding does not apply, with repo evidence.
- `DEFERRED`: coordinator records the backlog anchor and PR-body follow-up.

If a finding is real, fix the underlying issue first, rerun the targeted gate, then update `docs/review/PR_<N>_FIXED_MAPPING.md`.

## Post-Open And Bot-Review Chain

After opening the PR, run:

1. `qa-engineer-agent`
2. `bug-hunter`
3. `security-auditor`
4. Codex Security plugin diff scan

After the first bot review, run:

1. `agent-coordinator`
2. `qa-engineer-agent`
3. `bug-hunter`
4. `security-auditor`
5. premortem rerun on the actual updated diff

Findings from these passes follow the same fix-before-mapping rule as human and bot review threads.

## Bounded Validation Prompt

The generated prompt may include this local validation bundle:

```bash
.venv/bin/python scripts/orchestration/check_preflight.py --path <path>
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python -m pytest -q <targeted-test-file>
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed
PATH=.venv/bin:$PATH pre-commit run --all-files
```

Use `check_preflight.py --mode execute --path <path>` for the final pre-open validation pass after edits and before push.

Additional targeted commands are allowed only when they are not `make` targets and are tied to the touched surface. Environment setup target `make venv-sync` is allowed in startup only; it is not validation evidence.

## Review Governance

After the PR number exists:

- create `docs/review/PR_<N>_FIXED_MAPPING.md`;
- keep the PR body as a mirror of the canonical artifact;
- record mapping only after the underlying fix or formal decision exists;
- never use mapping as a substitute for fixing a real defect.

Merge readiness still depends on current-head CI, review dispositions, fixed mapping, mandatory wait-window, and the strict merge wrapper. Local bounded checks alone do not prove readiness.

## Design-Epic Boundary

This protocol does not authorize runtime web, iOS, backend, OpenAPI, billing, auth, StoreKit, HealthKit, `/tokens`, generated mirrors, Figma, Canva, Storybook config, screenshots, videos, traces, binary assets, or external asset generation.

It supports future design-epic PR prompts only. The selected future design automation lane remains the Icon Asset Validator / App Store asset guard lane recorded by the merged post-PR-8 decision packet.
