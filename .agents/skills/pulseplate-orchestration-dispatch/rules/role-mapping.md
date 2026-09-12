# Native Role Binding Consumption

## Canonical sources

The role slug and full `.cursor/agents/<slug>.md` definition are canonical.
The existing `scripts/orchestration/native_subagent_bridge.py` builds packet
native bindings; `role_dispatch_bridge.py` validates manifest occurrences and
explicit runtime ownership. This guide contains no independent mapping table.

For Codex, select `native_agent_type` from the matching packet
`native_subagent_bridge` binding. Current Codex types are `default`, `explorer`
and `worker`; Qoder `qoder_subagent_type` is for the Qoder adapter only. Bind the
applicable slot and occurrence; missing or ambiguous bindings stop dispatch.
Do not infer a type from a role name, readonly flag, or the task's size.

## Role constraints survive transport

Readonly describes permitted actions. It is not proof that an OS sandbox blocks
writes. Readonly Logic/Philosophy may use `default`; readonly verification or
review roles may use their native binding, including Qoder Verify/CodeReview.
An implementation-capable transport never grants write authority by itself.

Use an explicit packet-bound `--mode runtime --implementation-owner <role>`
override only for the coordinator's designated owner, scope and phase. Preserve
the manifest's resulting readonly and owner flags. Model choice cannot widen
them. Generic worker instructions do not permit implementation by other roles.

### Inherited Logic argument example

Illustrative Codex call arguments for a Logic binding; the actual `message`
must include the full required role/context, packet and predecessor evidence.
The omitted model/effort fields follow `docs/agents/model_policy.md`.

```json
{
  "task_name": "logic_review",
  "message": "You are PulsePlate custom role logic-agent. Perform the assigned read-only analysis using the supplied full required context and predecessor evidence.",
  "agent_type": "default"
}
```

The coordinator owns this manifest's declared role dispatch and model choices.
Already-authorized subordinate delegation cannot replace those occurrences or
expand scope. Follow the canonical native model policy for explicitly enabled
routing; this document creates no model service, fallback router, role ownership
or retry loop.
