# Codex Skills for PulsePlate

<!-- markdownlint-disable MD013 -->

This document explains how PulsePlate skills are discovered, installed, and kept
strictly passive inside the repository's coordinator-first bootstrap flow.

For the wider agent startup path across Cursor, Codex, and Claude, start with
[`docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md`](./AGENT_COMPATIBILITY_ONBOARDING.md).

## Install

Default install mode uses symlinks into the official user discovery path:

```bash
scripts/install_codex_skills.sh
```

Useful options:

```bash
scripts/install_codex_skills.sh --list
scripts/install_codex_skills.sh --copy
scripts/install_codex_skills.sh --target compat
scripts/install_codex_skills.sh --unlink
scripts/install_codex_skills.sh --dest /tmp/codex-skills
```

Discovery and install precedence:

1. Repo source of truth: `tools/codex_skills/`
2. Repo discovery mirror for Codex: `.agents/skills/`
3. Primary user install target: `$AGENTS_HOME/skills` (fallback: `$HOME/.agents/skills`)
4. Compatibility-only legacy target: `$CODEX_HOME/skills` (fallback: `~/.codex/skills`, via `--target compat`)

Use this section as the canonical discovery/install contract. Neighbor docs should reference it instead of restating host-path details independently.

Invariant:

- `tools/codex_skills/` remains the only repo source of truth.
- `.agents/skills/` is a passive discovery mirror, not a second canonical tree.
- The installer is operator-invoked only. It must not mutate Cursor config, launchers, shell profiles, or session behavior.

## Restart requirement

After installation or updates, restart Codex so newly installed skills are loaded.
This restart requirement is tooling-local only; it does not change repo orchestration semantics.

## Host `~/.codex` (compatibility-only, not repo SoT)

Machine-local Codex settings (`~/.codex/config.toml`, skills under `$CODEX_HOME/skills` with `~/.codex/skills` as the fallback) are **not**
repository source of truth. Keys drift with Codex CLI versions; verify against current vendor docs.
Use `$CODEX_HOME/skills` only as an explicit compatibility target when a local Codex setup still expects it.

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

**Launcher vs skills:** If you use an opt-in machine launcher (see [`docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md`](./LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md)), run preflight/bootstrap **before** relying on installed skills or manual task work. **Skills do not replace** `task_bootstrap.py`; they complement routing after a packet exists.

**Non-interference contract:** skills remain passive/discovery-only helpers. They do not:

- replace `agent-coordinator`,
- replace `scripts/orchestration/task_bootstrap.py`,
- turn `recommended_skills` into execution authority,
- change `native_subagent_bridge` semantics,
- or modify Cursor/custom orchestration behavior without explicit operator action.

**Advisory wiki (optional):** For operator-local wiki snapshots over the experimental support plane, see [`docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md`](../orchestration/LOCAL_WIKI_SUPPORT_PLANE.md) (`wiki_ingest` / `wiki_query` / `wiki_lint` / `wiki_promote`). This remains non-canonical and gitignored.

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
- Repo discovery mirror: `.agents/skills/`
- Installer script: `scripts/install_codex_skills.sh`
- Step 3 runbook: `docs/dev/PLAYWRIGHT_E2E_RUNBOOK.md`
- Skill routing policy: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- Alignment matrix / non-interference policy: `docs/orchestration/CODEX_SKILLS_ALIGNMENT_MATRIX.md`
- Coordinator and agent index:
  - `.cursor/agents/agent-coordinator.md`
  - `docs/agents/index.md`
