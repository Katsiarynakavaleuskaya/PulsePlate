# PulsePlate Agent Init

Initialize a PulsePlate agent session with the repo-native path below.

1. Read [`AGENTS.md`](../../AGENTS.md)
2. Read [`docs/ENGINEERING_LESSONS.md`](../../docs/ENGINEERING_LESSONS.md)
3. Read [`RUNBOOK_AGENT.md`](../../RUNBOOK_AGENT.md)
4. Read the nearest scoped `AGENTS.md` for the files you plan to touch
5. Read [`docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md`](../../docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md)
6. If you need project-local MCP wiring, copy [`.cursor/mcp.json.example`](../mcp.json.example) to `.cursor/mcp.json`
7. If you need Codex skills, run [`scripts/install_codex_skills.sh`](../../scripts/install_codex_skills.sh) and restart Codex

Use the repository's canonical custom orchestration workflow for any new task:

1. Start with coordinator-first routing via `agent-coordinator`
2. Follow [`docs/orchestration/workflow.md`](../../docs/orchestration/workflow.md)
3. If you are unsure whether something counts as a task, treat it as a task and use coordinator-first routing

Do not treat this local command as an alternative orchestration path.
