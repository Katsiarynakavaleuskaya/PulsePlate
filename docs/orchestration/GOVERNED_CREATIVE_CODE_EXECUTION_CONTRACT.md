# Governed Creative-Code Execution Contract

<!-- markdownlint-disable MD013 -->

**Status:** PR-6 first applied-candidate lane plus local private-pilot loop
operator. Repo-only governance contract. No runtime impact.

**Scope:** Define the authority boundary between a promoted `creative_research`
output, a PR-1 implementation specification, PR-2 local candidate-patch
generation, PR-3 human-approved non-draft PR handoff tooling, PR-4 telemetry,
PR-5 read-only review-disposition integration, the PR-6 local
applied-candidate run-plan wrapper, and a local private-pilot lifecycle
operator. PR-2
authorizes only isolated local candidate-patch generation/evaluation. PR-3
authorizes only the separate local promotion tool that can create a new
`experiment/*` branch, push it without force, and open a non-draft PR after
isolated validation and explicit TTY approval. PR-5 may read sanitized review
context or explicit read-only fixtures and emit local advisory disposition /
repair-launch packets. PR-6 may validate a PR-5 repair launch packet, bind the
first applied candidate target to `docs/prompts/cv/program.md`, and emit a
local PR-1 / PR-2 / PR-3 / PR-4 run plan. The private-pilot operator may read
sanitized metadata and refs and emit next-action artifacts only. It does not
authorize draft PRs, shared worktree mutation, existing branch modification,
review-thread resolution, fixed-mapping edits, merge, release, product runtime
AI, OpenAPI/client changes, public multi-tenant use, or Slack/GitHub authority
expansion.

---

## Authority Classes

| Class | Authority | Current State |
|---|---|---|
| `research` | Produces hypotheses, scorecards, falsifiers, and promote/defer/discard decisions inside `creative_research`. | Existing governed source only. |
| `code-specification` | Converts a promoted research output into a typed future implementation specification. | Allowed as the closed PR-0 `CreativeCodeCandidatePacket` plus PR-1 `CreativeCodeSpecificationBundle`. |
| `candidate-patch` | Produces isolated candidate patches for local evaluation. | Allowed only through PR-2 `CreativeCodePatchBuildRequest` and `CreativeCodePatchResult` artifacts in sandboxed workspaces. |
| `repository-write` | Writes to shared worktrees, creates branches, pushes, opens PRs, marks ready for review, resolves review threads, or merges. | Forbidden except the PR-3 promoter's narrowly validated new `experiment/*` branch push and non-draft PR creation. |
| `promotion` | Promotes a candidate into canonical repo behavior through human review, PR governance, and merge gates. | PR-3 opens the review handoff only. Canonical behavior still requires normal PR review and merge gates. |
| `private-pilot-lifecycle` | Reads sanitized lifecycle metadata and emits local next-action artifacts. | Allowed only through the private-pilot loop operator; no candidate generation or GitHub write authority. |

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
private-pilot loop operator adds local lifecycle state and checklist planning
without adding candidate-generation or repository-write authority. Product
runtime, OpenAPI/client, semantic-cache, review-thread, merge, release, and
Slack/GitHub authority flags remain closed.

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
- `scripts/orchestration/creative_code_patch_contract.py`
- `scripts/orchestration/creative_code_patch_workspace.py`
- `scripts/orchestration/creative_code_patch_executor.py`
- `scripts/orchestration/creative_code_patch_builder.py`

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
- `scripts/orchestration/creative_code_private_pilot_loop_contract.py`
- `scripts/orchestration/creative_code_private_pilot_loop_operator.py`
- `artifacts/orchestration/creative_code/private_pilot/<pr-number>/pilot_state.json`
- `artifacts/orchestration/creative_code/private_pilot/<pr-number>/candidate_plan.json`

`patch_request.json` remains a PR-2 `CreativeCodePatchBuildRequest` handoff
artifact. It is built and validated only after PR-1 emits
`spec_runs/<candidate-id>/bundle.json`, because its identity and fingerprint are
bound to that canonical specification bundle.

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
  PR-4 / PR-5 / PR-6 artifact refs, decide the next action, and optionally emit
  a checklist-only candidate plan. It cannot execute candidate generation,
  branch/PR operations, fixed-mapping edits, thread resolution, provider/runtime
  calls, or Slack/GitHub App changes.

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
They may classify the next action as wait/fix/hold/prepare, but they are not
review-thread disposition evidence, fixed-mapping evidence, readiness evidence,
runtime truth, release evidence, or GitHub App/Slack authority. Candidate plans
are checklist-only and remain bound to `docs/prompts/cv/program.md`.

---

## Rollback

Rollback is removal of the private-pilot operator files, PR-6
applied-candidate wrapper, their tests, and local ignored artifacts. If
reverting the whole train, also remove the PR-5 review-disposition files, PR-4
telemetry files, PR-3 promotion files, PR-2 patch-builder files, and existing
PR-1/PR-0 contract files. Because these layers add no product runtime behavior,
providers, workflows, external app settings, OpenAPI/client changes,
semantic-cache activation, Slack/GitHub App changes, or DB state, rollback does
not require data migration, OpenAPI regeneration, external app changes, or
release coordination. Any already opened promoted candidate PR remains normal
GitHub state and is closed or branch-deleted manually if needed.
