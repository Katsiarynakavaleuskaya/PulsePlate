# PR 1699 Premortem

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699
Branch: `ci/release-control-plane-evidence-publication`
Mode: `post_open_review`
Coordinator packet: `artifacts/orchestration/task_packets/b29596eedc9a.json`

## Scope Reviewed

- `.github/workflows/release-control-plane-evidence.yml`
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md`
- `docs/orchestration/RELEASE_CONTROL_PLANE_EVIDENCE_PUBLICATION_PACKET_2026-05-07.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `tests/test_release_control_plane_evidence_publication_workflow.py`
- dependency security floor changes required by local pre-push `pip-audit`

## Frame

It is 48 hours after merge. The evidence publication workflow either accepted
unsafe release-control-plane evidence or failed to provide a usable artifact for
the production tag gate. We are looking backward to understand why.

## Findings And Dispositions

### P1: Source runs were not allowlisted

Disposition: FIXED
Commit: `b264f752d`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now validates each
  source run against repo-owned producer workflow names before
  `gh run download`; source JSON that includes operator-supplied
  `workflow_name` now fails closed.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the per-source allowlist entries for release manifest, RAG gate result, and
  build-equivalence evidence.

### P1: Publication could imply missing producer workflows already exist

Disposition: FIXED
Commit: `b264f752d`
Evidence:

- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md` now records
  `Release Manifest Evidence` and `Build Equivalence Evidence` as reserved
  fail-closed producer identities and explicitly says production publication or
  production CD evidence variable setup must not run until the missing producer
  workflows land in a separate reviewed PR.
- `docs/roadmap/BACKLOG_LEDGER.md` records the producer-workflow follow-up and
  the fail-closed stop on ad hoc source runs.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the reserved producer names and the no-variable-setup stop.

### P1: Publication workflow could print handoff variables from the wrong ref

Disposition: FIXED
Commit: `bfb94e11a`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` fails when
  `GITHUB_SHA` differs from the operator-provided `git_sha`.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the publication-run SHA check.

### P1: Fixture/sample evidence and sentinel placeholder hashes could be packaged

Disposition: FIXED
Commit: `bfb94e11a`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` rejects sample RAG
  dataset paths, fixture/placeholder/fake strings, RAG fallback/advisory fixture
  flags, and repeated-character SHA-256 placeholder hashes or digests before
  publishing the artifact.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  those negative controls are present in the publisher.

### P1: Local pre-push dependency audit blocked publication

Disposition: FIXED
Commit: `9f6a655c6`
Evidence:

- `requirements.txt` and related governed requirement surfaces now use
  `mako==1.3.12` and `python-multipart==0.0.27`.
- `scripts/ci/emergency_python_wheels.json` records pinned wheel hashes for the
  updated exact wheels.
- `.secrets.baseline` was updated for the expected wheel SHA-256 fingerprints.
- `PATH=.venv/bin:$PATH pre-commit run pip-audit --hook-stage pre-push --all-files`
  passed locally.

### P2: Post-open workflow hardening findings could become false-green evidence

Disposition: FIXED
Commit: `37b5f046e`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now validates
  `EVIDENCE_ARTIFACT_NAME` as single-line before writing to `$GITHUB_ENV`.
- `.github/workflows/release-control-plane-evidence.yml` now sets
  `timeout-minutes: 20` on the evidence publication job.
- `.github/workflows/release-control-plane-evidence.yml` now rejects singular
  `test` path segments without restoring the overly broad `*test*` pattern that
  would reject legitimate release evidence terms such as `attestation`.
- `tests/test_release_control_plane_evidence_publication_workflow.py` covers the
  single-line guard, job timeout, and singular `test/` rejection.

### P2: Producer identity and test-path filtering still had narrow bypass shapes

Disposition: FIXED
Commit: `ce9016c15`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now validates source
  producer identity with both the workflow display name and the stable workflow
  file path returned by the Actions API.
- `.github/workflows/release-control-plane-evidence.yml` now rejects terminal
  `test` and `tests` path segments in shell inputs.
- `.github/workflows/release-control-plane-evidence.yml` now rejects generic
  `test/` and `tests/` path segments inside evidence JSON payloads after
  normalizing separators.
- `tests/test_release_control_plane_evidence_publication_workflow.py` covers the
  stable producer path allowlist and both shell/payload test-path guards.

## Residual Risks

- Producer workflow names are intentionally strict and currently reserve
  `Release Manifest Evidence` and `Build Equivalence Evidence` for future
  producer-workflow PRs. Until those producers exist, the publisher fails closed
  and production CD evidence variables must not be set from ad hoc source runs.
- This PR does not create the release truth. It publishes governed artifacts
  that are still validated again by production CD.

## Decision

Proceed with changes. All P0/P1 premortem findings and the later post-open P2
workflow hardening findings were fixed in code/docs/tests before mapping was
updated.
