# Context Loading Procedure

How to load and inject per-agent context before dispatch.

## Source of Truth

Each agent's required context is defined in:
`docs/orchestration/AGENT_CONTEXT_MAP.md`

This file lists, per agent slug:
- `required_context` — files that MUST be loaded
- `conditional_context` — files loaded only if the task matches a condition
- `optional_context` — files loaded if budget allows

## Loading Steps

1. **Resolve agent slug** from the dispatch manifest entry
2. **Look up context map** for that slug's `required_context` paths
3. **Read each file** listed in `required_context`
4. **Check conditions** for `conditional_context` entries:
   - If condition matches the packet's scope/domain, load the file
   - Otherwise skip it
5. **Assemble prompt section** titled "Required Context" with loaded content
6. **Budget check** — see below

## Context Budget

- Target: keep total prompt under ~50K tokens (including agent definition + context)
- If `required_context` alone exceeds budget:
  - Summarize files longer than 200 lines (keep first 20 + last 20 lines + summary)
  - Never drop `required_context` entirely — always include at least the summary
- `optional_context` is loaded only if remaining budget allows
- Priority order: required > conditional (matched) > optional

These budget rules govern the ordinary manual prompt path. They do not permit
summarization inside an exact delivery requested with
`--role-context-order <N>`. Exact mode either returns every byte of its finite
supported source inventory or returns an incomplete/manual result or a
fail-closed error.

## Prompt Assembly Order

```
1. System instructions (agent definition from .cursor/agents/<slug>.md)
2. Packet constraints (scope, DoD, hard rules)
3. Required Context (loaded files)
4. Previous agent output (if depends_on_previous)
5. Task-specific instructions
```

## Caching

The bridge does not persist exact context and exposes no cache CLI control.
Every invocation reacquires and revalidates the selected finite repository
sources. Historical experiment evidence belongs in the governing backlog item
and local lane artifacts, not in permanent dispatch instructions.

For exact JSON packet-backed delivery:

1. Select one existing final dispatch occurrence by one-based order.
2. Use the returned raw role definition and ordered source contents directly.
3. Keep the returned packet dynamic and outside the static source digest. Any
   static path resolving to the packet's captured device/inode identity blocks
   the exact invocation.
4. Do not reread, summarize, truncate, normalize, or infer instructions from
   recommended skill names.
5. Treat `complete=false` as a manual-loading requirement. Missing, unsafe,
   malformed, changed, or over-limit sources block the exact invocation.
