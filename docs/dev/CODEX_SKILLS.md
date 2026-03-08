# Codex Skills for PulsePlate

<!-- markdownlint-disable MD013 -->

This document explains how PulsePlate skills are installed and how the coordinator should use them automatically.

## Install

Default install mode uses symlinks:

```bash
scripts/install_codex_skills.sh
```

Useful options:

```bash
scripts/install_codex_skills.sh --list
scripts/install_codex_skills.sh --copy
scripts/install_codex_skills.sh --unlink
scripts/install_codex_skills.sh --dest /tmp/codex-skills
```

## Restart requirement

After installation or updates, restart Codex so newly installed skills are loaded.

## Coordinator-first auto-selection

The user should not have to name skills manually for normal project work.

Selection order:

1. `pulseplate-workflow`
2. Domain routing via `docs/orchestration/AGENT_ROUTING_GRAPH.md`
3. Skill policy via `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
4. Deterministic bootstrap via `scripts/orchestration/task_bootstrap.py`

The bootstrap task packet now carries `recommended_skills`, so coordinator and domain agents can invoke fitting skills as part of the workflow.
For explainability, the packet also carries `skill_routing` metadata with weighted evidence and blocked-pattern notes.

## Skill map (task to skill)

- Start task with repo policy context: `pulseplate-workflow`
- Run hard quality gates and failure triage: `pulseplate-gates`
- Regenerate OpenAPI + frontend schema types: `pulseplate-openapi-sync`
- Build UI in project style: `pulseplate-frontend-ui`
- Record deferred work and follow-ups: `pulseplate-ledger`
- Triage architecture/policy guards: `pulseplate-guards`
- Add backend endpoints with policy checks: `pulseplate-backend-endpoints`
- Produce AI trend reports: `pulseplate-ai-reports`
- Build/update architecture graph artifact: `pulseplate-graphmap`
- Run browser E2E flows (step 3 extension): `pulseplate-playwright-e2e`

## Project-specific whitelist

Recommended now for PulsePlate:

- `pulseplate-ai-reports` for founder/wellness/AI reporting
- `docs-sync` for orchestration, runbooks, and PR support docs
- `bug-triage` and `pulseplate-gates` for remediation and gate closure
- `openai-docs`, `playwright`, `figma`, `linear`, `notion-research-documentation` when the task explicitly matches

Not approved as default:

- broad internet scraping workflows
- TikTok scraping
- Google Maps scraping
- universal “any site” collectors

## Rollout steps

1. Step 1: Core workflow + gates + contract sync skills.
2. Step 2: Domain skills (guards, backend endpoints, AI reports, graph map).
3. Step 3: Browser E2E extension with Playwright (`pulseplate-playwright-e2e`) for controlled web flow automation.

## Canonical source

- Skill source folders: `tools/codex_skills/`
- Installer script: `scripts/install_codex_skills.sh`
- Step 3 runbook: `docs/dev/PLAYWRIGHT_E2E_RUNBOOK.md`
- Skill routing policy: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- Coordinator and agent index:
  - `.cursor/agents/agent-coordinator.md`
  - `docs/agents/index.md`
