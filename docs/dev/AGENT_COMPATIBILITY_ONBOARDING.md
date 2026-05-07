# Agent Compatibility Onboarding

Short repo-specific startup guide for agent users.

## Start here

Read these in order:

1. [`AGENTS.md`](../../AGENTS.md)
2. [`docs/ENGINEERING_LESSONS.md`](../ENGINEERING_LESSONS.md)
3. [`RUNBOOK_AGENT.md`](../../RUNBOOK_AGENT.md)
4. the nearest scoped `AGENTS.md` for the files you touch
5. for a new PR lane, run the repo-level starter:
   `scripts/orchestration/start_pr_lane.sh --goal "<goal>" --task-class "<class>" --branch "codex/<slug>" --worktree "worktrees/<slug>"`
   and paste its `Paste into Codex now` block into the Codex session before
   implementation
6. optional machine-local launcher (if installed on your host): see [`LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md`](./LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md) — **opt-in only**, not a global default
7. coordinator bootstrap: `scripts/orchestration/check_preflight.py` then `scripts/orchestration/task_bootstrap.py` (or the printed recipe from `local_session_bootstrap.sh`)
8. this guide for tool-specific setup notes

## Cursor

- Canonical agent specs live in [`.cursor/agents/`](../../.cursor/agents/)
- Cursor-specific scoped rules live in [`.cursor/agents/AGENTS.md`](../../.cursor/agents/AGENTS.md)
- The repo keeps a project-local command surface in [`.cursor/commands/`](../../.cursor/commands/)
- If you want project MCP wiring locally, start from [`.cursor/mcp.json.example`](../../.cursor/mcp.json.example)

Suggested first action in Cursor:

- open [`.cursor/commands/init.md`](../../.cursor/commands/init.md)
- use it as a local bridge into the canonical coordinator-first workflow, not as a replacement for [`docs/orchestration/workflow.md`](../orchestration/workflow.md)
- follow the local startup checklist there

## Raw session vs bootstrap (invariant)

Policy and routing are **deterministic only after** you run the repo entrypoints (`check_preflight.py`, then `task_bootstrap.py`). Markdown and skills do **not** auto-start a coordinator-first session on the host.

Preferred first command for a new PR lane from a clean, synced repo root:

```bash
scripts/orchestration/start_pr_lane.sh \
  --goal "<short goal>" \
  --task-class "<task_class>" \
  --branch "codex/<slug>" \
  --worktree "worktrees/<slug>" \
  --path "<touched-path>"
```

This creates the isolated worktree, runs analyze preflight, runs
`task_bootstrap.py`, and prints the non-blocking plugin/runtime checklist, the
bootstrap packet summary, and a Codex-ready coordinator-start prompt. It does
not push, open a PR, install host plugins, or auto-start a raw Codex session.

Optional raw-session helper when you only need preflight plus a printed
bootstrap recipe:

```bash
scripts/orchestration/local_session_bootstrap.sh
```

See [`docs/orchestration/AUTOMATION_READINESS_MATRIX.md`](../orchestration/AUTOMATION_READINESS_MATRIX.md) for capability claims vs launcher requirements.

## Codex

- Repo-native Codex skills live in [`tools/codex_skills/`](../../tools/codex_skills/)
- Repo discovery mirror for Codex lives in [`.agents/skills/`](../../.agents/skills/)
- Install them with:

```bash
scripts/install_codex_skills.sh --no-cybersec
```

- Primary install target follows the canonical contract in [`docs/dev/CODEX_SKILLS.md`](./CODEX_SKILLS.md):
  `$AGENTS_HOME/skills` with `$HOME/.agents/skills` as the fallback
- Legacy compat target follows the same contract:
  `$CODEX_HOME/skills` with `~/.codex/skills` as the fallback (`scripts/install_codex_skills.sh --target compat`)
- If you need the cybersecurity bundle in Codex CLI, prefer copied installs:
  `scripts/install_codex_skills.sh --only-cybersec --copy-cybersec`
- After install or updates, restart Codex so the new skills load
- Full skill map and policy notes live in [`docs/dev/CODEX_SKILLS.md`](./CODEX_SKILLS.md)
- Preferred repo-root PR lane starter (isolated worktree + preflight + packet):
  `scripts/orchestration/start_pr_lane.sh`
- Optional repo-root helper (preflight analyze + printed `task_bootstrap.py` recipe):
  `scripts/orchestration/local_session_bootstrap.sh`
- Codex raw sessions are not the same as Cursor's init bridge: repo markdown,
  docs, and skills do not execute themselves at session start. Use the
  Codex-ready block printed by the repo starter or helper as the explicit
  bridge into coordinator-first sequencing.
- Host-only `~/.codex/config.toml` is outside repo SoT; optional template:
  [`docs/templates/codex.config.example.toml`](../templates/codex.config.example.toml)
- Skills stay passive/discovery-only. They do not auto-start coordinator bootstrap and must not change Cursor/custom orchestration behavior.
- `Computer Use` is a bundled plugin, not a checked-in repo MCP server. If it fails with
  `Apple event error -10000`, fix macOS `Accessibility` and `Screen Recording`
  permissions for `Codex` (`com.openai.codex`), then restart Codex.

## Claude

- This repo now keeps a lightweight [`CLAUDE.md`](../../CLAUDE.md) at the root as the project entrypoint
- [`CLAUDE.md`](../../CLAUDE.md) is only a bridge; the source of truth remains [`AGENTS.md`](../../AGENTS.md), [`RUNBOOK_AGENT.md`](../../RUNBOOK_AGENT.md), and scoped `AGENTS.md`
- There is currently no checked-in project `.claude/` skill tree in this repository

## Precedence

When instructions overlap, use this order:

1. root `AGENTS.md`
2. nearest scoped `AGENTS.md`
3. `RUNBOOK_AGENT.md`
4. optional host launcher (if present) for **ordering** preflight/bootstrap only — does not override policy in root `AGENTS.md`
5. tool-specific bridge docs such as this file, `CLAUDE.md`, or `docs/dev/CODEX_SKILLS.md`

## Local validation reminder

For the current compatibility-friendly backend loop, start from the canonical
navigation in [`AGENTS.md`](../../AGENTS.md) and [`RUNBOOK_AGENT.md`](../../RUNBOOK_AGENT.md).

- `pytest -q tests/test_repo_policy_guards.py` for the cheapest policy sanity check
- `make test-fast` for the deterministic smoke subset
- `make verify` only for the full PR gate
