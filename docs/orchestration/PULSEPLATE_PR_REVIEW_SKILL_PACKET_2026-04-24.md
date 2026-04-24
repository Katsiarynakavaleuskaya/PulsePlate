# PulsePlate PR Review Skill Packet - 2026-04-24

## Purpose

Create a conservative PR1 for `pulseplate-pr-review`: a passive, coordinator-owned Codex skill that helps PulsePlate run repo-native PR self-review when external review quota is unavailable or delayed.

This packet does not create a new merge authority. Root `AGENTS.md`, scoped `AGENTS.md`, `RUNBOOK_AGENT.md`, `make verify`, strict merge-readiness wrappers, and fixed-mapping disposition governance remain the source of truth.

## Scope

Allowed in PR1:

- add `tools/codex_skills/pulseplate-pr-review/SKILL.md`
- expose the repo mirror at `.agents/skills/pulseplate-pr-review`
- route review and PR-governance tasks toward `pulseplate-pr-review`
- update Codex skill inventory and routing docs
- add deterministic tests for skill install parity and routing
- record the PR2 context collector follow-up in `docs/roadmap/BACKLOG_LEDGER.md`

Out of scope for PR1:

- GitHub review comment posting
- review-thread resolution
- merge automation
- context collector CLI implementation
- required Sentry, Figma, Browser Use, Computer Use, Hugging Face, Jam, or Life Science runtime dependencies
- replacing CodeRabbit, Sourcery, or Cubic as external advisory signals

## Coordinator Start

The lane starts with `agent-coordinator` and the generated local packet:

- packet id: `53344af8fac1`
- packet path: `artifacts/orchestration/task_packets/53344af8fac1.json`
- primary agent: `agent-coordinator`
- reviewer: `architecture-specialist`
- requested agents:
  - `agent-coordinator`
  - `architecture-specialist`
  - `security-auditor`
  - `qa-engineer-agent`
  - `bug-hunter`
  - `data-scientist-agent`

The pre-edit bootstrap command was:

```bash
python3 scripts/orchestration/task_bootstrap.py \
  --goal "Add passive PulsePlate PR review skill for repo-native CodeRabbit/Sourcery/Cubic-style self-review" \
  --task-class "Orchestration" \
  --path tools/codex_skills \
  --path scripts/orchestration/skill_router.py \
  --path docs/orchestration \
  --path docs/dev/CODEX_SKILLS.md \
  --requested-agent agent-coordinator \
  --requested-agent architecture-specialist \
  --requested-agent security-auditor \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter \
  --requested-agent data-scientist-agent \
  --pr-phase pre_open
```

## Role Order

1. `agent-coordinator`: scope lock, skill authority boundary, synthesis, DoD.
2. `architecture-specialist`: no parallel orchestration layer; passive skill/router architecture only.
3. `security-auditor`: privileged-surface safety, plugin boundaries, no auto-resolve, no broad scraping.
4. `qa-engineer-agent`: deterministic tests, validation evidence, merge-ready gate plan.
5. `bug-hunter`: false-green risks, edge cases, historical reviewer-pattern coverage.
6. `data-scientist-agent`: advisory false-positive calibration and future benchmark design.

Optional consults:

- `frontend-engineer` for frontend/browser/Figma review surfaces.
- `backend-engineer` for backend/API/OpenAPI review surfaces.
- `app-store-release-agent` for billing, subscriptions, Fastlane, and App Store surfaces.
- `wellness-analyst-agent` and `philosophy-agent` for wellness, psychology, and claim-safety surfaces.
- `creative-designer` for design-fidelity surfaces.

## Skill And Plugin Contract

Required PR1 skills:

- `pulseplate-workflow`
- `pulseplate-gates`
- `pulseplate-guards`
- `code-review-expert`
- `pulseplate-pr-review`

Conditional companion skills:

- `bug-triage`
- `security-best-practices`
- `security-threat-model`
- manual-only `cybersecurity-skills`
- `docs-sync`
- `agents-md`

Plugin roles are advisory only:

- GitHub: PR metadata, checks, reviews, and future dry-run-to-comment path.
- CodeRabbit: reference workflow only; no quota dependency.
- Hugging Face: optional research/model scouting for code review and vulnerability detection.
- Browser Use / Computer Use: optional visual/runtime evidence for frontend flows.
- Figma: optional design fidelity evidence only with valid design metadata.
- Sentry/Jam: optional production/runtime evidence when callable data exists.
- Life Science Research: optional wellness/psychology claim-safety evidence, not core code-review runtime.

## Finding Schema

Every finding produced by the skill must include:

- `severity`: `critical`, `major`, `minor`, or `note`
- `role_agent`
- `category`
- `file`
- `line`
- `evidence`
- `suggested_fix`
- `gate_to_run`
- `disposition_candidate`: `FIXED`, `NOT-A-BUG`, `DEFERRED`, or `NEEDS-HUMAN`

## Deferred Follow-up

PR2 may add `scripts/orchestration/pr_review_context.py` as a read-only context collector for changed files, diff stats, scoped `AGENTS.md`, PR metadata, fixed-mapping state, and relevant test suggestions.

Backlog anchor:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pulseplate-pr-review-context-collector`

## Acceptance

- `pulseplate-pr-review` exists in repo skills and discovery mirror.
- Review and PR-governance routing recommends `pulseplate-pr-review`.
- Skill docs explicitly forbid auto-merge, auto-resolve, and replacing canonical gates.
- Install mirror tests include the new skill.
- Skill-router tests prove explicit review and PR-governance selection.
- Focused validation passes before opening the PR.
