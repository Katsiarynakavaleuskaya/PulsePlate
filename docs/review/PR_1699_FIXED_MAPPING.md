# PR 1699 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699
Branch: `ci/release-control-plane-evidence-publication`
Head at open: `9f6a655c63dc9facb94301265da024dd567dce47`

## Summary

This artifact records pre-open subagent findings and post-open governance
placeholders for PR #1699. Mapping is evidence after fix or disposition; it is
not a substitute for fixes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open review comments visible through the latest local GitHub review
inspection are dispositioned below. New comments after this pass require a new
mapping update before merge readiness.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201096560 -> b264f752d
Disposition: FIXED
Commit: b264f752d
Evidence: Workflow producer validation now rejects operator-supplied `workflow_name` and compares GitHub run metadata against repo-owned producer workflow constants before artifact download.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201116494 -> 98be97185
Disposition: FIXED
Commit: 98be97185
Evidence: Workflow SHA comparisons normalize expected git SHA, workflow GITHUB_SHA, source run headSha, and manifest build_identity.git_sha before comparison.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201116498 -> 98be97185
Disposition: FIXED
Commit: 98be97185
Evidence: Workflow guard tests now assert production CD gate docs describe fail-closed behavior when release evidence is missing.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201116502 -> 98be97185
Disposition: FIXED
Commit: 98be97185
Evidence: Backlog ledger wording now consistently records mako 1.3.12 as the audited floor.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201116524 -> 98be97185
Disposition: FIXED
Commit: 98be97185
Evidence: Backlog ledger wording now uses workflow_dispatch terminology consistently for governed source artifacts.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#pullrequestreview-4243624471
Disposition: NOT-A-BUG
Evidence: Sourcery review summary listed four concrete findings; the actionable discussion URLs from that review are individually mapped and fixed above.
Reason: The review-level summary itself is a container for mapped findings, not a separate repository defect.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699 -> 66023306c
Disposition: FIXED
Commit: 66023306c
Evidence: The release evidence workflow now uses three JSON source inputs and stays under GitHub's workflow_dispatch 10-input limit while preserving fail-closed source validation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699 -> 9f6a655c6
Disposition: FIXED
Commit: 9f6a655c6
Evidence: Local pre-push pip-audit blocker was fixed by bumping mako to 1.3.12 and python-multipart to 0.0.27 across governed dependency surfaces.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201422682 -> 04fc129bf
Disposition: FIXED
Commit: 04fc129bf
Evidence: The release-control-plane ledger Target PR chain now includes concrete PR #1699 alongside the branch token.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#pullrequestreview-4243989997 -> 04fc129bf
Disposition: FIXED
Commit: 04fc129bf
Evidence: CodeRabbit review summary corresponds to discussion_r3201422682, fixed by adding PR #1699 to the ledger Target PR chain.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201814486 -> 37b5f046e45caa2e7617441d228bfbe4810cc3cd
Disposition: FIXED
Commit: 37b5f046e45caa2e7617441d228bfbe4810cc3cd
Evidence: Evidence artifact name CR/LF validation was added before appending to `$GITHUB_ENV`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#pullrequestreview-4244423490 -> 37b5f046e45caa2e7617441d228bfbe4810cc3cd
Disposition: FIXED
Commit: 37b5f046e45caa2e7617441d228bfbe4810cc3cd
Evidence: Release evidence publication job now has `timeout-minutes: 20`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201820243 -> ce9016c155e619b3640d861e4c0d17bb0440cb5d
Disposition: FIXED
Commit: ce9016c155e619b3640d861e4c0d17bb0440cb5d
Evidence: Shell and JSON payload guards now reject singular and terminal `test` / `tests` path segments.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#pullrequestreview-4244429141 -> ce9016c155e619b3640d861e4c0d17bb0440cb5d
Disposition: FIXED
Commit: ce9016c155e619b3640d861e4c0d17bb0440cb5d
Evidence: Cubic review finding is fixed by the path-segment guard and stable producer identity hardening.

## Pre-Open Subagent Findings

### Source runs are not allowlisted

Disposition: FIXED
Commit: `bfb94e11a`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml`
- `tests/test_release_control_plane_evidence_publication_workflow.py`

### Publication run SHA is not checked

Disposition: FIXED
Commit: `bfb94e11a`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml`
- `tests/test_release_control_plane_evidence_publication_workflow.py`

### Fixture/sample evidence and placeholder hashes can still validate

Disposition: FIXED
Commit: `bfb94e11a`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml`
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md`
- `tests/test_release_control_plane_evidence_publication_workflow.py`

### Dependency audit blocked push

Disposition: FIXED
Commit: `9f6a655c6`
Evidence:

- `requirements.txt`
- `requirements-lock.txt`
- `requirements-ci-lite.txt`
- `requirements-docker-runtime.txt`
- `scripts/ci/emergency_python_wheels.json`
- `tests/fixtures/dependency_security_schema.json`
- `.secrets.baseline`
- `PATH=.venv/bin:$PATH pre-commit run pip-audit --hook-stage pre-push --all-files` passed.

## Second Agent / Security / Premortem Pass

### Producer workflow name is self-attested by operator input

Disposition: FIXED
Commit: `b264f752d`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` rejects
  source JSON containing `workflow_name`; the expected producer workflow names
  are repo-owned constants: `Release Manifest Evidence`, `RAG Release Gates`,
  and `Build Equivalence Evidence`.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  source input descriptions/defaults do not accept `workflow_name`, the
  operator-provided `*_WORKFLOW_NAME` variables are absent, and repo-owned
  producer constants are present.
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md` documents that
  producer identity is not operator-supplied dispatch metadata.

### Release-manifest and build-equivalence producer workflows are not present yet

Disposition: FIXED
Commit: `b264f752d`
Evidence:

- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md` records
  `Release Manifest Evidence` and `Build Equivalence Evidence` as reserved
  fail-closed producer identities for future producer-workflow PRs and says not
  to run production publication or set production CD evidence variables until
  those workflows exist.
- `docs/roadmap/BACKLOG_LEDGER.md` records the producer-workflow follow-up and
  blocks ad hoc source runs.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the reserved producer names and no-variable-setup stop.

### Ledger still recorded stale Mako floor

Disposition: FIXED
Commit: `b264f752d`
Evidence:

- `docs/roadmap/BACKLOG_LEDGER.md` now distinguishes the historical
  `Mako 1.3.11` first-patched version from the current enforced floor
  `Mako 1.3.12`, and its DoD uses `1.3.12` for governed surfaces, lock pins,
  and dependency security schema evidence.

## Post-Open Review Threads

### Codex Review: include current evidence producers in the allowlist

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201096560 -> b264f752d

Disposition: FIXED
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now rejects
  operator-supplied `workflow_name` and compares each source run `workflowName`
  against repo-owned producer workflow constants before download.
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md` documents that RAG
  currently has a repo-defined producer while manifest/build-equivalence
  producer names are reserved fail-closed identities for separate producer
  workflow PRs.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the repo-owned producer allowlist contract.

### Sourcery: normalize git SHA comparisons

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201116494 -> 98be97185

Disposition: FIXED
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` normalizes
  `EXPECTED_GIT_SHA`, `GITHUB_SHA`, source run `headSha`, and release manifest
  `build_identity.git_sha` to lowercase before comparison.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  all normalized comparison variables.

### Sourcery: assert fail-closed CD gate docs

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201116498 -> 98be97185

Disposition: FIXED
Evidence:

- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  that `RELEASE_CONTROL_PLANE_CI_GATE.md` documents production blocking on
  missing evidence.

### Sourcery: align Russian Mako fallback wording

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201116502 -> 98be97185

Disposition: FIXED
Evidence:

- `docs/roadmap/BACKLOG_LEDGER.md` now uses `mako 1.3.12` consistently in the
  Russian and English fallback wording.

### Sourcery: use `workflow_dispatch` terminology consistently

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201116524 -> 98be97185

Disposition: FIXED
Evidence:

- `docs/roadmap/BACKLOG_LEDGER.md` now says successful `workflow_dispatch`
  source artifacts.

### Sourcery review summary

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#pullrequestreview-4243624471

Disposition: NOT-A-BUG
Evidence:

- The review summary is a container for the four Sourcery discussion findings
  mapped above; it did not add a separate code or docs defect after those
  findings were fixed.

### CodeRabbit: add concrete PR number to ledger Target PR

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201422682 -> 04fc129bf

Disposition: FIXED
Evidence:

- `docs/roadmap/BACKLOG_LEDGER.md` Target PR now includes `PR #1699`
  alongside `ci/release-control-plane-evidence-publication`.

### CodeRabbit review summary

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#pullrequestreview-4243989997 -> 04fc129bf

Disposition: FIXED
Evidence:

- This review summary corresponds to `discussion_r3201422682`; the ledger
  traceability finding is fixed in commit `04fc129bf`.

## Current-Head CI Findings

### GitHub Actions: actionlint rejects more than 10 workflow_dispatch inputs

Disposition: FIXED
Commit: `66023306c`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now uses three JSON
  source inputs plus `git_sha` and `evidence_artifact_name`, keeping the manual
  workflow below GitHub's 10-input limit while preserving source run, artifact,
  repo-owned workflow producer, path, and git SHA validation.
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md` documents the JSON
  source object contract for operators.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the workflow input count stays at or below 10.
- `PATH=.venv/bin:$PATH pre-commit run --all-files` passed after the fix.

## Post-Open Bot Review Pass After `832c65d30`

### CodeRabbit: validate evidence artifact name before writing to GITHUB_ENV

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201814486 -> 37b5f046e

Disposition: FIXED
Commit: `37b5f046e`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml:73` adds
  `reject_newline` for CR/LF rejection.
- `.github/workflows/release-control-plane-evidence.yml:148` validates
  `EVIDENCE_ARTIFACT_NAME` before it is appended to `$GITHUB_ENV`.
- `tests/test_release_control_plane_evidence_publication_workflow.py:132`
  asserts the single-line guard and evidence artifact name validation.

### CodeRabbit: add a job timeout around governed artifact downloads

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#pullrequestreview-4244423490 -> 37b5f046e

Disposition: FIXED
Commit: `37b5f046e`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml:37` sets
  `timeout-minutes: 20` on the release evidence publication job.
- `tests/test_release_control_plane_evidence_publication_workflow.py:84`
  asserts the timeout remains present.

### Cubic: reject singular `test/` evidence paths without broad `test` substring blocking

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201820243 -> 37b5f046e

Disposition: FIXED
Commit: `37b5f046e`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml:66` rejects exact
  `test`, `test/...`, and `.../test/...` path segments while preserving the
  narrower guard that does not reject release words such as `attestation`.
- `tests/test_release_control_plane_evidence_publication_workflow.py:140`
  asserts the broad `*[Tt][Ee][Ss][Tt]*` pattern stays absent.
- `tests/test_release_control_plane_evidence_publication_workflow.py:141`
  asserts singular `test/` path segment patterns are covered.

### Local focused regression check

Disposition: FIXED
Commit: `37b5f046e`
Evidence:

- `.venv/bin/python -m pytest -q tests/test_release_control_plane_evidence_publication_workflow.py` -> PASS.

## Third Agent / Security / Premortem Pass

### Stable producer identity must not rely only on workflow display name

Disposition: FIXED
Commit: `ce9016c15`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now fetches each source
  run through the Actions REST API and validates its stable workflow file path
  against repo-owned expected workflow paths.
- `.github/workflows/release-control-plane-evidence.yml` still checks the
  human-readable workflow name, but the path check prevents duplicate display
  names from satisfying producer identity.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the Actions API path lookup, the path mismatch error, and all expected
  workflow file path constants.

### Terminal `test` and `tests` path segments could bypass shell guard

Disposition: FIXED
Commit: `ce9016c15`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now rejects exact
  terminal path segments such as `.../test` and `.../tests` in addition to
  `test/...`, `tests/...`, and nested variants.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  terminal `test` and `tests` path segment patterns without reintroducing broad
  `*test*` substring blocking.

### Evidence JSON scanner missed generic `test/` and `tests/` payload paths

Disposition: FIXED
Commit: `ce9016c15`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now normalizes path
  separators in evidence strings and rejects `(^|/)tests?(/|$)` path segments
  inside downloaded JSON payloads before publishing.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the normalized-path scanner and `test evidence path rejected` fail-closed
  error.

Any later actionable review comment must be added here with one of:

- `FIXED`: commit SHA plus evidence.
- `NOT-A-BUG`: evidence and rationale.
- `DEFERRED`: backlog link and rationale.

## Validation

- `.venv/bin/python scripts/orchestration/check_preflight.py` -> PASS
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py` -> PASS
- `.venv/bin/python -m pytest -q tests/test_release_control_plane_evidence_publication_workflow.py tests/test_release_control_plane_ci_gate.py tests/test_production_release_evidence_wiring.py tests/test_build_equivalence.py tests/test_release_manifest.py tests/test_dependency_security_guard.py tests/test_install_locked_python_requirements.py` -> PASS
- `.venv/bin/python scripts/ci/check_docs_phase1_gates.py --files docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md docs/orchestration/RELEASE_CONTROL_PLANE_EVIDENCE_PUBLICATION_PACKET_2026-05-07.md docs/roadmap/BACKLOG_LEDGER.md docs/security/CVE-2026-40347-python-multipart.md docs/security/GHSA-v92g-xgxw-vvmm-mako.md` -> PASS
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` -> PASS
- `PATH=.venv/bin:$PATH pre-commit run --all-files` -> PASS
- `PATH=.venv/bin:$PATH pre-commit run pip-audit --hook-stage pre-push --all-files` -> PASS
- `git push -u origin ci/release-control-plane-evidence-publication` pre-push hooks -> PASS

## Merge Readiness

Not claimed. Merge readiness still requires current-head CI, review-thread
disposition, mandatory wait-window, and strict merge-readiness wrapper.
