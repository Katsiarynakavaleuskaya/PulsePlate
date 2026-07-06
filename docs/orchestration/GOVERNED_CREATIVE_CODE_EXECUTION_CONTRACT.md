# Governed Creative-Code Execution Contract

<!-- markdownlint-disable MD013 -->

**Status:** PR-6 first applied-candidate lane, local private-pilot loop
operator, local Experiment Runner PR creative-context attachment, and approved
creative-hypothesis specification bridge. Repo-only governance contract. No
runtime impact.

**Scope:** Define the authority boundary between a promoted `creative_research`
output, a PR-1 implementation specification, PR-2 local candidate-patch
generation, PR-3 human-approved non-draft PR handoff tooling, PR-4 telemetry,
PR-5 read-only review-disposition integration, the PR-6 local
applied-candidate run-plan wrapper, and a local private-pilot lifecycle
operator, plus a local PR creative-context artifact layer for Experiment
Runner hypothesis generation and agent routing, and a local bridge from human
approved creative hypotheses into existing PR-1 specification candidate
artifacts. PR-2
authorizes only isolated local candidate-patch generation/evaluation. PR-3
authorizes only the separate local promotion tool that can create a new
`experiment/*` branch, push it without force, and open a non-draft PR after
isolated validation and explicit TTY approval. PR-5 may read sanitized review
context or explicit read-only fixtures and emit local advisory disposition /
repair-launch packets. PR-6 may validate a PR-5 repair launch packet, bind the
first applied candidate target to `docs/prompts/cv/program.md`, and emit a
local PR-1 / PR-2 / PR-3 / PR-4 run plan. The private-pilot operator may read
sanitized metadata, refs, and an optional read-only GitHub App capability
report, then emit next-action artifacts only. It does not
authorize draft PRs, shared worktree mutation, existing branch modification,
review-thread resolution, fixed-mapping edits, merge, release, product runtime
AI, OpenAPI/client changes, public multi-tenant use, or Slack/GitHub authority
expansion. The PR creative-context layer may read sanitized PR surface refs,
generate bounded hypotheses or ingest validated operator-supplied local model
hypothesis JSON, route normalized hypotheses to agents, emit coordinator
dispatch handoffs, and prepare a human approval reservation; it does not
authorize candidate patches, repository writes, workflow changes, provider
calls, model adapters, semantic-cache use, or PR/GitHub mutations. The approved
creative-hypothesis bridge may consume that human approval reservation only to
build a validated `CreativeCodeCandidatePacket`, deterministic local metrics,
and existing PR-1 prepare artifacts; it does not widen candidate mutable
surfaces, execute agents, finalize bundles, generate patches, call providers,
write PR/GitHub/Slack state, write product runtime truth, write graph truth, or
open the semantic-cache gate.

---

## Authority Classes

| Class | Authority | Current State |
|---|---|---|
| `research` | Produces hypotheses, scorecards, falsifiers, and promote/defer/discard decisions inside `creative_research`. | Existing governed source only. |
| `code-specification` | Converts a promoted research output into a typed future implementation specification. | Allowed as the closed PR-0 `CreativeCodeCandidatePacket` plus PR-1 `CreativeCodeSpecificationBundle`. |
| `candidate-patch` | Produces isolated candidate patches for local evaluation. | Allowed only through PR-2 `CreativeCodePatchBuildRequest`, deterministic generation gate, sanitized generation receipt, and `CreativeCodePatchResult` artifacts in sandboxed workspaces. |
| `repository-write` | Writes to shared worktrees, creates branches, pushes, opens PRs, marks ready for review, resolves review threads, or merges. | Forbidden except the PR-3 promoter's narrowly validated new `experiment/*` branch push and non-draft PR creation. |
| `promotion` | Promotes a candidate into canonical repo behavior through human review, PR governance, and merge gates. | PR-3 opens the review handoff only. Canonical behavior still requires normal PR review and merge gates. |
| `private-pilot-lifecycle` | Reads sanitized lifecycle metadata and emits local next-action artifacts. | Allowed only through the private-pilot loop operator; no candidate generation or GitHub write authority. |
| `pr-creative-context` | Expands eligible PR context into 3-5 hypotheses, validates operator-supplied local hypothesis JSON, assigns normalized hypothesis IDs, records cross-domain analogies, emits agent routing/coordinator dispatch, and prepares approval reservations. | Allowed only through local sanitized Experiment Runner creative-context artifacts; no repo-side provider/model call, patch generation, workflow mutation, semantic cache, or GitHub write authority. |
| `approved-hypothesis-spec-bridge` | Converts a human-approved creative hypothesis into a validated PR-0 creative-code candidate and existing PR-1 prepare artifacts. | Allowed only through local `creative_hypothesis_spec_bridge.py`; no mutable-surface widening, provider calls, patch generation, PR writes, role execution, finalization, semantic cache, graph truth, or product runtime authority. |
| `reviewed-spec-finalize` | Attaches sanitized local skeptic-review evidence to a prepared bridge run and delegates to existing PR-1 finalize in a sibling reviewed directory. | Allowed only through local `creative_specification_skeptic_review.py`; must preserve `spec_prepare/`; no agent execution, provider calls, patch generation, PR writes, workflow changes, semantic cache, graph truth, product runtime, fixed-mapping edits, review-thread actions, or readiness claims. |
| `reviewed-spec-learning-rollup` | Converts finalized creative specification outcomes into proposal-only learning records and coordinator advisory hints. | Allowed only through local `creative_spec_learning_rollup.py` and optional `task_bootstrap.py --creative-learning-hints`; no provider calls, agent execution, patch generation, routing authority, required-role changes, lifecycle-gate changes, PR/GitHub/Slack writes, semantic cache, graph truth, product runtime truth, or merge-readiness authority. |

PR-0 sets:

```text
gate_status=closed
authority_class=code-specification
candidate_patch_allowed=false
repository_write_allowed=false
promotion_allowed=false
```

PR-1 adds only a local specification-bundle layer. PR-2 opens only local
sandboxed candidate-patch generation/evaluation. PR-3 adds a separate
human-approved non-draft PR creation lane. PR-6 adds a local run-plan wrapper
for the first applied candidate without adding execution authority. The
private-pilot loop operator adds local lifecycle state, GitHub App read-only
capability gating, and checklist planning without adding candidate-generation
or repository-write authority. Product runtime, OpenAPI/client, semantic-cache,
review-thread, merge, release, and Slack/GitHub authority flags remain closed.
The PR creative-context layer adds bounded hypothesis/routing artifacts only;
active model/operator intake remains local and validated; auto-workflow
attachment remains a separate follow-up PR.
The approved-hypothesis bridge adds only local candidate/specification handoff
artifacts after human approval. The approval must bind to the exact source
hypothesis packet id, packet fingerprint, and selected hypothesis fingerprint;
approval targets outside the current `CreativeCodeCandidatePacket` mutable
allowlist become immutable oracles, and the bridge fails closed when no allowed
mutable target remains.

Premortem is part of this creative line, not a documentation closeout ritual.
For Experiment Runner creative-context work, premortem should forecast plausible
future failures from the perspective of users, business outcomes, project
development, security, and orchestration governance. That forecast must still
land on the actual diff: every PR-scoped finding needs a concrete affected
surface and closure through code, schema, validator, workflow guard,
deterministic test, policy guard, fail-closed behavior, or an explicit
`NOT-A-BUG` / `DEFERRED` disposition. Learning-loop feedback over both
recurring failure patterns and successful iteration patterns is proposal-only
until a reviewed repo diff promotes it into the smallest authoritative surface.
Every learning-loop record for this creative line must include bounded
proposal-only metrics for user-impact clarity, business-risk clarity,
project-development signal, repeat-failure reduction, and successful-pattern
reuse; these metrics must not write runtime telemetry, semantic cache, graph
truth, or product runtime truth.

---

## Closed Boundary

The only PR-0 handoff artifact is a valid `CreativeCodeCandidatePacket` under:

- `docs/orchestration/contracts/CREATIVE_CODE_CANDIDATE_CONTRACT.md`
- `docs/orchestration/contracts/creative_code_candidate.v1.schema.json`
- `docs/orchestration/contracts/creative_code_candidate.v1.json`

The PR-1 executable handoff artifact is a valid `CreativeCodeSpecificationBundle` under:

- `docs/orchestration/contracts/CREATIVE_CODE_SPECIFICATION_CONTRACT.md`
- `docs/orchestration/contracts/creative_code_specification.v1.schema.json`
- `docs/orchestration/contracts/creative_code_specification.v1.json`
- `scripts/orchestration/creative_code_specification.py`
- `scripts/orchestration/creative_code_spec_pipeline.py`
- `scripts/orchestration/creative_code_rejection_index.py`

The PR-2 local candidate-patch handoff artifacts are:

- `docs/orchestration/contracts/CREATIVE_CODE_PATCH_BUILDER_CONTRACT.md`
- `docs/orchestration/contracts/creative_code_patch_request.v1.schema.json`
- `docs/orchestration/contracts/creative_code_patch_result.v1.schema.json`
- `docs/orchestration/contracts/creative_code_patch_generation_gate.v1.schema.json`
- `docs/orchestration/contracts/creative_code_patch_generation_receipt.v1.schema.json`
- `scripts/orchestration/creative_code_patch_contract.py`
- `scripts/orchestration/creative_code_patch_workspace.py`
- `scripts/orchestration/creative_code_patch_executor.py`
- `scripts/orchestration/creative_code_patch_builder.py`
- `scripts/orchestration/creative_code_patch_generation.py`

The PR-3 human-approved non-draft PR promotion artifacts are:

- `docs/orchestration/contracts/CREATIVE_CODE_PR_PROMOTION_CONTRACT.md`
- `docs/orchestration/contracts/creative_code_pr_promotion_plan.v1.schema.json`
- `docs/orchestration/contracts/creative_code_pr_promotion_validation.v1.schema.json`
- `docs/orchestration/contracts/creative_code_pr_promotion_approval.v1.schema.json`
- `docs/orchestration/contracts/creative_code_pr_promotion_receipt.v1.schema.json`
- `scripts/orchestration/creative_code_pr_promotion_contract.py`
- `scripts/orchestration/creative_code_pr_promotion.py`

The PR-6 local applied-candidate run-plan artifacts are:

- `scripts/orchestration/creative_code_applied_candidate_pr6.py`
- `artifacts/orchestration/creative_code/applied_candidates/<candidate-id>/run_plan.json`
- `artifacts/orchestration/creative_code/applied_candidates/<candidate-id>/candidate_packet.json`

The private-pilot loop operator artifacts are:

- `docs/orchestration/contracts/CREATIVE_CODE_PRIVATE_PILOT_LOOP_OPERATOR_CONTRACT.md`
- `docs/orchestration/contracts/creative_code_private_pilot_state.v1.schema.json`
- `docs/orchestration/contracts/creative_code_private_pilot_candidate_plan.v1.schema.json`
- `docs/orchestration/contracts/github_app_private_pilot_capability_report.v1.schema.json`
- `scripts/orchestration/creative_code_private_pilot_loop_contract.py`
- `scripts/orchestration/creative_code_private_pilot_loop_operator.py`
- `scripts/orchestration/github_app_private_pilot_capability.py`
- `artifacts/orchestration/creative_code/private_pilot/<pr-number>/pilot_state.json`
- `artifacts/orchestration/creative_code/private_pilot/<pr-number>/candidate_plan.json`

The Experiment Runner PR creative-context artifacts are:

- `docs/orchestration/contracts/EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md`
- `docs/orchestration/contracts/experiment_runner_pr_oracle_attachment.v1.schema.json`
- `docs/orchestration/contracts/creative_protocol_context_map.v1.schema.json`
- `docs/orchestration/contracts/creative_hypothesis_operator_model_intake.v1.schema.json`
- `docs/orchestration/contracts/creative_hypothesis_packet.v1.schema.json`
- `docs/orchestration/contracts/creative_hypothesis_agent_routing.v1.schema.json`
- `docs/orchestration/contracts/creative_hypothesis_coordinator_dispatch.v1.schema.json`
- `docs/orchestration/contracts/creative_hypothesis_agent_consumption_summary.v1.schema.json`
- `docs/orchestration/contracts/creative_hypothesis_approval.v1.schema.json`
- `scripts/orchestration/experiment_runner_pr_creative_context_contract.py`
- `scripts/orchestration/experiment_runner_pr_creative_context.py`
- `artifacts/orchestration/experiments/creative_context/<context-id>/context_map.json`
- `artifacts/orchestration/experiments/creative_context/<context-id>/hypothesis_packet.json`
- `artifacts/orchestration/experiments/creative_context/<context-id>/agent_routing.json`
- `artifacts/orchestration/experiments/creative_context/<context-id>/coordinator_dispatch.json`
- `artifacts/orchestration/experiments/creative_context/<context-id>/oracle_attachment.json`
- `artifacts/orchestration/experiments/creative_context/<context-id>/agent_consumption_summary.json`

The approved creative-hypothesis specification bridge artifacts are:

- `docs/orchestration/contracts/creative_hypothesis_specification_bridge.v1.schema.json`
- `docs/orchestration/contracts/creative_hypothesis_spec_bridge_metrics.v1.schema.json`
- `scripts/orchestration/creative_hypothesis_spec_bridge_contract.py`
- `scripts/orchestration/creative_hypothesis_spec_bridge.py`
- `scripts/orchestration/creative_specification_skeptic_review_contract.py`
- `scripts/orchestration/creative_specification_skeptic_review.py`
- `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/creative_hypothesis_specification_bridge.json`
- `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/creative_code_candidate_packet.json`
- `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/bridge_metrics.json`
- `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/spec_prepare/source_packet.json`
- `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/spec_prepare/variants.json`
- `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/spec_prepare/skeptic_reviews.json`
- `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/spec_prepare/context_pack.json`
- `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/spec_finalize_reviewed/skeptic_review_attachment.json`
- `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/spec_finalize_reviewed/creative_code_specification_bundle.json`
- `artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/spec_finalize_reviewed/finalize_receipt.json`

The reviewed creative specification learning rollup artifacts are:

- `docs/orchestration/contracts/creative_spec_learning_rollup.v1.schema.json`
- `docs/orchestration/contracts/creative_spec_coordinator_advisory_hints.v1.schema.json`
- `scripts/orchestration/creative_spec_learning_rollup_contract.py`
- `scripts/orchestration/creative_spec_learning_rollup.py`
- `artifacts/orchestration/creative_code/learning_rollup/<rollup-id>/creative_spec_learning_rollup.json`
- `artifacts/orchestration/creative_code/learning_rollup/<rollup-id>/coordinator_advisory_hints.json`

The finalized creative specification patch-admission artifacts are:

- `docs/orchestration/contracts/CREATIVE_SPEC_PATCH_ADMISSION_CONTRACT.md`
- `docs/orchestration/contracts/creative_spec_patch_human_admission.v1.schema.json`
- `docs/orchestration/contracts/creative_spec_patch_admission.v1.schema.json`
- `scripts/orchestration/creative_spec_patch_admission_contract.py`
- `scripts/orchestration/creative_spec_patch_admission.py`
- `artifacts/orchestration/creative_code/patch_admission/<admission-id>/human_admission.json`
- `artifacts/orchestration/creative_code/patch_admission/<admission-id>/finalize_receipt.json`
- `artifacts/orchestration/creative_code/patch_admission/<admission-id>/source_bundle.json`
- `artifacts/orchestration/creative_code/patch_admission/<admission-id>/request.json`
- `artifacts/orchestration/creative_code/patch_admission/<admission-id>/creative_spec_patch_admission.json`

Bridge output directories must be exactly
`artifacts/orchestration/creative_code/spec_bridge/<bridge-id>/`; bridge refs,
candidate packets, metrics, and prepare directories must agree on that id.
Build-only artifacts may only allow `prepare_specification`; agent skeptic
review is the next action only after the four PR-1 prepare artifacts exist.

`request.json` in a patch-admission directory is a PR-2
`CreativeCodePatchBuildRequest` handoff artifact. It is built and validated only
after reviewed finalize evidence emits a selected
`spec_finalize_reviewed/creative_code_specification_bundle.json` plus a
`finalize_receipt.json` whose next allowed action is
`human_review_for_patch_builder`. The admission layer calls the existing PR-2
request builder, validates the request through the existing PR-2 request
validator, and keeps its own executed authority prepare-only with
`validate_patch_builder_request=true`.

`generation_gate.json` in a patch-generation directory is a PR-2 local
pre-generation control artifact. It may be emitted only after the admission
artifact is prepared, the prepared run state matches the request/source bundle,
the request base SHA still equals current local `origin/main`, the shared
worktree is clean, no candidate artifacts already exist, and any coordinator
advisory hints validate as non-authoritative. `generation_receipt.json` links
the gate, existing local `candidate.patch`, patch metadata, Experiment Runner
candidate packet, and PR-2 result metadata by repo-relative refs and
fingerprints only. It is local PR-2 candidate evaluation evidence, not
fixed-mapping evidence, review-thread disposition evidence, merge-readiness
evidence, product runtime truth, semantic-cache authority, Slack/GitHub
authority, or PR-3 promotion authority.

The packet, bundle, request, result, local `candidate.patch`, plan, validation,
approval, receipt, applied-candidate run plan, and generated PR body may
describe or contain an implementation candidate, but they are not:

- a repo-write instruction;
- merge-readiness evidence;
- review-thread disposition evidence;
- canonical product/runtime truth;
- provider, cache, OpenAPI, frontend, iOS, DB, Slack, or GitHub App authority.

---

## Mandatory PR-0 Invariants

Every valid creative-code candidate packet must:

- originate from promoted `creative_research` output with `promotion_decision=promote`;
- keep `gate_status=closed`;
- keep `variant_count` between 3 and 5;
- require sandboxed evaluation and human review;
- provide repo-relative `target_surface` and `immutable_oracles` paths;
- reject absolute paths, parent traversal, URL/scheme paths, control characters, local artifact paths, and path overlap between mutable target surfaces and immutable oracles;
- reuse the existing `validate_mutable_candidate_surface(...)` allowlist for
  target surfaces, then reject protected governance, review, security,
  compliance, legal, test, CI, AGENTS, and release surfaces;
- keep all repository-write, provider, runtime, semantic-cache, PR, review-thread, merge, release, and Slack/GitHub expansion authority flags fail-closed;
- treat scientific-style output as hypothesis or evidence-supported planning only, not verified discovery, unless a separate reviewed evidence result is promoted in a future PR.

---

## Future PR Train

PR-0 is a contract-only start point.

- PR-0: closed authority contract, schema, reference packet, validator, and tests.
- PR-1: emit deterministic implementation specification bundles from promoted
  creative research; no patches, provider calls, repo writes, runtime truth,
  review disposition authority, or merge-readiness evidence.
- Approved-hypothesis specification bridge: consume human-approved
  `CreativeHypothesisApproval` artifacts that bind to the current source packet
  and selected hypothesis fingerprints, then emit a validated
  `CreativeCodeCandidatePacket`, deterministic local bridge metrics, and
  existing PR-1 prepare artifacts; no agent execution, finalize, candidate
  patches, provider calls, workflow changes, repository writes, product runtime
  truth, semantic cache, graph truth, or mutable-surface widening.
- Reviewed bridge finalize evidence attachment: attach sanitized local
  skeptic-review evidence in sibling `spec_finalize_reviewed/`, run the
  existing PR-1 `finalize`, emit metadata-only attachment/receipt counts, and
  preserve `spec_prepare/`; no agent execution, patches, branch/PR writes,
  provider calls, workflows, product runtime truth, semantic cache, graph truth,
  fixed-mapping edits, review-thread actions, or readiness claims.
- Creative spec learning rollup: ingest finalized creative spec outcomes into
  proposal-only `agent_learning_record.v1` success/failure records and
  coordinator advisory hints; optional task bootstrap packet visibility may
  expose hint fingerprints and reviewer-focus lesson ids only, without changing
  routing, role order, required gates, agent execution, patch generation,
  semantic cache, graph truth, product runtime truth, PR/GitHub/Slack writes,
  or merge-readiness authority.
- Creative spec patch admission: admit a finalized selected creative spec to a
  valid PR-2 `CreativeCodePatchBuildRequest` and optionally run builder
  `prepare` only, proving `request.json`, `source_bundle.json`,
  `selected_variant.json`, and `state.json` exist while `candidate.patch` and
  `result.json` remain absent; no `generate`, `evaluate`, Codex exec,
  promotion, branch/PR writes, workflow changes, product runtime truth,
  semantic cache, graph truth, fixed-mapping edits, review-thread actions, or
  readiness claims.
- PR-2: generate isolated candidate patches only in sandboxed evaluation
  workspaces with exact source-bundle fingerprint binding, exact `origin/main`
  base SHA, fixed Codex CLI argv/env, strict patch policy validation, direct
  Experiment Runner candidate-mode evaluation, and sanitized result metadata.
- PR-3: allow human-approved non-draft PR creation from one accepted PR-2 patch
  under a separate plan -> validation -> approval -> receipt contract.
- PR-4: add local candidate evaluation telemetry and rejection taxonomy over
  sanitized PR-1/PR-2/PR-3 artifacts; no public GitHub App backend, Slack beta,
  live review ingestion, or new authority.
- PR-5: add local review-disposition integration through
  `CreativeCodeReviewFeedbackRecord` -> `CreativeCodeReviewDispositionPacket`
  -> `CreativeCodeRepairLaunchPacket`; no review-thread resolution,
  fixed-mapping edits, GitHub mutation, patch generation, branch writes, PR
  creation, merge authority, or readiness claims.
- PR-6: run the first governed applied creative-code candidate through normal PR
  governance, starting from a local wrapper that validates the PR-5 launch
  packet, binds the target surface to `docs/prompts/cv/program.md`, and emits a
  deterministic PR-1 / PR-2 / PR-3 / PR-4 run plan before the generated
  candidate is restricted to that prompt/program document.
- Private-pilot loop operator: collect sanitized PR/check/review state and
  PR-4 / PR-5 / PR-6 artifact refs, consume an optional sanitized GitHub App
  private-pilot capability report, decide the next action, and optionally emit
  a checklist-only candidate plan. It cannot execute candidate generation,
  branch/PR operations, fixed-mapping edits, thread resolution, provider/runtime
  calls, token minting, GitHub App settings changes, or Slack/GitHub writes.
- PR creative-context attachment: collect sanitized PR surface refs, emit a
  `CreativeProtocolContextMap`, generate a `CreativeHypothesisPacket`, emit
  `CreativeHypothesisAgentRouting`, and summarize the next allowed action for
  role agents. It cannot generate candidate patches, mutate code, change
  workflows, call providers, call product runtime, create branches, open PRs,
  post comments, resolve threads, edit fixed mappings, merge, or claim
  readiness.
- Bridge follow-ups remain separate reviewed PRs: the reviewed-spec learning
  rollup ingests finalized bridge/finalize outcomes into the existing
  proposal-only learning loop, while graph/multimodal lineage remains deferred
  until repo-reviewed evidence contracts define asset lineage, fingerprints,
  idempotency, and replay/admission behavior.

Minimum future telemetry fields are defined now for the later train and must not be emitted before PR-1:

- `packet_id`
- `source_candidate_id`
- `variant_count`
- `generation_status`
- `oracle_status`
- `failure_class`
- `human_decision`
- `cost_metadata_available`

PR-4 telemetry artifacts are defined by:

- `docs/orchestration/contracts/CREATIVE_CODE_TELEMETRY_CONTRACT.md`
- `docs/orchestration/contracts/creative_code_telemetry_event.v1.schema.json`
- `docs/orchestration/contracts/creative_code_telemetry_rollup.v1.schema.json`
- `docs/orchestration/contracts/creative_code_rejection_taxonomy.v1.schema.json`
- `docs/orchestration/contracts/creative_code_rejection_taxonomy.v1.json`
- `scripts/orchestration/creative_code_telemetry_contract.py`
- `scripts/orchestration/creative_code_telemetry.py`

PR-4 rollups are advisory local measurements only. They are not routing truth,
review-thread disposition evidence, fixed-mapping evidence, merge-readiness
evidence, product runtime truth, or release evidence.

PR-5 review-disposition artifacts are defined by:

- `CreativeCodeReviewFeedbackCollection` local collection output, validated by
  `validate_creative_code_review_feedback_collection(...)`.
- `docs/orchestration/contracts/CREATIVE_CODE_REVIEW_DISPOSITION_CONTRACT.md`
- `docs/orchestration/CREATIVE_CODE_REVIEW_DISPOSITION_PR5_PREMORTEM.md`
- `docs/orchestration/contracts/creative_code_review_feedback_record.v1.schema.json`
- `docs/orchestration/contracts/creative_code_review_disposition_packet.v1.schema.json`
- `docs/orchestration/contracts/creative_code_repair_launch_packet.v1.schema.json`
- `scripts/orchestration/creative_code_review_disposition_contract.py`
- `scripts/orchestration/creative_code_review_disposition.py`

PR-5 packets are advisory local classification output only. They are not
review-thread disposition evidence, fixed-mapping evidence, merge-readiness
evidence, runtime truth, release evidence, or GitHub write authority. The only
positive launch authority is `create_pr1_specification=true`; patch generation,
branch writes, PR creation, review-thread resolution, fixed-mapping edits, and
merge authority remain false.

PR-6 applied-candidate run plans are local operator handoff artifacts only. They
are not patch generation authority, PR promotion authority, review-thread
disposition evidence, fixed-mapping evidence, merge-readiness evidence, runtime
truth, release evidence, or GitHub App/Slack authority. The first generated
candidate target surface is exactly `docs/prompts/cv/program.md`; scripts,
tests, review docs, governance docs, workflows, product runtime, OpenAPI,
frontend, iOS, DB, provider settings, and semantic-cache surfaces remain
outside generated candidate mutation authority.

Private-pilot loop state and candidate plans are local lifecycle artifacts only.
They may classify the next action as `wait_for_hotfix_main`, `wait_for_review`,
`wait_for_ci`, `fix_current_pr`, `prepare_next_candidate_plan`,
`hold_for_governance`, or `hold_for_security`, but they are not review-thread
disposition evidence, fixed-mapping evidence, readiness evidence, runtime truth,
release evidence, or GitHub App/Slack authority. The GitHub App capability
section is read-only capability evidence only: Pull requests read and Checks
read gate private-pilot read access, while Actions write is optional and
modeled solely as fixed workflow-dispatch capability. Candidate plans are
checklist-only and remain bound to `docs/prompts/cv/program.md`.

This capability gate does not automatically launch Experiment Runner in every
PR lane. Automatic PR-lane attachment is a separate follow-up contract: a
coordinator/packet hook may attach oracle-only Experiment Runner evidence and
make role agents consume the resulting decisions, but only after a reviewed PR
defines trigger rules, artifact reuse, failure behavior, co-author attribution,
rate/quota boundaries, opt-out behavior, and PR-body evidence requirements.

The PR creative-context layer also does not automatically launch on GitHub
Actions in v1. It provides the local sanitized artifact and contract surface
that a later auto-attach PR may consume after workflow trigger, permission, and
artifact-retention rules are reviewed. GitHub App initiated
`workflow_dispatch` and Actions write remain deferred capability-gate work; the
current model/hypothesis lane runs on the developer/operator's local machine and
requires the operator to choose any local model/API tool outside repo authority.

---

## Rollback

Rollback is removal of the private-pilot operator files, PR-6
applied-candidate wrapper, Experiment Runner PR creative-context files, their
tests, and local ignored artifacts. If
reverting the whole train, also remove the PR-5 review-disposition files, PR-4
telemetry files, PR-3 promotion files, PR-2 patch-builder files, and existing
PR-1/PR-0 contract files. Because these layers add no product runtime behavior,
providers, workflows, external app settings, OpenAPI/client changes,
semantic-cache activation, Slack/GitHub App changes, or DB state, rollback does
not require data migration, OpenAPI regeneration, external app changes, or
release coordination. Any already opened promoted candidate PR remains normal
GitHub state and is closed or branch-deleted manually if needed.
