# Orchestration Dispatch — Agent Instructions

## Envelope Protocol

Communication between the dispatch layer and agents uses two envelope types:

- **TASK_PACKET_V1** (dispatcher → agent): Contains task scope, constraints,
  required context paths, and expected output format.
- **AGENT_RESULT_V1** (agent → dispatcher): Contains status, findings, artifacts
  produced, and blockers encountered.
- **REPAIR_REQUEST_V1** (dispatcher → agent): Sent when result is insufficient;
  contains what's missing and retry constraints.

Envelope usage is optional in Qoder — natural language prompts work. Envelopes
add structure for audit trail and cross-tool compatibility.

## Role Mapping (Summary)

| Agent slug | Qoder type | Notes |
|------------|-----------|-------|
| agent-coordinator | Research | Always analysis mode |
| architecture-specialist | Research | Read-only |
| philosophy-agent | Research | Read-only |
| rag-systems-agent | Research | Coding if mode=runtime |
| security-auditor | Research | Read-only |
| qa-engineer-agent | Verify | Runs tests |
| bug-hunter | Verify | Runs tests |
| backend-engineer | Coding | Research if mode=analysis |
| frontend-engineer | Coding | Browser if UI validation |
| dev-operator | Coding | Research if mode=analysis |
| All others | Research | Safe fallback |

Full mapping: `rules/role-mapping.md`

## Context Loading

1. Read `docs/orchestration/AGENT_CONTEXT_MAP.md` for per-role requirements
2. Load each file listed under `required_context` for the active role
3. Include loaded content in the subagent prompt under "Required Context"
4. If total context exceeds ~50K tokens, summarize secondary/conditional files

## Parallelization Rules

- Agents in the same `parallelizable_groups` array MAY run concurrently
- An agent with `depends_on_previous: true` MUST wait for its predecessor
- The post-open mandatory pass is always sequential: qa-engineer → bug-hunter
- Coordinator (first) and QA pass (last) are never parallelized with others
- The post-open role/security/review chain is one required pass per PR lane. Do
  not rerun the full chain for each new review comment. Later comments are
  handled through `docs/review/PR_<N>_FIXED_MAPPING.md` disposition and targeted
  validation unless a new security-relevant diff, coordinator routing update, or
  explicit operator instruction reopens the chain.

## Error Handling

- `status: "completed"` — proceed to next agent
- `status: "blocked"` — stop sequence, report blocker to user, do NOT skip
- `status: "partial"` — feed partial results to next agent, flag for synthesis
- If an agent fails to produce a result within timeout, treat as blocked
- Never auto-retry more than once without user confirmation
