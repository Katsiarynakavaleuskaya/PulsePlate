# PR-1 Creative-Code Specification Pipeline Premortem

Mode: `pr-premortem`

Packet: `artifacts/orchestration/task_packets/6bb7ee0c5548.json`

Branch: `codex/creative-code-specification-pr1`

Frame: It is 6 months from now. The PR-1 creative-code specification pipeline
failed. We are looking backward to understand why.

## Summary

PR-1 adds a local control-plane pipeline that converts a validated PR-0
`CreativeCodeCandidatePacket` into deterministic implementation specifications,
skeptic reviews, synthesis, telemetry summary, and a fingerprint-only rejection
index.

The failure frame is a governance/control-plane failure: the PR accidentally
widens creative-code authority into patches, provider calls, repo writes,
runtime truth, or misleading merge/review evidence.

## Findings

### Finding 1: Specification Output Becomes Patch Or Repo-Write Authority

Failure story: A later lane treats `CreativeCodeSpecificationBundle` as an
implicit approval to generate candidate patches or open a PR because the bundle
contains target paths, implementation steps, and a selected variant. Reviewers
then cite the bundle as implementation or merge evidence instead of a
human-review planning artifact.

Underlying assumption: Readers will infer the boundary from PR-0 docs alone.

Early warning signs:

- Bundle fields mention patch, PR, merge readiness, provider calls, or runtime
  behavior.
- PR body uses the bundle as fixed-mapping or review-thread disposition proof.

Containment action: Keep authority flags fail-closed, reject unsafe authority
text, and document that the bundle is not review or merge evidence.

Disposition: FIXED

Evidence:

- `scripts/orchestration/creative_code_specification.py`
- `docs/orchestration/contracts/CREATIVE_CODE_SPECIFICATION_CONTRACT.md`
- `tests/test_creative_code_specification.py::test_authority_flags_fail_closed`
- `tests/test_creative_code_specification.py::test_unsafe_variant_text_is_rejected`

### Finding 2: Local CLI Leaks Or Writes Outside The Artifact Boundary

Failure story: The `prepare` or `finalize` command accepts a symlinked artifact
directory or absolute output path. A local run writes outside
`artifacts/orchestration/creative_code`, reads a secret-adjacent path, or leaves
a partial JSON bundle that a later step mistakes for valid evidence.

Underlying assumption: Repo-relative validation is enough for local artifact
I/O.

Early warning signs:

- CLI code uses only lexical path checks.
- Failed finalize leaves a partially written bundle.

Containment action: Resolve paths under the repo/artifact root, reject symlink
components, and write JSON by same-directory atomic replace.

Disposition: FIXED

Evidence:

- `scripts/orchestration/creative_code_spec_pipeline.py`
- `tests/test_creative_code_specification.py::test_pipeline_rejects_symlinked_artifact_directory`
- `tests/test_creative_code_specification.py::test_pipeline_prepare_and_finalize_write_valid_bundle`

### Finding 3: Rejected Variants Store Raw Prompt, Secret, Or Candidate Text

Failure story: The rejection index becomes a convenient audit log and starts
capturing rejected candidate prose, raw prompts, provider payloads, local paths,
or secret-shaped strings. That makes the local control plane unsafe to share or
attach to review artifacts.

Underlying assumption: Rejections need raw detail to be useful.

Early warning signs:

- Rejection records include prose fields beyond reason codes and fingerprints.
- Tests assert only that rejection records exist, not that raw content is absent.

Containment action: Make the rejection index fingerprint-only and test that raw
prompt, patch, provider payload, secret, and local-path strings are absent.

Disposition: FIXED

Evidence:

- `scripts/orchestration/creative_code_rejection_index.py`
- `tests/test_creative_code_specification.py::test_rejection_index_is_fingerprint_only`
- `tests/test_creative_code_specification.py::test_rejection_index_duplicate_keys_fail_closed`

### Finding 4: Synthesis Selects A Rejected, Duplicate, Or Unreviewed Variant

Failure story: The bundle contains multiple variants and some skeptic reviews,
but the synthesis code accepts a selected variant that has a rejection, duplicate
fingerprint, missing reviewer, or revised status. A later operator trusts the
selection and starts PR-2 from a weak spec.

Underlying assumption: Selection can be trusted if the JSON shape validates.

Early warning signs:

- Tests cover schema shape but not all-rejected or selected-rejected states.
- Review coverage is optional or reviewer roles can repeat.

Containment action: Require complete skeptic coverage, deterministic synthesis,
unique IDs/fingerprints/approach families, and all-rejected terminal behavior.

Disposition: FIXED

Evidence:

- `scripts/orchestration/creative_code_specification.py`
- `tests/test_creative_code_specification.py::test_all_rejected_is_valid_terminal_state`
- `tests/test_creative_code_specification.py::test_selected_rejected_variant_is_banned`
- `tests/test_creative_code_specification.py::test_duplicate_approach_families_fail_closed`

### Finding 5: Local Gates Report A False Green

Failure story: `make validate-changed` is run before new files are committed, so
the diff-based backend hook reports no changed Python files. The PR body then
claims validation coverage even though the new validator and CLI were not
selected.

Underlying assumption: A zero exit from `validate-changed` always means the PR
surface was tested.

Early warning signs:

- Hook output says `No Python or cross-surface governance files changed`.
- New tests are untracked or staged but not committed when the gate runs.

Containment action: Treat empty selection as non-sufficient, run focused pytest,
commit the diff, then rerun `make validate-changed` so branch-diff detection
selects the PR-1 tests.

Disposition: FIXED

Evidence:

- Focused pytest: `tests/test_creative_code_contract.py`, `tests/test_creative_code_specification.py`, `tests/test_context_pack_compression.py`, `tests/core/evidence/test_fingerprints.py`
- `make validate-changed` after commit selected `tests/test_creative_code_specification.py`

## Most Likely Failure

The most likely failure was false validation evidence from diff selection before
the new files were committed. It already appeared during local validation and
was closed by focused pytest plus a post-commit `make validate-changed` rerun.

## Most Dangerous Failure

The most dangerous failure was authority drift from specification output into
patch generation, review disposition, merge readiness, or runtime truth. That
would compromise the creative-code governance train and could let local control
plane artifacts bypass normal PR review.

## Hidden Assumption

The hidden assumption was that "specification-only" would stay obvious once the
pipeline became executable. PR-1 now makes that boundary machine-checkable in
schema, validator, CLI, tests, and docs.

## Revised Plan

- Keep PR-1 pure/offline and specification-only.
- Use PR-0 validator as the source-packet authority.
- Keep all file writes inside the safe local artifact root.
- Store rejected variants as fingerprints and reason codes only.
- Require complete skeptic review coverage before selection.
- Treat empty `validate-changed` selection as non-sufficient until committed
  branch diff selects the relevant tests.

## Pre-Merge Checklist

- Focused creative-code pytest passes.
- `make validate-changed` selects and passes the PR-1 test surface.
- `pre-commit run --all-files` passes after hook modifications are committed.
- Experiment Runner oracle-only evidence is recorded for the actual diff.
- PR body and fixed mapping document the operator-approved local `make verify`
  deferral and current-head GitHub CI heavy-signal requirement.
- Post-open QA, bug-hunter, security, Codex Security, and
  `pulseplate-pr-review` findings are fixed or formally dispositioned.

## Decision

Decision: `proceed`

Reason: The premortem produced PR-surface findings, and each finding is fixed by
the PR-1 validator, CLI, rejection-index, docs, and focused tests before PR open.
