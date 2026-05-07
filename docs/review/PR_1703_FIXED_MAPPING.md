# PR #1703 Fixed In Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1703
Branch: `ci/release-control-plane-source-producers`

## Discussion Thread Pass

Status: Pending external review.

No GitHub review threads were resolved before this artifact was created. New CodeRabbit/Sourcery/Cubic/human comments must be fixed or dispositioned here before thread resolution.

## Fixed In Commit Mapping

Internal pre-open review findings fixed before PR open:

- Raw upload artifact name bypassed validation -> `1876e231b`
- Missing `rag_gate_result.git_sha` validation -> `1876e231b`
- Downloaded artifact symlink target escape -> `1876e231b`
- Noncanonical source object paths -> `1876e231b`
- Generic test paths accepted inside RAG payload -> `9a4b5f666`
- Uppercase `git_sha` propagated into manifest generation -> `9a4b5f666`
- Build equivalence could upload non-`EQUIVALENT` result -> `1876e231b`
- Manual supply-chain assertions -> `f43d6c1ec`
- Mixed supply-chain source runs/artifacts -> `e1f454cb9`
- Docker build self-certified App Review / production-candidate digests -> `f43d6c1ec`

## NOT-A-BUG

- Suggested `artifact-metadata: write` permission.
  - Evidence: `check-github-workflows` rejects `artifact-metadata` in the current schema. Valid permissions retained: `attestations: write`, `id-token: write`, `packages: write`.
  - Guard: `tests/test_release_manifest_evidence_workflow.py` asserts `artifact-metadata` is absent.

## DEFERRED

- App Store build identity truth remains separate from this release-control-plane source-producer PR.
  - Backlog: `docs/roadmap/BACKLOG_LEDGER.md`
  - Reason: App Store Connect upload execution, Fastlane protected upload mutation, and App Review binary artifact production are explicitly out of scope for PR #1703.

## Validation

- `.venv/bin/python scripts/orchestration/check_preflight.py` -> PASS
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py` -> PASS
- `.venv/bin/python -m pytest -q tests/test_release_manifest_evidence_workflow.py tests/test_build_equivalence_evidence_workflow.py tests/test_release_control_plane_evidence_publication_workflow.py tests/test_release_manifest.py tests/test_build_equivalence.py tests/test_release_control_plane_ci_gate.py tests/test_production_release_evidence_wiring.py tests/test_check_docker_provenance_attestation.py` -> PASS
- `.venv/bin/python scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md` -> PASS
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` -> PASS
- `PATH=.venv/bin:$PATH pre-commit run --all-files` -> PASS

## Merge Readiness

Not ready yet. Current-head CI, external review comments, mandatory wait-window, and strict merge-readiness wrapper must pass before merge.
