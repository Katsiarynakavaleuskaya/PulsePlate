# PR #1703 Fixed In Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1703
Branch: `ci/release-control-plane-source-producers`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Status: External review comments inspected through current head.

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
- GitHub workflow lint failed on too many dispatch inputs and SC2153 shell variables -> `664c1fd5d`
- CodeRabbit actionable: fixed-mapping checklist was missing checked discussion/mapping boxes -> `79c15fcfe`
- CodeRabbit nit: `artifact-name` CLI command relied on implicit fall-through -> `79c15fcfe`
- Cubic P2: evidence source substring matching could reject valid paths such as `latest/...` -> `79c15fcfe`
- Bug-hunter P1: nested RAG `source_artifacts[*].path` allowed path escapes such as `../prod/release.jsonl` -> `79c15fcfe`

## NOT-A-BUG

- Suggested `artifact-metadata: write` permission.
  - Evidence: `check-github-workflows` rejects `artifact-metadata` in the current schema. Valid permissions retained: `attestations: write`, `id-token: write`, `packages: write`.
  - Guard: `tests/test_release_manifest_evidence_workflow.py` asserts `artifact-metadata` is absent.
- Cubic P1: artifact root mismatch for `release-control-plane-build-sources`.
  - Evidence: Fixed by `664c1fd5d`, which replaced separate `sbom_digest_source`, `provenance_digest_source`, and `attestation_status_source` inputs with a single governed `supply_chain_source` object whose expected path is `release-control-plane-build-sources`. The manifest producer then reads `${supply_chain_source_path}/sbom_digest.txt`, `${supply_chain_source_path}/provenance_digest.txt`, and `${supply_chain_source_path}/attestation_status.txt`.
- CodeRabbit nit: `scripts/release/build_identity.py` direct-invocation `sys.path.insert`.
  - Evidence: Fixed as documentation-only in `79c15fcfe`; the script remains a standalone repo CLI for GitHub Actions, and package-style `python -m` invocation remains available.
- Sourcery weekly diff-character rate limit.
  - Evidence: Sourcery posted a rate-limit comment only; no actionable code finding was provided.

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
