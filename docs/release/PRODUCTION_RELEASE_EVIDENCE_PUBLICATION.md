# Production Release Evidence Publication

This document defines the governed publication ceremony for the
release-control-plane evidence artifact consumed by production CD.

## Purpose

PR #1692 made production tags fail closed unless CD can download real
release-control-plane evidence through:

- `RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID`
- `RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME`

This PR adds the manual `Release Control Plane Evidence` workflow that publishes
that artifact after the release manifest, RAG gate result, and build-equivalence
evidence already exist as governed workflow artifacts.

The publication workflow does not create release truth. The source of truth
remains the release manifest contract, RAG gate result export contract,
build-equivalence contract, release-control-plane CI gate contract, and CD
production gate behavior.

## Artifact Layout

The published workflow artifact must include:

```text
release-control-plane/
  release_manifest.json
  rag_gate_result.json
  build_equivalence_result.json
```

Canonical file paths:

- `release-control-plane/release_manifest.json`
- `release-control-plane/rag_gate_result.json`
- `release-control-plane/build_equivalence_result.json`

The workflow also includes validation outputs in the same directory:

```text
release-control-plane/
  release_control_plane_ci_gate.json
  release_control_plane_ci_gate.md
  source_runs.txt
```

Production CD consumes only the three canonical evidence files and validates
them again with `scripts/ci/check_release_control_plane.py`.

## Required Workflow Inputs

Run the `Release Control Plane Evidence` workflow manually with:

- `git_sha`: expected release commit SHA.
- `release_manifest_run_id`, `release_manifest_artifact_name`,
  `release_manifest_path`.
- `rag_gate_result_run_id`, `rag_gate_result_artifact_name`,
  `rag_gate_result_path`.
- `build_equivalence_run_id`, `build_equivalence_artifact_name`,
  `build_equivalence_path`.
- `evidence_artifact_name`: final artifact name for production CD.

GitHub `workflow_dispatch` cannot upload arbitrary operator-local files. The
workflow therefore downloads existing governed workflow artifacts from
successful `workflow_dispatch` source runs, copies the selected files into the
canonical layout, validates them, and publishes the combined artifact.

Approved source producer workflow names:

- `Release Control Plane Manifest` or `Release Manifest` for
  `release_manifest.json`.
- `RAG Release Gates` for `rag_gate_result.json`.
- `Release Control Plane Build Equivalence` or `Build Equivalence` for
  `build_equivalence_result.json`.

The publication workflow itself must be dispatched on the release commit or ref:
its workflow ref must match `git_sha`.

Local validation for PR work on this lane uses the repo virtualenv only:
`.venv/bin/python`. Do not substitute system `python3` for local repository
commands.

## Protected Operator Ceremony

1. Produce or locate governed source artifacts for the release manifest, RAG
   gate result, and build-equivalence result.
2. Run `Release Control Plane Evidence` with the release `git_sha` and source
   artifact details.
3. Confirm the workflow completed successfully and published the artifact.
4. Copy the workflow run id from the step summary.
5. Set production or repository Actions variables:
   - `RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID=<workflow run id>`
   - `RELEASE_CONTROL_PLANE_EVIDENCE_ARTIFACT_NAME=<evidence artifact name>`
6. Create the production tag only after evidence publication is complete.

If the repo does not have a dedicated `release-evidence` protected environment,
the manual workflow still remains non-secret and operator-governed. Protected
App Store credentials are not required.

## Fail-Closed Behavior

The publication workflow blocks when:

- any source run id is missing or non-numeric;
- any source artifact name or path references fixture, test, placeholder, or
  fake evidence;
- any source artifact cannot be downloaded;
- a selected evidence file is missing;
- evidence JSON is malformed;
- the publication workflow ref does not match `git_sha`;
- a source run was not triggered by `workflow_dispatch`;
- a source run workflow name is not one of the approved evidence producers;
- source run `headSha` does not match `git_sha`;
- release manifest `build_identity.git_sha` does not match `git_sha`;
- any evidence JSON contains a sentinel placeholder digest or hash such as a
  repeated-character SHA-256 value;
- RAG evidence points to the sample eval dataset, fixture paths, fallback data,
  or advisory fixture gates;
- `scripts/ci/check_release_control_plane.py` returns `BLOCK`.

The production tag path still performs its own independent fail-closed download
and validation after operators set the two evidence variables.

## Forbidden Behavior

This workflow must not:

- use fixtures as production evidence;
- accept placeholder digests;
- contact App Store Connect;
- run or mutate Fastlane upload behavior;
- read App Store credentials;
- change backend, iOS, frontend, OpenAPI, RAG, billing, semantic cache,
  GraphRAG, or product-facing runtime behavior;
- run from `pull_request`;
- publish generated release artifacts into the repository.

## Rollback

Revert the workflow/docs/tests PR. PR #1692 production CD behavior remains
fail-closed, so production deploy stays blocked until a valid evidence artifact
is supplied.

## Definition Of Done

- Manual evidence publication workflow exists.
- Workflow is `workflow_dispatch` only.
- Workflow publishes the canonical `release-control-plane/` artifact layout.
- Workflow validates source evidence and release `git_sha`.
- Docs explain the operator handoff variables.
- Tests prove no fixtures, App Store upload, Fastlane mutation, or runtime
  behavior enters this PR.
