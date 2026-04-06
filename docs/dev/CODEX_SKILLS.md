# Codex Skills for PulsePlate

<!-- markdownlint-disable MD013 -->

This document explains how PulsePlate skills are installed and how they plug into the
repository's coordinator-first bootstrap flow.

For the wider agent startup path across Cursor, Codex, and Claude, start with
[`docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md`](./AGENT_COMPATIBILITY_ONBOARDING.md).

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

## Host `~/.codex` (optional, not repo SoT)

Machine-local Codex settings (`~/.codex/config.toml`, skills under `~/.codex/skills`) are **not**
repository source of truth. Keys drift with Codex CLI versions; verify against current vendor docs.

For a **minimal copy-paste starter only**, see
[`docs/templates/codex.config.example.toml`](../templates/codex.config.example.toml).
Customize on your machine; do not treat that template as a production or team contract.

## Repo compatibility bridge

Use the repo bridge documents together:

- [`docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md`](./AGENT_COMPATIBILITY_ONBOARDING.md)
- [`CLAUDE.md`](../../CLAUDE.md)
- [`.cursor/commands/init.md`](../../.cursor/commands/init.md)

## Coordinator-first auto-selection

The user should not have to name skills manually for normal project work, but
that routing comes from the canonical bootstrap/orchestration path, not from
this document by itself.

**Raw session note:** nothing in this file runs at host session start. Use `scripts/orchestration/local_session_bootstrap.sh` (optional) then `task_bootstrap.py` so routing and `recommended_skills` are produced deterministically.

Canonical selection order after bootstrap:

1. `pulseplate-workflow`
2. Domain routing via [`docs/orchestration/AGENT_ROUTING_GRAPH.md`](../orchestration/AGENT_ROUTING_GRAPH.md)
3. Skill policy via [`docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`](../orchestration/AGENT_SKILL_ROUTING_POLICY.md)
4. Deterministic bootstrap via [`scripts/orchestration/task_bootstrap.py`](../../scripts/orchestration/task_bootstrap.py)

When [`scripts/orchestration/task_bootstrap.py`](../../scripts/orchestration/task_bootstrap.py) produces a task packet, it carries
`recommended_skills`, so coordinator and domain agents can invoke fitting
skills as part of the workflow.
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
- `figma` as the first design-system and prototype lane
- `notion-research-documentation` and `notion-knowledge-capture` for governed
  structured memory and handoff pages
- `openai-docs`, `playwright`, `linear` when the task explicitly matches

OpenAI-specific baseline:

- `openai-docs` remains the canonical external-docs lane for OpenAI tasks
- optional runtime pilot for live docs retrieval is documented in
  `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md`
- external MCP/CLI outputs remain advisory and must promote durable findings
  through KPP before they become repo memory

Design-tooling precedence for this repo:

1. `Figma`
2. `Notion`
3. `Airweave`
4. `Penpot`

See `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`.

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
