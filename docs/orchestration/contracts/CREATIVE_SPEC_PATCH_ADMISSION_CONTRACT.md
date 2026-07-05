# Creative Spec Patch Admission Contract

Status: active local control-plane contract.

This contract admits an already finalized creative-code specification bundle to
the existing PR-2 `CreativeCodePatchBuildRequest` shape and optionally proves
that patch-builder `prepare` can create its isolated checkout artifacts.

It does not generate a patch, evaluate a candidate, call Codex, promote a
candidate, write a branch, open or edit a PR, resolve review threads, edit fixed
mapping, change workflows, call product runtime, use semantic cache, or write
graph truth.

## Inputs

The admission CLI reads only sanitized local JSON artifacts:

- `spec_finalize_reviewed/finalize_receipt.json`
- `spec_finalize_reviewed/creative_code_specification_bundle.json`
- `creative_spec_patch_human_admission.v1` operator approval

The finalize receipt must have:

- `synthesis_status == selected`
- `next_allowed_action == human_review_for_patch_builder`
- `counts.selected_variant_count == 1`
- a `bundle_id`, `bundle_fingerprint`, and selected variant binding that match
  the supplied bundle

The human admission must bind:

- bundle id and fingerprint
- selected variant id and fingerprint
- non-empty oracle commands
- non-empty metrics
- bounded PR-2 budgets
- explicit prepare-only authority

## Outputs

`creative_spec_patch_admission.py build-request` writes a local admission
directory under:

`artifacts/orchestration/creative_code/patch_admission/<operator-run-id>/`

The directory contains:

- `creative_spec_patch_admission.json`
- `human_admission.json`
- `finalize_receipt.json`
- `source_bundle.json`
- `request.json`

`request.json` is a normal PR-2 `CreativeCodePatchBuildRequest` built by
`build_creative_code_patch_build_request(...)` and then validated by
`validate_creative_code_patch_build_request(...)`. This admission layer does not
duplicate the PR-2 request contract logic.

`creative_spec_patch_admission.json` records prepare-only executed effects. It
intentionally separates this admission authority from the PR-2 request
authority. The request remains a valid PR-2 builder request; this CLI only
executes build, validate, summarize, and builder `prepare`.

## Prepare Proof

`creative_spec_patch_admission.py prepare-builder` calls only
`creative_code_patch_builder.prepare(...)`. It writes the existing builder
prepare artifacts under `patch_runs/<run-id>/`:

- `request.json`
- `source_bundle.json`
- `selected_variant.json`
- `state.json`

The admission summary must prove:

- `candidate.patch` is absent
- `result.json` is absent
- `candidate_patch_generated == false`
- `candidate_patch_evaluated == false`
- no Codex exec, provider call, product runtime call, semantic-cache write,
  graph-truth write, branch write, PR write, review-thread action, fixed-mapping
  edit, or merge-readiness claim occurred

## CLI

Commands:

- `build-request`
- `validate`
- `prepare-builder`
- `build-and-prepare`
- `summarize`

`build-request`, `prepare-builder`, and `build-and-prepare` require the shared
worktree to be clean and `base_sha` to match current `origin/main`.

`validate` and `summarize` re-check the admission bindings and current
`origin/main` base SHA before reporting success.

## Authority

True authority is limited to:

- read finalized creative specs
- approve/build a patch-builder request
- validate the request
- run builder `prepare`
- emit local artifacts

False authority includes:

- `run_patch_builder_generate`
- `run_patch_builder_evaluate`
- `generate_candidate_patch`
- `call_local_codex_exec`
- `call_provider`
- `call_product_runtime`
- `write_repository`
- `write_shared_worktree`
- `create_branch`
- `push_branch`
- `open_pull_request`
- `resolve_review_threads`
- `edit_fixed_mapping`
- `claim_merge_readiness`
- `merge`
- `modify_workflows`
- `use_semantic_cache`
- `write_graph_truth`
- `read_secrets`

## Schemas And Validators

Tracked contract surfaces:

- `docs/orchestration/contracts/creative_spec_patch_human_admission.v1.schema.json`
- `docs/orchestration/contracts/creative_spec_patch_admission.v1.schema.json`
- `scripts/orchestration/creative_spec_patch_admission_contract.py`
- `scripts/orchestration/creative_spec_patch_admission.py`

Regression surface:

- `tests/test_creative_spec_patch_admission.py`
- `tests/test_creative_code_patch_builder.py`
- `tests/test_creative_code_specification.py`
- `tests/test_creative_specification_skeptic_review.py`
- `tests/test_creative_hypothesis_spec_bridge.py`
- `tests/test_creative_spec_learning_rollup.py`
- `tests/test_task_bootstrap.py`
