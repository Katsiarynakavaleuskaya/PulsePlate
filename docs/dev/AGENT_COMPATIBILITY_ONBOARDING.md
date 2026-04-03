# Agent Compatibility Onboarding

Short repo-specific startup guide for agent users.

## Start here

Read these in order:

1. `AGENTS.md`
2. `docs/ENGINEERING_LESSONS.md`
3. `RUNBOOK_AGENT.md`
4. the nearest scoped `AGENTS.md` for the files you touch
5. this guide for tool-specific setup notes

## Cursor

- Canonical agent specs live in `.cursor/agents/`
- Cursor-specific scoped rules live in `.cursor/agents/AGENTS.md`
- The repo keeps a project-local command surface in `.cursor/commands/`
- If you want project MCP wiring locally, start from `.cursor/mcp.json.example`

Suggested first action in Cursor:

- open `.cursor/commands/init.md`
- use it as a local bridge into the canonical coordinator-first workflow, not as a replacement for `docs/orchestration/workflow.md`
- follow the local startup checklist there

## Codex

- Repo-native Codex skills live in `tools/codex_skills/`
- Install them with:

```bash
scripts/install_codex_skills.sh
```

- After install or updates, restart Codex so the new skills load
- Full skill map and policy notes live in `docs/dev/CODEX_SKILLS.md`

## Claude

- This repo now keeps a lightweight `CLAUDE.md` at the root as the project entrypoint
- `CLAUDE.md` is only a bridge; the source of truth remains `AGENTS.md`, `RUNBOOK_AGENT.md`, and scoped `AGENTS.md`
- There is currently no checked-in project `.claude/` skill tree in this repository

## Precedence

When instructions overlap, use this order:

1. root `AGENTS.md`
2. nearest scoped `AGENTS.md`
3. `RUNBOOK_AGENT.md`
4. tool-specific bridge docs such as this file, `CLAUDE.md`, or `docs/dev/CODEX_SKILLS.md`

## Local validation reminder

For the current compatibility-friendly backend loop:

- `make validate-min` for the cheap deterministic local bundle
- `make validate-changed` for diff-based Python test selection
- `make verify` only for the full PR gate
