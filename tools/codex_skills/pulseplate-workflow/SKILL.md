---
name: pulseplate-workflow
description: Start any PulsePlate task with the required policy, scope, and quality-gate workflow.
---

# PulsePlate Workflow

<!-- markdownlint-disable MD013 -->

## When to use

- Starting any new task in this repository.
- Clarifying scope before coding, testing, or documentation changes.
- Ensuring coordinator-first routing and AGENTS policy compliance.

## Inputs required

- Task goal in one sentence.
- Candidate paths to change (or `unknown`).
- Expected output (code change, docs update, report, or review).

## Procedure (commands)

1. Baseline repo state:

   ```bash
   git status --short
   git log -1 --oneline
   ```

2. Load policy context:

   ```bash
   ls AGENTS.md RUNBOOK_AGENT.md
   find . -name AGENTS.md -maxdepth 4 | sort
   ```

3. Identify relevant module scope:

   ```bash
   rg -n "Scope and layout|This AGENTS.md applies to" app/AGENTS.md core/AGENTS.md frontend/AGENTS.md ios/AGENTS.md tests/AGENTS.md
   ```

4. Start coordinator-first routing for multi-agent work:
   - Use `.cursor/agents/agent-coordinator.md` as entrypoint.

5. For PR/live merge work, use current-head truth only:

   ```bash
   GH_TOKEN=$(gh auth token) python3 scripts/orchestration/check_review_threads_disposition.py --pr-number <PR_NUMBER> --require-auth
   GITHUB_TOKEN=$(gh auth token) python3 scripts/ci/check_pr_merge_readiness.py --pr-number <PR_NUMBER> --repo Katsiarynakavaleuskaya/PulsePlate
   gh pr checks <PR_NUMBER>
   ```

   Notes:
   - Treat `gh pr checks <PR_NUMBER>` as diagnostic-only.
   - A non-zero exit can mean live pending jobs, not failed checks.
   - If only one current-head job remains live, inspect it directly with
     `gh run view <RUN_ID>` or `gh run view --job=<JOB_ID>`.

6. For design/frontend tasks, load the code-first UI naming layer:

   ```bash
   sed -n '1,220p' docs/design/UI_COMPONENT_VOCABULARY.md
   sed -n '1,220p' docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md
   ```

7. After a PR is merged, verify merge state and clean the lane before starting
   follow-up work:

   ```bash
   gh pr view <PR_NUMBER> --json state,mergeCommit,mergedAt
   git fetch --prune origin
   git worktree list
   ```

   Notes:
   - If `state=MERGED`, remove the merged worktree and local branch in the same
     work session.
   - Do not continue pushing to a merged PR branch; start the next slice from a
     fresh branch/worktree on `origin/main`.

## Output format

- `Task summary`: one paragraph.
- `Scope`: exact files/directories in scope.
- `Policy checks`: list of AGENTS/RUNBOOK files used.
- `Execution plan`: ordered steps with command list.
- `Risks`: concrete constraints and fallback path.
- `PR lane decision`: continue current PR, or open replacement PR after parent merge / auto-close.

If blocked, always include:

- Raw failing lines.
- `file:line:error` pointers.
- Minimal next-fix steps.

## Guardrails

- Do not claim green/ready/mergeable without local gate evidence.
- Avoid bypassing hard rules in `AGENTS.md`.
- Refrain from editing unrelated dirty files.
- Do not use GUI/RPA automation in this workflow.
- If a stacked child PR auto-closes after parent merge, rebase the child branch
  onto `origin/main`, rerun local gates, and open a replacement PR with a new
  `docs/review/PR_<N>_FIXED_MAPPING.md` artifact.
- Post-merge cleanup is part of the workflow, not optional housekeeping.

## SoT links

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `.cursor/agents/AGENTS.md`
- `.cursor/agents/agent-coordinator.md`
- `app/AGENTS.md`
- `core/AGENTS.md`
- `frontend/AGENTS.md`
- `ios/AGENTS.md`
- `tests/AGENTS.md`
