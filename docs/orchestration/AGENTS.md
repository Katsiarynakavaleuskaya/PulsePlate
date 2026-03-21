# Orchestration Docs Scope

Scope: `docs/orchestration/**`

- Root [`AGENTS.md`](../../AGENTS.md) owns repo-global workflow, merge gates, and cross-repo agent policy. Keep this scope file focused on orchestration-doc specifics only.
- When a PR changes workflow or agent behavior only for an orchestration/docs lane, update this scoped file instead of broadcasting initiative-specific routing into root `AGENTS.md`.
- PR-local orchestration packets are the canonical field-level contract for their lane. Higher-level chain docs should keep only the invariant and link back to the packet.
- For the design-agent runtime realignment bridge:
  - primary: `agent-coordinator`
  - secondary: `cursor-specialist-agent`
  - reviewer: `qa-engineer-agent`
  - advisory: `architecture-specialist`
  - optional consult: `creative-designer`, `frontend-engineer`
  - mandatory post-open lane: `qa-engineer-agent -> bug-hunter`
- Any PR that updates `docs/review/PR_<N>_FIXED_MAPPING.md` in this scope must refresh the PR body mirror after the canonical artifact changes.
- Detailed governance procedure lives in:
  - [`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`](./PR_ORCHESTRATION_CONTRACT_MATRIX.md)
  - [`RUNBOOK_AGENT.md`](../../RUNBOOK_AGENT.md)
