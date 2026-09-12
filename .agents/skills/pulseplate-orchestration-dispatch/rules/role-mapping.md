# Native Role Binding Consumption

## Canonical sources

The role slug and full `.cursor/agents/<slug>.md` definition are canonical.
The existing `scripts/orchestration/native_subagent_bridge.py` builds packet
native bindings; `role_dispatch_bridge.py` validates manifest occurrences and
explicit runtime ownership. This guide contains no independent mapping table.

For Codex, select `native_agent_type` from the matching packet
`native_subagent_bridge` binding in the governing validated JSON packet.
CLI Markdown/manual manifest parsing does not supply those native bindings.
Current Codex types are `default`, `explorer`
and `worker`; Qoder `qoder_subagent_type` is for the Qoder adapter only. Bind the
applicable slot and occurrence; missing or ambiguous bindings stop dispatch.
Do not infer a type from a role name, readonly flag, or the task's size.
If the host lacks typed-agent arguments, root `AGENTS.md` permits a general-purpose
native spawn using only supported arguments. Preserve the validated packet binding
as role/context evidence without claiming the requested typed executor was selected.

## Role constraints survive transport

Readonly describes permitted actions. It is not proof that an OS sandbox blocks
writes. Readonly Logic/Philosophy may use `default`; readonly verification or
review roles may use their native binding, including Qoder Verify/CodeReview.
An implementation-capable transport never grants write authority by itself.

Use an explicit packet-bound `--mode runtime --implementation-owner <role>`
override as emitted by the governing packet. It may name multiple eligible roles;
preserve the complete set and resulting readonly/owner flags. Eligibility is
distinct from the one active role/occurrence and exact files selected by each
later implementation handoff in the canonical workflow. Unselected eligible
roles receive no implementation task. Model choice and generic worker instructions
do not make that selection or widen its scope.

The existing override is role-slug scoped: every eligible repetition of that
slug receives it. `--role-context-order` selects context delivery after manifest
construction, not permission for one occurrence. Repeated roles are valid.
Only a mixed-rights request that requires different manifest ownership across
those repetitions must stop for coordinator rescoping through existing
phase/packet mechanisms; do not invent occurrence-level bridge enforcement.

Before dispatching an owner occurrence, complete the workflow's executable
preflight. Every preparatory occurrence still has an explicit no-tracked-writes
instruction, even when its metadata says `readonly=false`. After all required
preparatory roles finish and preflight passes, a separate coordinator handoff
selects one active eligible role, occurrence and exact files. Missing or ambiguous
selection/scope blocks implementation, not analysis. This does not change manifest
permissions or enforce sandboxing. That uniform preparation constraint
does not make ordinary repetition a mixed-rights request.

### Inherited Logic argument example

Illustrative Codex call arguments for a Logic binding; the actual `message`
must include the full required role/context, packet and predecessor evidence.
The omitted model/effort fields follow `docs/agents/model_policy.md`.
Use the active host's callable schema; this example is not a universal API signature.

```json
{
  "task_name": "logic_review",
  "message": "You are PulsePlate custom role logic-agent. Perform the assigned read-only analysis using the supplied full required context and predecessor evidence.",
  "agent_type": "default"
}
```

### Generic native-spawn argument example

For a host exposing only supported general-purpose spawn arguments, use the
root-authorized generic transport. This example uses a supported bounded fork;
omit that field too if unavailable. Supply the same full role definition, validated
JSON packet/binding, required context, scope, action constraints and predecessor
evidence in the real handoff. Omit unsupported `agent_type`, `model` and
`reasoning_effort` kwargs; never emulate model choice in prompt prose or claim
typed/requested-model selection occurred. An unavailable explicitly required
model remains subject to the model policy's no-substitution rule. Missing packet
bindings or genuinely missing required action/tool capabilities still block the
dependent action; generic transport grants no metadata or permission bypass.

```json
{
  "task_name": "generic_security_review",
  "message": "You are PulsePlate custom role security-auditor. Perform the assigned read-only preparation with no tracked writes, using the supplied full role/context, validated JSON packet and predecessor evidence. Report the actual generic transport without claiming typed or requested-model selection.",
  "fork_turns": "none"
}
```

The coordinator owns this manifest's declared role dispatch and model choices.
Already-authorized subordinate delegation cannot replace those occurrences or
expand scope. Follow the canonical native model policy for explicitly enabled
routing; this document creates no model service, fallback router, role ownership
or retry loop.
