# Governed Creative-Code Execution Contract

<!-- markdownlint-disable MD013 -->

**Status:** PR-3 human-approved non-draft PR promotion tooling. Repo-only governance contract. No runtime impact.

**Scope:** Define the authority boundary between a promoted `creative_research`
output, a PR-1 implementation specification, PR-2 local candidate-patch
generation, and PR-3 human-approved non-draft PR handoff tooling. PR-2
authorizes only isolated local candidate-patch generation/evaluation. PR-3
authorizes only the separate local promotion tool that can create a new
`experiment/*` branch, push it without force, and open a non-draft PR after
isolated validation and explicit TTY approval. It does not authorize draft PRs,
shared worktree mutation, existing branch modification, review-thread
resolution, merge, release, product runtime AI, OpenAPI/client changes, public
multi-tenant use, or Slack/GitHub authority expansion.

---

## Authority Classes

| Class | Authority | Current State |
|---|---|---|
| `research` | Produces hypotheses, scorecards, falsifiers, and promote/defer/discard decisions inside `creative_research`. | Existing governed source only. |
| `code-specification` | Converts a promoted research output into a typed future implementation specification. | Allowed as the closed PR-0 `CreativeCodeCandidatePacket` plus PR-1 `CreativeCodeSpecificationBundle`. |
| `candidate-patch` | Produces isolated candidate patches for local evaluation. | Allowed only through PR-2 `CreativeCodePatchBuildRequest` and `CreativeCodePatchResult` artifacts in sandboxed workspaces. |
| `repository-write` | Writes to shared worktrees, creates branches, pushes, opens PRs, marks ready for review, resolves review threads, or merges. | Forbidden except the PR-3 promoter's narrowly validated new `experiment/*` branch push and non-draft PR creation. |
| `promotion` | Promotes a candidate into canonical repo behavior through human review, PR governance, and merge gates. | PR-3 opens the review handoff only. Canonical behavior still requires normal PR review and merge gates. |

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
human-approved non-draft PR creation lane. Product runtime, OpenAPI/client,
semantic-cache, review-thread, merge, release, and Slack/GitHub authority flags
remain closed.

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

The packet, bundle, request, result, local `candidate.patch`, plan, validation,
approval, receipt, and generated PR body may describe or contain an
implementation candidate, but they are not:

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
- PR-5: add review-disposition integration without review-thread resolution authority.
- PR-6: run the first governed applied creative-code candidate through normal PR governance.

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

---

## Rollback

Rollback is removal of the PR-3 promotion files and references. If reverting the
whole train, also remove the PR-2 patch-builder files and existing PR-1/PR-0
contract files. Because PR-3 adds no product runtime behavior, providers,
workflows, external app settings, OpenAPI/client changes, semantic-cache
activation, Slack/GitHub App changes, or DB state, rollback does not require
data migration, OpenAPI regeneration, external app changes, or release
coordination. Any already opened promoted candidate PR remains normal GitHub
state and is closed or branch-deleted manually if needed.
