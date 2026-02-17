# Codex Skills for PulsePlate

This document explains how to install and use repo-tracked PulsePlate Codex skills.

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

## Rollout steps

1. Step 1: Core workflow + gates + contract sync skills.
2. Step 2: Domain skills (guards, backend endpoints, AI reports, graph map).
3. Step 3: Browser E2E extension with Playwright (`pulseplate-playwright-e2e`) for controlled web flow automation.

## Canonical source

- Skill source folders: `tools/codex_skills/`
- Installer script: `scripts/install_codex_skills.sh`
- Step 3 runbook: `docs/dev/PLAYWRIGHT_E2E_RUNBOOK.md`
- Coordinator and agent index:
  - `.cursor/agents/agent-coordinator.md`
  - `docs/agents/index.md`
