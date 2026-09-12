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

1. **Resolve the occurrence and agent slug** from the dispatch manifest entry
2. **Look up context map** for that slug's `required_context` paths
3. **Select concrete sources** under the context map's applicability conditions.
   Wildcard/directory entries such as `docs/orchestration/*` are navigation
   selectors, not instructions to expand and read the entire library. The
   coordinator records selected concrete paths and an applicability reason for
   each in the handoff. Preserve every literal mandatory packet/role file,
   root `AGENTS.md`, and nearest scoped `AGENTS.md`.
4. **Read the selected mandatory files fully**, including each task-applicable
   conditional source. The selection follows
   `docs/orchestration/AGENT_CONTEXT_MAP.md` → Context Requirements by Agent;
   it does not invent a parser, change that map or imply all wildcard files were read.
5. **Assemble prompt section** titled "Required Context" with loaded content
6. Include the current packet, accepted criteria and predecessor output. Keep
   the full role definition; `system_prompt_excerpt` is not sufficient.

## Context Budget

- Load every selected mandatory role, authority and applicable context file fully.
  Do not replace them with excerpts or summaries to meet a convenience budget.
- Trim or summarize optional reference material first. Literal mandatory files
  cannot be silently dropped because of size. If the selected required material
  truly cannot be delivered, report the concrete missing paths and bounded
  context limitation to the coordinator for evidence rescoping before the
  dependent action. Never describe a summary or omitted file as full delivery.
- A new child with a bounded/no-history fork still needs the same required
  context and predecessor evidence; model selection does not waive it.

The same full-context obligation applies to the manual prompt path and to
exact delivery requested with
`--role-context-order <N>`. Exact mode either returns every byte of its finite
supported source inventory or returns an incomplete/manual result or a
fail-closed error.
The existing exact materializer and successful complete source bytes remain
unchanged. A glob/directory `complete=false` result uses the manual selection
above; selection is not a claim that the exact invocation completed.

## Prompt Assembly Order

```
1. Role definition/project instructions (.cursor/agents/<slug>.md), under runtime and user precedence
2. Packet constraints (scope, DoD, hard rules)
3. Required Context (loaded files)
4. Relevant predecessor findings/evidence for each required serial occurrence
5. Task-specific instructions
```

`depends_on_previous` describes a handoff dependency; a false value does not
authorize skipping a serial occurrence or withholding predecessor evidence
needed for that assigned pass.

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
