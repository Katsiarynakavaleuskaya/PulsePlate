# PR #1703 Premortem

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1703
Branch: `ci/release-control-plane-source-producers`
Mode: `pr-premortem`

## Scope Reviewed

- `.github/workflows/release-manifest-evidence.yml`
- `.github/workflows/build-equivalence-evidence.yml`
- `.github/workflows/build.yml`
- `scripts/release/evidence_source.py`
- `scripts/release/build_identity.py`
- `tests/test_release_manifest_evidence_workflow.py`
- `tests/test_build_equivalence_evidence_workflow.py`
- `tests/test_release_control_plane_evidence_publication_workflow.py`
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md`
- `docs/release/RELEASE_CONTROL_PLANE_EPIC.md`
- `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

## Frame

It is 48 hours after merge. The release-control-plane source producer lane failed by publishing misleading production evidence or by blocking the governed publisher forever. This premortem records the failure modes found before PR open and the fixes made before mapping.

## Findings And Dispositions

### P1: Raw artifact name bypassed validation

Disposition: FIXED
Commit: `1876e231b`
Evidence: upload steps now use sanitized step outputs, not raw `inputs.evidence_artifact_name`; guarded by `tests/test_release_manifest_evidence_workflow.py` and `tests/test_build_equivalence_evidence_workflow.py`.

### P1: RAG payload `git_sha` was not checked

Disposition: FIXED
Commit: `1876e231b`
Evidence: `scripts/release/evidence_source.py` validates `rag_gate_result.git_sha` against the expected SHA; workflow calls `rag-gate-result`; regression tests cover mismatch.

### P1: Downloaded artifact symlink target could escape path guard

Disposition: FIXED
Commit: `1876e231b`
Evidence: workflows resolve downloaded file targets with `Path.resolve()` before reading; tests assert the resolved-path guard.

### P2: Source object path contract accepted noncanonical paths

Disposition: FIXED
Commit: `1876e231b`
Evidence: `source-env` supports `--expected-path`; producer workflows pin `rag_gate_result.json` and `release_manifest.json`.

### P1: Generic test paths inside RAG payload were not rejected

Disposition: FIXED
Commit: `9a4b5f666`
Evidence: `FORBIDDEN_TEST_PATH_RE` in `scripts/release/evidence_source.py`; tests reject `tests/evals/release.jsonl`.

### P2: Manifest generation could preserve uppercase git SHA input

Disposition: FIXED
Commit: `9a4b5f666`
Evidence: `release-manifest-evidence.yml` passes normalized `$expected_git_sha_lc` to `release_manifest.py generate`.

### P1: Build-equivalence producer could publish `BLOCK` evidence as successful

Disposition: FIXED
Commit: `1876e231b`
Evidence: workflow checks `build_equivalence_result.decision == EQUIVALENT` before upload.

### P1: Supply-chain values were manual assertions

Disposition: FIXED
Commit: `f43d6c1ec`
Evidence: `build.yml` runs `scripts/ci/check_docker_provenance_attestation.py`; source files are written only when verifier JSON has `passed: true`; release manifest producer compares source files to explicit inputs.

### P1: Supply-chain source files could be mixed across runs

Disposition: FIXED
Commit: `e1f454cb9`
Evidence: release manifest producer requires SBOM, provenance, and attestation status sources to share the same run id and artifact name.

### P1: Docker build self-certified App Review and production-candidate digests

Disposition: FIXED
Commit: `f43d6c1ec`
Evidence: `build.yml` no longer emits `review_artifact_digest.txt` or `production_candidate_artifact_digest.txt`; build equivalence keeps those as explicit protected dispatch inputs because App Store/Fastlane binary production is out of scope.

### P1: Producer workflows failed GitHub workflow lint on current head

Disposition: FIXED
Commit: `664c1fd5d`
Evidence: `Release Manifest Evidence` now uses one governed `supply_chain_source` object so `workflow_dispatch` stays at the GitHub limit of 10 inputs. Both producer workflows copy generated env output into local shell variables before use, closing SC2153. Local `check-github-workflows`, focused pytest, docs gate, `make validate-changed`, and `pre-commit run --all-files` passed after the fix.

### P2: Evidence source substring matching rejected valid path words

Disposition: FIXED
Commit: `04c7ba87d`
Evidence: the evidence source validator now uses boundary-aware word extraction for fixture/sample/placeholder/fake/fallback tokens instead of raw substring matching. Regression coverage accepts a valid `latest/rag_gate_result.json` source path while still rejecting `test` / `tests` path components and forbidden evidence words.

### P1: Nested RAG source artifact paths could escape evidence roots

Disposition: FIXED
Commit: `04c7ba87d`
Evidence: the evidence source validator now checks nested `*.path` fields inside the governed RAG payload with the same path-safety rules used for top-level source objects. Regression coverage rejects `../prod/release.jsonl`, absolute paths, and double-slash paths before a manifest can be generated.

### P1: Suggested `artifact-metadata: write` permission

Disposition: NOT-A-BUG
Evidence: local `check-github-workflows` rejects `artifact-metadata` as invalid for the current workflow schema. PR keeps valid attestation permissions: `attestations: write`, `id-token: write`, `packages: write`; regression asserts `artifact-metadata` is absent.

### P2: App Store build identity can drift from repo release truth

Disposition: DEFERRED
Backlog: App Store Connect upload execution / Fastlane protected upload mutation remain deferred in `docs/roadmap/BACKLOG_LEDGER.md`.
Reason: This PR does not implement App Store binary production or upload. Build identity stays a protected release input until the dedicated App Store release execution/readiness lane owns it.

## Decision

Proceed with review. All P0/P1 premortem findings found before PR open were fixed or dispositioned with evidence. P2 App Store identity truth remains explicitly deferred to the separate App Store release execution/readiness line.

## Validation Evidence

- `.venv/bin/python scripts/orchestration/check_preflight.py` -> PASS
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py` -> PASS
- `.venv/bin/python -m pytest -q tests/test_release_manifest_evidence_workflow.py tests/test_build_equivalence_evidence_workflow.py tests/test_release_control_plane_evidence_publication_workflow.py tests/test_release_manifest.py tests/test_build_equivalence.py tests/test_release_control_plane_ci_gate.py tests/test_production_release_evidence_wiring.py tests/test_check_docker_provenance_attestation.py` -> PASS
- `.venv/bin/python scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md` -> PASS
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` -> PASS
- `PATH=.venv/bin:$PATH pre-commit run --all-files` -> PASS
