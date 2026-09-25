---
name: pulseplate-orchestration-dispatch
description: Execute a coordinator-owned PulsePlate JSON role packet through the available Codex-native subagent transport.
license: MIT
metadata:
  author: PulsePlate
  version: '1.2.0'
---

# PulsePlate Orchestration Dispatch

Use this skill after coordinator routing establishes the governing packet. Root
`AGENTS.md` owns authority and role gates; `docs/orchestration/workflow.md` owns
staged startup. This skill consumes the existing bridge and creates no parser,
role registry, implementation permission or model service.

## Codex-native input boundary

Use a governing JSON packet from the existing `task_bootstrap.py` with validated,
unambiguous `native_subagent_bridge` bindings for this Codex-native workflow.
Existing CLI Markdown or `--roles` parsing remains available for manifest
inspection; that compatibility path does not admit native dispatch by itself.
Manual bootstrap means generating the JSON packet with the existing bootstrap,
not inventing bindings from a Markdown list. Reuse an existing governing packet;
do not create a second packet merely to follow the manual path. Missing or
ambiguous bindings block the dependent native dispatch, not authorized diagnosis.

## Packet-backed dispatch

1. Before dispatching a potentially writable runtime-owner occurrence, run
   execute-mode preflight with the declared scope/routing inputs and require
   exit 0 under `docs/orchestration/workflow.md` → Admit tracked implementation.
   This does not require completed preparatory roles and grants no edit authority.
2. Reuse the governing packet. Copy
   `role_agent_dispatch_contract.dispatch_manifest_command` verbatim, replace
   `<packet>` with its actual path, and use repo-approved Python. Do not
   reconstruct a generic bridge command or drop runtime mode/owner flags.
3. Require successful validation by
   `scripts/orchestration/role_dispatch_bridge.py`. A nonzero exit or nonempty
   `missing_agents` blocks dispatch; retain diagnostics and repair the input.
   No best-effort parsing or guessed role fallback is permitted.
4. Default output is the v2 manifest. Exact context output wraps the unchanged
   manifest under `manifest`; consume its selected occurrence and source
   contents under `rules/context-loading.md`.
5. Preserve every `dispatch_sequence` occurrence and its `order`, phase,
   readonly/owner constraints and predecessor evidence. Execute serially as
   required by `parallel_execution_allowed=false`; group hints do not grant
   parallel execution. Repeated slugs are separate occurrences. Do not append
   or normalize a later post-open tail into a pre-open or analysis sequence.
6. For Codex, use the matching packet `native_subagent_bridge` binding's
   `native_agent_type` on hosts supporting typed dispatch, not `qoder_subagent_type`.
   A generic-only host may use the root-authorized general-purpose native spawn
   while preserving that validated binding, canonical role/context and action limits;
   omit unsupported typed/model/effort arguments and report the actual transport.
   Resolve the applicable role slot without discarding repeated occurrences;
   an absent or ambiguous packet binding still blocks native dispatch.
   See `rules/role-mapping.md` and the model policy's required-choice boundary.
7. The coordinator dispatches new native children with the full role,
   applicable authority context, packet/criteria and predecessor output.
   Follow `docs/agents/model_policy.md` for inherited arguments or the explicitly
   enabled Astra/Sol mode. Native transport and model choice grant no write
   authority and do not change the manifest. Every preparatory occurrence,
   including an owner with `readonly=false`, receives an explicit prohibition
   on tracked writes until all preparatory roles finish and the coordinator
   issues a separate implementation handoff after successful preflight.
   The emitted owner set may contain multiple eligible slugs. Each later handoff
   selects one active eligible role, its occurrence and exact files under the
   canonical workflow; other eligible roles receive no implementation task.
   Keep every metadata flag and serial occurrence unchanged.
8. Record each actual result before the next dependent occurrence. Synthesize
   against the accepted criteria after the declared pass; packet generation
   and a role's `completed` status do not prove overall completion.

### Runtime-owner command example

Illustration for a packet whose emitted eligible-owner set contains only
`security-auditor`. Other packets may emit multiple owner flags; preserve them
all. Use your actual emitted command after
the required preflight. Owner metadata never overrides the preparation write ban.
The override is role-slug scoped for every eligible repetition; it is not an
occurrence permission selector. See `rules/role-mapping.md` for mixed-rights requests.

```bash
python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/example/packet.json --mode runtime --implementation-owner security-auditor --pretty
```

### Exact-context command example

Extend the actual packet-emitted command only with the selected occurrence and
explicit admitted instruction paths. Preserve every eligible owner and existing flag.
Replace `<emitted-dispatch-command>` with that unchanged command after substituting
its packet path. Select `<N>` from the intended occurrence's `order` in the actual
validated manifest, using its role/slot and order to distinguish repetitions.
Missing or ambiguous selection blocks that context request, not analysis. Replace
both placeholders before running; do not copy a number from an unrelated packet.
`--role-context-order` selects context only; it does not narrow owner permissions.

```bash
<emitted-dispatch-command> --role-context-order <N> --instruction-file tools/codex_skills/pulseplate-workflow/SKILL.md
```

## Context and evidence boundaries

Load the full role definition, not `system_prompt_excerpt`. Exact JSON delivery
uses the existing `pulseplate.role-context-output.v1` envelope and its bounded
source checks. A successful complete delivery is used directly; do not reread,
summarize or truncate it. Unsupported glob/directory context returns
`complete=false` and requires the existing manual loading route. Missing,
unsafe, changed or over-limit sources are errors, not complete context.
For manual loading, the coordinator resolves navigation selectors to explicit
task-applicable paths with reasons under the canonical context map. Fully load
the selected required sources and every literal mandatory authority/role file;
do not expand a wildcard into an indiscriminate library read or claim a summary
is full context. See `rules/context-loading.md` for the bounded limitation path.

Skill names alone do not load instructions. Supply admitted repository
`--instruction-file` paths when using exact delivery. The bridge has no
context-cache CLI flag and stores no exact context between invocations.

The later mandatory post-open pass and exact-material closeout follow root
`AGENTS.md`. Provider absence requires no invocation/retry and is not review,
scan, approval or no-findings evidence. No full local verification budget or
unscheduled role-chain repeat follows from this skill.

## Operational Creative handoff

When the validated packet applicability projection recommends Creative and the
coordinator admits bounded alternatives, use the same native transport and
packet binding. This is a host procedure, not a provider call in repository
Python. A direct fix, disabled treatment, or higher-assurance preemption does
not enter this procedure.

1. Retain the complete accepted requirements source, criteria version, current
   packet bytes, base/head, exact allowed paths, test budget, and validated Euler
   reference. Build one `creative_workflow_request.v1` under the owned ignored
   artifact directory. Run `experiment_runner_pr_creative_context.py
   workflow-prepare --packet <packet> --request <request> --output-dir <dir>`.
   A missing or changed source blocks preparation.
2. Spawn the assigned native agent with the full canonical role and packet
   context. Ask for exactly one `creative_workflow_native_result.v1` JSON object:
   three concrete distinct variants plus an unchanged baseline, with criterion
   IDs, exact paths, assumptions, observations, counterexamples, tests, risks,
   Euler relation IDs, request fingerprint and packet ID. Await the actual
   returned output. Send its bytes to `workflow-ingest --workflow
   <workflow.prepared.json> --native-result-stdin` through host stdin. The user
   does not transcribe or create `model_intake.json`. On malformed/incomplete
   output the returned stage records only `INVALID_NATIVE_RESULT`; no validated
   intake or completion claim follows.
3. Coordinator inspects content, goal coverage, Euler relation and
   counterexample evidence. Capture its separate structured review and run
   `workflow-review`. Only then capture one exact-file, packet-eligible writer
   handoff and run `workflow-admit`. These stage artifacts record the host's
   decisions; their JSON, hashes and role labels do not authenticate a human,
   execute the writer, or grant repository/merge authority by themselves.
4. Dispatch the selected writer under the normal packet's separate
   implementation handoff. Compare the actual Git diff paths, elapsed candidate
   time and executed focused-test count with the selected exact files and
   request budget; record an overrun as a failed/pending outcome. Review the
   actual patch and test results against each accepted criterion in Work
   Review. Export a sanitized owned capsule using `workflow-export`, then let
   the host upload, read the same document ID, download the archive, compare its
   SHA-256 and run `workflow-verify-archive` into a fresh owned directory. Until
   this round trip passes, record `storage_pending` and retain local evidence.

Reopen an existing stage only against its unchanged source and input; identical
replay is a no-write reuse, while divergent replay or changed packet,
requirements or Euler bytes fails. Material changes stale dependent review;
recheck affected criteria without automatically restarting every role or
generating a new proposal. The legacy creative-context v1 intake and PR-2
sandbox remain separate, with their existing product and workflow target bans.

## Canonical references

- `scripts/orchestration/role_dispatch_bridge.py` — existing manifest entrypoint
- `scripts/orchestration/qoder_dispatch_bridge.py` — compatibility implementation
- `scripts/orchestration/native_subagent_bridge.py` — native bindings
- `docs/orchestration/AGENT_CONTEXT_MAP.md` — role context requirements
- `.cursor/agents/` — canonical role definitions
