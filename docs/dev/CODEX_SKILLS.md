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
scripts/install_codex_skills.sh --no-cybersec
scripts/install_codex_skills.sh --copy-cybersec
scripts/install_codex_skills.sh --only-cybersec --copy-cybersec
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

## Codex CLI safe path

For normal PulsePlate repo work, prefer:

```bash
scripts/install_codex_skills.sh --no-cybersec
```

If you need the cybersecurity bundle in Codex CLI, prefer copied installs:

```bash
scripts/install_codex_skills.sh --only-cybersec --copy-cybersec
```

Why: Codex follows symlink targets when scanning skills. The cybersecurity bundle
is valid by slug, but repo-target symlink paths like
`tools/cybersecurity_skills/skills/<slug>` can still surface noisy
`invalid name: exceeds maximum length of 64 characters` warnings in Codex logs.
Copying just that bundle avoids the long repo-target path without changing the
repo source of truth.

## Restart requirement

After installation or updates, restart Codex so newly installed skills are loaded.
This restart requirement is tooling-local only; it does not change repo orchestration semantics.

## Troubleshooting

If OpenCode or Codex reports fewer loaded skills than the repo contains:

1. Run the verifier: `python3 scripts/verify_codex_skills_install.py --strict`
2. See the full diagnosis flow: [`docs/dev/OPENCODE_SKILL_DISCOVERY_RUNBOOK.md`](./OPENCODE_SKILL_DISCOVERY_RUNBOOK.md)

## Host `~/.codex` (compatibility-only, not repo SoT)

Machine-local Codex settings (`~/.codex/config.toml`, skills under `$CODEX_HOME/skills` with `~/.codex/skills` as the fallback) are **not**
repository source of truth. Keys drift with Codex CLI versions; verify against current vendor docs.
Use `$CODEX_HOME/skills` only as an explicit compatibility target when a local Codex setup still expects it.

If an older host setup already populated `$CODEX_HOME/skills` with the
cybersecurity bundle, remove that legacy install before relying on the official
user path:

```bash
scripts/install_codex_skills.sh --unlink --target compat --only-cybersec
```

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

**Raw session note:** nothing in this file runs at host session start. For a new PR lane, prefer `scripts/orchestration/start_pr_lane.sh` from a clean checkout synced with `origin/main`; it creates the isolated worktree, runs analyze preflight, invokes `task_bootstrap.py`, and prints the packet summary plus plugin/runtime checklist. Use `scripts/orchestration/local_session_bootstrap.sh` (optional) only when you need analyze preflight and a printed `task_bootstrap.py` command without creating a worktree. Evidence for the weaker helper: `scripts/orchestration/local_session_bootstrap.sh:145-147` (analyze preflight) and `scripts/orchestration/local_session_bootstrap.sh:154-166` (printed task bootstrap command).

**Launcher vs skills:** If you use an opt-in machine launcher (see [`docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md`](./LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md)), run preflight/bootstrap **before** relying on installed skills or manual task work. **Skills do not replace** `task_bootstrap.py`; they complement routing after a packet exists.

**Plugins vs skills:** external plugins such as Browser Use, Computer Use, GitHub, Hugging Face, Life Science Research, Plugin Eval, and CodeRabbit are operator/runtime checklist items. The repo starter may print them to make availability explicit, but it does not install them, fail closed when they are unavailable, or treat them as product/runtime truth. Repo-native skill selection still comes from `task_bootstrap.py` `recommended_skills`.

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
Wave 2 routing packets additionally expose `skill_routing.explanation` for the
stable explanation schema and `skill_routing.research_connector_policy` for the
approved research-only connector contract. Evidence:
`scripts/orchestration/skill_router.py:594-626`,
`scripts/orchestration/skill_router.py:695-733`,
`scripts/orchestration/task_bootstrap.py:786-923`,
`tests/test_skill_router.py:1510-1586`,
`tests/test_task_bootstrap.py:163-183`.

## Skill map (task to skill)

- Start task with repo policy context: `pulseplate-workflow`
- Run hard quality gates and failure triage: `pulseplate-gates`
- Regenerate OpenAPI + frontend schema types: `pulseplate-openapi-sync`
- Build UI in project style: `pulseplate-frontend-ui`
- Record deferred work and follow-ups: `pulseplate-ledger`
- Triage architecture/policy guards: `pulseplate-guards`
- Add backend endpoints with policy checks: `pulseplate-backend-endpoints`
- Produce AI trend reports: `pulseplate-ai-reports`
- Prepare App Store metadata, screenshot packs, and release evidence: `pulseplate-app-store-release`
- Guide monetization, paywall, pricing, and wellness-safe GTM work: `pulseplate-monetization-gtm`
- Govern design-system readiness, launch-asset boundaries, and token/brand consistency: `pulseplate-design-launch-system` (evidence: `tools/codex_skills/pulseplate-design-launch-system/SKILL.md:1`, `tests/test_install_codex_skills.py:264`, `tests/test_skill_router.py:750`)
- Plan and implement public launch-site pages, CTA funnels, waitlist/lead-capture paths, and wellness-safe launch copy: `pulseplate-web-launch-site` (evidence: `tools/codex_skills/pulseplate-web-launch-site/SKILL.md:1`, `tests/test_skill_router.py:657`)
- Shape agent-product surfaces, operator workflows, HITL boundaries, and product handoffs without creating runtime autonomy: `pulseplate-agent-product` (evidence: `tools/codex_skills/pulseplate-agent-product/SKILL.md:1`, `tests/test_skill_router.py:847`)
- Build/update architecture graph artifact: `pulseplate-graphmap`
- Run browser E2E flows (step 3 extension): `pulseplate-playwright-e2e`
- Run coordinator-owned PR self-review before external review-bot signals: `pulseplate-pr-review` (evidence: `tools/codex_skills/pulseplate-pr-review/SKILL.md:1`, `docs/orchestration/PULSEPLATE_PR_REVIEW_SKILL_PACKET_2026-04-24.md:1`)
- Run premortem risk analysis on high-downside plans before merge or launch: `pulseplate-premortem-risk-review` (evidence: `tools/codex_skills/pulseplate-premortem-risk-review/SKILL.md:1`, `scripts/orchestration/skill_router.py`)

## Project-specific whitelist

Recommended now for PulsePlate:

- `pulseplate-ai-reports` for founder/wellness/AI reporting
- `pulseplate-app-store-release` for App Store metadata, screenshot packs, and release evidence
- `pulseplate-monetization-gtm` for monetization, paywall, pricing, and wellness-safe GTM work
- `pulseplate-design-launch-system` for passive design-launch governance, launch asset bundles, token/brand consistency, and fail-closed packet metadata review (evidence: `tools/codex_skills/pulseplate-design-launch-system/SKILL.md:8`, `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:15`, `tests/test_skill_router.py:750`)
- `pulseplate-web-launch-site` for launch-site pages, CTA funnels, waitlist/lead-capture paths, and wellness-safe public launch copy (evidence: `tools/codex_skills/pulseplate-web-launch-site/SKILL.md:8`, `tests/test_skill_router.py:657`)
- `pulseplate-agent-product` for agent-product surfaces, operator workflows, HITL boundaries, and product handoffs that preserve coordinator authority (evidence: `tools/codex_skills/pulseplate-agent-product/SKILL.md:8`, `tests/test_skill_router.py:847`)
- `pulseplate-pr-review` for passive, coordinator-owned PR self-review that stays advisory and preserves merge-readiness gates
- `pulseplate-premortem-risk-review` for premortem risk analysis on high-downside plans (PR, epic, launch, security, CI/CD, AI/RAG, App Store, monetization, design decisions)
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
`pulseplate-design-launch-system` is a governance-only helper and must follow
that source precedence rather than override it (evidence: `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:17`, `docs/design/TOKENS_SOT.md:18`, `tools/codex_skills/pulseplate-design-launch-system/SKILL.md:55`).

Not approved as default:

- broad internet scraping workflows
- TikTok scraping
- Google Maps scraping
- universal “any site” collectors

## Rollout steps

1. Step 1: Core workflow + gates + contract sync skills.
2. Step 2: Domain skills (guards, backend endpoints, AI reports, graph map).
3. Step 3: Browser E2E extension with Playwright (`pulseplate-playwright-e2e`) for controlled web flow automation.
4. Step 4: Launch/product extensions (`pulseplate-design-launch-system`, `pulseplate-web-launch-site`, `pulseplate-agent-product`, `pulseplate-pr-review`) for repo-native go-to-market, agent-product, and review governance support.
5. Step 5: Risk/decision extensions (`pulseplate-premortem-risk-review`) for premortem risk analysis on high-downside plans before merge or launch.

## Computer Use / MCP troubleshooting

- `Computer Use` is a bundled plugin, not a repo-local MCP server.
- If Codex returns `Apple event error -10000: Sender process is not authenticated`,
  the failure is in macOS permissions, not in repo routing or skill setup.
- Grant `Codex` (`com.openai.codex`) access in macOS `Privacy & Security` for:
  `Accessibility` and `Screen Recording`.
- After changing permissions, restart Codex and re-check the tool.
- Repo-local MCP examples such as `.cursor/mcp.json.example` cover checked-in
  integrations like Figma only; they do not provision macOS privacy permissions.

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
