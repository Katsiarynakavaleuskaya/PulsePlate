---
name: pulseplate-pr-review
description: Run a coordinator-owned PulsePlate PR self-review that mirrors CodeRabbit/Sourcery/Cubic-style scrutiny without replacing repo merge gates or external review governance.
---

# PulsePlate PR Review

## When to use

- Reviewing a PulsePlate PR before or after external CodeRabbit, Sourcery, or Cubic feedback.
- Preparing a PR for post-open `qa-engineer-agent -> bug-hunter` review.
- Auditing logical, semantic, technical, wellness-safety, and cybersecurity risks in a PR.
- Checking whether review findings have enough evidence before they become fixed-mapping dispositions.

## Inputs required

- PR number or branch name, if available.
- Changed file list or candidate paths.
- Active coordinator packet or task packet path.
- Existing `docs/review/PR_<N>_FIXED_MAPPING.md`, if the PR is already open.
- Target mode: `dry-run-report`, `post-open-review`, or `merge-ready-audit`.

## Coordinator start

1. Start with repo gates and coordinator bootstrap:

   ```bash
   python3 scripts/orchestration/check_preflight.py
   python3 scripts/orchestration/check_agent_consistency.py
   python3 scripts/orchestration/task_bootstrap.py --goal "<goal>" --task-class "Orchestration" --pr-phase pre_open
   ```

2. Preserve the coordinator-declared role order. This skill is advisory and must not invent a parallel review authority.
3. Treat `recommended_skills` and `skill_routing` from the packet as additive context, not execution permission.

## Role order

Use this default order unless the active packet declares a narrower compatible sequence:

1. `agent-coordinator`: scope lock, role assignment, synthesis, DoD.
2. `architecture-specialist`: boundaries, ownership, layering, duplicate logic, public contract drift.
3. `security-auditor`: auth, quota, secrets, subprocess safety, broad scraping, plugin and GitHub safety.
4. Surface owners as applicable: `backend-engineer`, `frontend-engineer`, `app-store-release-agent`, `wellness-analyst-agent`, `philosophy-agent`, `creative-designer`.
5. `qa-engineer-agent`: deterministic test plan, missing negative cases, gate coverage.
6. `bug-hunter`: edge cases, false-green risks, historical reviewer-pattern gaps.
7. `data-scientist-agent`: optional scoring, false-positive calibration, and benchmark follow-up design.

## Review procedure

1. Load canonical context:

   ```bash
   sed -n '1,220p' AGENTS.md
   sed -n '1,220p' RUNBOOK_AGENT.md
   sed -n '1,220p' docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md
   sed -n '1,220p' docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md
   ```

2. Inspect the diff and prior review patterns:

   ```bash
   git diff --name-only origin/main...HEAD
   git diff --stat origin/main...HEAD
   rg -n "CodeRabbit|Sourcery|Cubic|Disposition:|FIXED|NOT-A-BUG|DEFERRED" docs/review docs/orchestration
   ```

3. For deterministic dry-run mode, collect context and render the report:

   ```bash
   python3 scripts/orchestration/pr_review_context.py --pr <PR_NUMBER> --output /tmp/pulseplate_pr_review_context.json
   python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr_review_context.json --format markdown
   python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr_review_context.json --format json
   ```

4. Classify findings with the required schema:
   - `severity`: `critical`, `major`, `minor`, or `note`
   - `role_agent`: owning reviewer agent
   - `category`: correctness, security, architecture, tests, docs, wellness, release, or governance
   - `file` and `line`: exact pointer when available
   - `evidence`: repo file, command output, PR thread, Sentry/Jam signal, Figma metadata, or model/research reference
   - `suggested_fix`: smallest concrete fix
   - `gate_to_run`: exact command that proves the fix
   - `disposition_candidate`: `FIXED`, `NOT-A-BUG`, `DEFERRED`, or `NEEDS-HUMAN`

5. Keep plugin evidence optional:
   - GitHub: PR metadata, checks, reviews, and future dry-run-to-comment path.
   - CodeRabbit: reference workflow only; do not depend on available review quota.
   - Hugging Face: optional model/paper scouting for code review and vulnerability-detection methods.
   - Browser Use / Computer Use: optional visual/runtime evidence for frontend flows.
   - Figma: optional design fidelity evidence only with valid packet metadata.
   - Sentry/Jam: optional production or reproduced runtime evidence when callable data exists.
   - Life Science Research: optional wellness/psychology claim-safety evidence, not core code-review runtime.

## Output format

- `Coordinator packet`: task packet id/path and role order used.
- `Scope reviewed`: changed files and omitted surfaces.
- `Findings`: schema-compliant ordered list by severity.
- `Role review`: one short paragraph per assigned role agent.
- `Gate plan`: exact commands to run or rerun.
- `Deferred / Follow-ups`: backlog anchors for intentionally postponed work.
- `Decision log`: what this review does and does not prove.

## Guardrails

- Do not replace `agent-coordinator`, `scripts/orchestration/task_bootstrap.py`, `make verify`, `check_merge_ready.py`, or fixed-mapping governance.
- Do not auto-merge, auto-resolve review threads, or post GitHub review comments in v1.
- Do not claim CodeRabbit/Sourcery/Cubic approval unless those external tools actually ran.
- Do not treat LLM/model output as proof without repo evidence or a deterministic gate.
- Do not make Sentry, Figma, Browser Use, Computer Use, Hugging Face, Jam, or Life Science Research required dependencies for ordinary PR review.
- Do not use broad scraping or external data collection outside the bounded research-only lane.

## SoT links

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `scripts/orchestration/pr_review_context.py`
- `scripts/orchestration/pr_review_report.py`
