# PR-2 Sandboxed Creative-Code Patch Builder Premortem

Mode: `pr-premortem`

Packet: `artifacts/orchestration/task_packets/904282be7567.json`

Branch: `codex/creative-code-sandboxed-patch-builder-pr2`

Frame: It is 6 months from now. The PR-2 sandboxed creative-code patch builder
failed. We are looking backward to understand why.

## Summary

PR-2 adds a local control-plane builder that can create and evaluate isolated
candidate patches from a validated PR-1 `CreativeCodeSpecificationBundle`.

The failure frame is an authority and isolation failure: a local candidate patch
path accidentally becomes shared repo-write, PR automation, promotion evidence,
runtime AI behavior, or a raw-output leakage surface.

## Findings

### Finding 1: Candidate Patch Authority Expands Into Repo Or PR Authority

Failure story: A later operator treats `CreativeCodePatchBuildRequest` as
permission to create a branch, push, open a pull request, resolve review
threads, or promote a generated candidate because the builder produced a patch
and a runner result. The PR-2 artifact then becomes misleading fixed-mapping or
merge-readiness evidence instead of local evaluation evidence.

Underlying assumption: The local builder boundary will be obvious from context.

Early warning signs:

- Result artifacts contain PR, review-thread, promotion, or merge-ready fields.
- Docs describe `candidate.patch` as review disposition or merge evidence.

Containment action: Keep authority fields explicit and fail-closed; document
that PR-2 artifacts are local-only evidence and never fixed-mapping,
review-thread, merge, or promotion authority.

Disposition: FIXED

Evidence:

- `scripts/orchestration/creative_code_patch_contract.py`
- `docs/orchestration/contracts/CREATIVE_CODE_PATCH_BUILDER_CONTRACT.md`
- `scripts/AGENTS.md`
- `tests/test_creative_code_patch_builder.py::test_reference_patch_contracts_validate_and_schema_is_closed`
- `tests/test_creative_code_patch_builder.py::test_cli_prepare_generate_evaluate_cleanup`

### Finding 2: Codex Execution Leaks Secrets Or Persists Raw Provider Output

Failure story: The wrapper forwards parent shell credentials, persists raw Codex
JSON events, or writes the prompt into artifacts. A local failure output then
contains tokens, absolute paths, raw prompts, or model/provider payloads that
later get copied into review artifacts.

Underlying assumption: Local-only execution makes raw output persistence safe.

Early warning signs:

- Executor code forwards `GH_TOKEN`, `OPENAI_API_KEY`, `CODEX_HOME`, or `GIT_*`.
- Result files contain patch text, prompt text, oracle stdout/stderr, or local
  absolute paths.

Containment action: Use a fixed `codex exec` argv, pass prompt only through
stdin, strip credential-shaped env, and store only counts/fingerprints in
sanitized metadata.

Disposition: FIXED

Evidence:

- `scripts/orchestration/creative_code_patch_executor.py`
- `scripts/orchestration/creative_code_patch_contract.py`
- `tests/test_creative_code_patch_builder.py::test_executor_builds_fixed_argv_and_strips_secret_env`
- `tests/test_creative_code_patch_builder.py::test_evaluate_writes_sanitized_result_without_runner_leaks`

### Finding 3: The Generation Checkout Mutates Or Trusts The Shared Worktree

Failure story: The builder generates inside the active PR worktree, retains a
remote, checks out a moving branch instead of an exact base SHA, or leaves an
interrupted checkout behind. A generated change is then confused with human
authored repo changes, or a later cleanup command deletes outside the artifact
root.

Underlying assumption: A local checkout path is isolated enough.

Early warning signs:

- Generation uses a branch name rather than a 40-character SHA.
- `origin` remains configured inside the generation checkout.
- Cleanup accepts traversal or symlinked run directories.

Containment action: Require exact `origin/main` SHA binding, clone with
`--no-hardlinks`, detach at the exact base, remove `origin`, verify clean state,
and destroy the generation checkout in `finally` with containment checks.

Disposition: FIXED

Evidence:

- `scripts/orchestration/creative_code_patch_workspace.py`
- `scripts/orchestration/creative_code_patch_builder.py`
- `tests/test_creative_code_patch_builder.py::test_workspace_creates_detached_no_remote_checkout_and_cleanup`
- `tests/test_creative_code_patch_builder.py::test_cli_prepare_generate_evaluate_cleanup`

### Finding 4: Patch Policy Allows A Dangerous False Negative

Failure story: A candidate patch looks small in `git diff --name-only`, but it
actually deletes a file, renames a guarded surface, adds a symlink, modifies an
immutable oracle, includes binary content, touches tests/governance/OpenAPI/iOS
surfaces, or is a no-op. The runner evaluates the wrong thing and the PR-2
result looks safer than it is.

Underlying assumption: Git name-only output is enough to validate a patch.

Early warning signs:

- Validation ignores untracked files, mode changes, numstat binary markers, or
  `git apply --check`.
- Allowed paths are not re-bound to the selected PR-1 variant and immutable
  oracles.

Containment action: Validate status, name-status with no renames, numstat, raw
diff modes, `git diff --check`, clean `git apply --check`, allowed path
surfaces, immutable oracle overlap, file count, diff line, and patch byte
budgets.

Disposition: FIXED

Evidence:

- `scripts/orchestration/creative_code_patch_builder.py`
- `scripts/orchestration/creative_code_patch_contract.py`
- `tests/test_creative_code_patch_builder.py::test_patch_metadata_accepts_allowed_modified_file`
- `tests/test_creative_code_patch_builder.py::test_patch_metadata_rejects_unapproved_untracked_file`
- `tests/test_creative_code_patch_builder.py::test_patch_metadata_rejects_symlink_mode_change`

### Finding 5: Runner Evaluation Is Treated As PR Governance Evidence

Failure story: PR-2 `evaluate` calls Experiment Runner in candidate-patch mode,
and someone later reuses that result as the mandatory PR oracle-only governance
review or as a CodeRabbit/fixed-mapping substitute. The PR then bypasses the
separate pre-open oracle-only evidence and post-open review lane.

Underlying assumption: All Experiment Runner artifacts have the same PR
governance meaning.

Early warning signs:

- PR body cites `CreativeCodePatchResult` as the mandatory oracle-only evidence.
- Candidate-patch runner result appears in fixed mapping as a resolved review
  proof.

Containment action: Keep PR-2 builder evaluation local-only and document that
the mandatory PR oracle-only governance evidence remains a separate
`oracle_only_governance_reviewer` run against the actual PR diff.

Disposition: FIXED

Evidence:

- `scripts/AGENTS.md`
- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
- `docs/orchestration/contracts/CREATIVE_CODE_PATCH_BUILDER_CONTRACT.md`
- `tests/test_creative_code_patch_builder.py::test_evaluate_writes_sanitized_result_without_runner_leaks`

### Finding 6: Local Gates Report A False Green Before New Files Are Tracked

Failure story: `make validate-changed` runs before the new Python files are in
`HEAD`, so the branch-diff selector reports no changed Python files. The PR body
then claims branch-scoped validation even though the new builder modules were
tested only by focused ad hoc pytest.

Underlying assumption: Any zero exit from `make validate-changed` is sufficient
without checking what it selected.

Early warning signs:

- `make validate-changed` prints `No Python or cross-surface governance files`.
- New Python files remain untracked when branch-diff validation runs.

Containment action: Treat the early `validate-changed` result as
non-sufficient, keep focused pytest as the current proof, and rerun
`make validate-changed` after the PR-2 files are committed so the selector sees
the tracked branch diff.

Disposition: FIXED

Evidence:

- `tests/test_creative_code_patch_builder.py`
- Local focused pytest: `tests/test_creative_code_patch_builder.py`
- Local regression pytest: `tests/test_creative_code_patch_builder.py tests/test_creative_code_specification.py tests/test_experiment_bootstrap.py tests/test_experiment_runner.py tests/test_codex_ollama_operator_doctor.py tests/guards/test_subprocess_uses_absolute_binaries.py tests/guards/test_nosec_policy_guard.py tests/test_repo_policy_guards.py`
- Required follow-up gate before push: rerun `make validate-changed` after commit.

## Synthesis

Most likely failure: a false-positive validation story, especially confusing
candidate-patch Runner evaluation with mandatory PR oracle-only governance
evidence.

Most dangerous failure: authority drift from local candidate-patch generation
into repo-write, review-thread, PR, or promotion automation.

Hidden assumption: local-only artifacts are safe unless their authority and
sanitization boundaries are repeatedly enforced by contracts, docs, tests, and
PR body wording.

## Revised Plan

- Keep PR-2 result authority explicit and false for repo, PR, review-thread,
  merge, and promotion actions.
- Keep raw patch text local-only as `candidate.patch`; sanitized results store
  counts and fingerprints only.
- Run and document the mandatory PR oracle-only Experiment Runner evidence as a
  separate governance artifact from builder candidate-patch evaluation.
- Repeat `make validate-changed` after commit so branch-diff selection covers
  the new tracked Python files.

## Pre-Merge Checklist

- [ ] Focused PR-2 builder tests pass.
- [ ] Regression runner/spec/guard tests pass.
- [ ] `make validate-changed` is rerun after the files are committed.
- [ ] `pre-commit run --all-files` passes.
- [ ] Oracle-only Experiment Runner evidence is accepted for the actual PR diff.
- [ ] PR body and fixed mapping document the full `make verify` deferral.
- [ ] Post-open role lane and review-thread disposition gates complete.

## Decision

`proceed with changes` - the scope is valid after the implemented authority,
workspace, executor, patch-policy, runner-sanitization, and validation-selection
guards remain in place.
