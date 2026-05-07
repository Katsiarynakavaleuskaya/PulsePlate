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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201096560 -> 3bcd02e97
Disposition: FIXED
Commit: 3bcd02e97
Evidence: Workflow producer validation now accepts explicit source workflow names and compares them to GitHub run metadata before artifact download.

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699 -> 66023306c
Disposition: FIXED
Commit: 66023306c
Evidence: The release evidence workflow now uses three JSON source inputs and stays under GitHub's workflow_dispatch 10-input limit while preserving fail-closed source validation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699 -> 9f6a655c6
Disposition: FIXED
Commit: 9f6a655c6
Evidence: Local pre-push pip-audit blocker was fixed by bumping mako to 1.3.12 and python-multipart to 0.0.27 across governed dependency surfaces.

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

## Post-Open Review Threads

### Codex Review: include current evidence producers in the allowlist

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699#discussion_r3201096560 -> 3bcd02e97

Disposition: FIXED
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now accepts explicit
  `*_workflow_name` inputs and compares each source run `workflowName` against
  the operator-provided expected producer before download.
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md` documents that RAG
  currently has a repo-defined producer while manifest/build-equivalence
  producers must be supplied explicitly or added in a separate PR.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the expected-producer input contract.

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

## Current-Head CI Findings

### GitHub Actions: actionlint rejects more than 10 workflow_dispatch inputs

Disposition: FIXED
Commit: `66023306c`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now uses three JSON
  source inputs plus `git_sha` and `evidence_artifact_name`, keeping the manual
  workflow below GitHub's 10-input limit while preserving source run, artifact,
  workflow name, path, and git SHA validation.
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md` documents the JSON
  source object contract for operators.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the workflow input count stays at or below 10.
- `PATH=.venv/bin:$PATH pre-commit run --all-files` passed after the fix.

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
