<!-- markdownlint-disable MD013 -->
# PulsePlate Canonical PR Execution Prompt v2026-05-08

## Summary

This document is the canonical PulsePlate PR-prompt contract for coordinator-owned design and orchestration lanes after the Design Intelligence PR-8 and next-lane decision sequence.

It governs prompts handed to Codex or role agents. It does not override root `AGENTS.md`, scoped `AGENTS.md`, `RUNBOOK_AGENT.md`, fixed-mapping governance, current-head CI, or strict merge-readiness rules.

## Prompt Canon

Generated PR prompts must:

- start from a clean worktree created directly from `origin/main`;
- open a normal review PR after local narrow evidence exists;
- omit operator-owned post-merge local main synchronization commands;
- create a worktree-local virtual environment with `python3.13 -m venv .venv --copies`;
- use repo-local Python commands through `.venv/bin/python`;
- list `make validate-changed` as the only `make` target in prompt text;
- state that bounded local checks are evidence only, not a merge-ready claim;
- require PR body, checkbox, fixed-mapping, review-governance, and merge-readiness docs to be read before PR opening;
- keep external tools such as Figma, Canva, Storybook, Browser Use, Slack, Hugging Face, Supabase, and research connectors as evidence or reference layers unless a coordinator packet explicitly scopes stronger authority.

Generated PR prompts must not:

- instruct agents to switch the root checkout;
- include a provisional PR state instruction;
- include the full local root verification bundle as a prompt command;
- list additional `make` targets in prompt text;
- delegate post-merge local main synchronization to the agent prompt;
- treat skills, plugins, browser state, design files, prompt outputs, scorecards, or evidence packs as source of truth.

## Required Startup Flow

The execution prompt must require this order before edits:

```bash
git fetch --prune origin
git worktree add -b <branch> <worktree-path> origin/main
cd <worktree-path>
python3.13 -m venv .venv --copies
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

The prompt must include all touched paths as repeated `--path` arguments in preflight and bootstrap so scoped `AGENTS.md` resolution is explicit.

## Required Execution Chain

The minimum pre-open execution chain is:

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `security-auditor`
5. `creative-designer`
6. `qa-engineer-agent`
7. `bug-hunter`

If `task_bootstrap.py` or `agent-coordinator` expands the role order, the expanded order becomes mandatory for the lane. No declared role agent may be skipped without a coordinator update to the packet or PR body.

## Required Skills And Plugins

Use these as passive helpers, not authority:

- `chronicle` for recent-screen or prior-run context when available and relevant.
- `pulseplate-design-launch-system` for design source-precedence and launch/design governance.
- `pulseplate-premortem-risk-review` for required premortem execution.
- `pulseplate-pr-review` for CodeRabbit/Sourcery/Cubic-style self-review.
- Codex Security plugin for diff-scoped security review.

Any additional plugin or connector remains optional evidence unless the coordinator packet explicitly scopes its use.

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

The prompt may include this local validation bundle:

```bash
.venv/bin/python scripts/orchestration/check_preflight.py --path <path>
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python -m pytest -q <targeted-test-file>
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed
PATH=.venv/bin:$PATH pre-commit run --all-files
```

Additional targeted commands are allowed only when they are not `make` targets and are tied to the touched surface.

## Review Governance

The prompt must require agents to read PR body, checkbox, fixed-mapping, and merge-readiness governance before PR opening.

After the PR number exists:

- create `docs/review/PR_<N>_FIXED_MAPPING.md`;
- keep the PR body as a mirror of the canonical artifact;
- record mapping only after the underlying fix or formal decision exists;
- never use mapping as a substitute for fixing a real defect.

Merge readiness still depends on current-head CI, review dispositions, fixed mapping, mandatory wait-window, and the strict merge wrapper. Local bounded checks alone do not prove readiness.

## Operator Boundary

Post-merge local main synchronization is operator-owned. Generated agent prompts should close with PR status, evidence, cleanup instructions for lane-local artifacts, and any blocked merge-readiness state, but should not provide post-merge root checkout command sequences.

## Scope Boundary

This canon is a prompt and governance contract. It does not authorize runtime web, iOS, backend, OpenAPI, billing, auth, StoreKit, HealthKit, `/tokens`, generated mirrors, Figma, Canva, Storybook config, screenshots, videos, traces, binary assets, or external asset generation.
