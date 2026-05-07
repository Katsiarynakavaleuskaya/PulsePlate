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
Commit: `bfb94e11a`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml` now validates each
  source run against an approved producer workflow name before `gh run download`.
- `tests/test_release_control_plane_evidence_publication_workflow.py` asserts
  the per-source allowlist entries for release manifest, RAG gate result, and
  build-equivalence evidence.

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

## Residual Risks

- Producer workflow names are intentionally strict. If the repo later renames
  release manifest or build-equivalence producer workflows, this publisher will
  fail closed until the allowlist and docs are updated in a reviewed PR.
- This PR does not create the release truth. It publishes governed artifacts
  that are still validated again by production CD.

## Decision

Proceed with changes. All P0/P1 premortem findings identified before PR open
were fixed in code/docs/tests before this artifact was created.
