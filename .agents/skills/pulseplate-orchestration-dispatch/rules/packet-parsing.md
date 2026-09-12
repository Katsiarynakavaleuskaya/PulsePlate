# Packet Consumption Rules

## Existing executable owner

`scripts/orchestration/role_dispatch_bridge.py` owns packet parsing and manifest
validation. Invoke the packet's
`role_agent_dispatch_contract.dispatch_manifest_command`, substituting the
actual packet path and repo-approved interpreter while preserving every mode,
owner and phase flag. Use the examples in `../SKILL.md` only as illustrations.

Do not extract role order with a new Markdown/regex parser, deduplicate slugs,
guess unknown roles, or repair a failed manifest through best-effort parsing.
Supported Markdown/manual inputs still go through the existing bridge.

## Preserve the returned occurrence

- Require exit 0 and an empty `missing_agents` result before native dispatch.
- Ordinary output is the manifest. Exact-context output contains it under
  `manifest` together with the selected current occurrence and context result.
- Keep every `dispatch_sequence` occurrence, its one-based `order`, constraints
  and `depends_on_previous` handoff. Repeated names are not duplicate work to
  discard; occurrence identity includes order and the applicable packet slot.
- Follow the manifest's serial policy. `parallelizable_groups` hints do not
  override `parallel_execution_allowed=false`.
- Preserve the selected phase. `post_open_role_gates` describes the later
  required QA/Bug/Security pass; its presence in metadata does not append that
  pass to an analysis/pre-open sequence. Let the existing bridge handle an
  explicitly selected post-open phase.

## Failure boundary

Retain the original exit code/diagnostic and report the unmet prerequisite.
Missing definitions, invalid input or absent/ambiguous native bindings block
dispatch. A parsed object alone is not proof of role execution or authority.
Context completeness is handled separately under `context-loading.md`.
