# PR 1682 Premortem Risk Review

<!-- markdownlint-disable MD013 -->

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682
Mode: `pr-premortem`
Release-control-plane slice: PR-5 CI release decision integration

Frame: It is 6 months from now. PR-5 merged, but a production release proceeded with incomplete or incoherent release evidence.

## Files Inspected

- `scripts/ci/check_release_control_plane.py`
- `tests/test_release_control_plane_ci_gate.py`
- `.github/workflows/cd.yml`
- `docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md`
- `docs/release/RELEASE_CONTROL_PLANE_CI_GATE.schema.json`
- `docs/release/RELEASE_CONTROL_PLANE_EPIC.md`
- `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

## Failure Modes

### 1. Gate ALLOWs when build equivalence is BLOCK

**Risk:** The CI checker trusts manifest labels and ignores PR-4 build-equivalence output.

**Inspection:** `check_release_control_plane.py` requires `build_equivalence.decision == "EQUIVALENT"` and returns `build_equivalence_not_equivalent` otherwise. Post-open review found that a contradictory payload with `decision == "EQUIVALENT"` plus non-empty findings could still pass.

**Disposition:** FIXED

**Commit:** `78a800f7f`

**Evidence:** `tests/test_release_control_plane_ci_gate.py::test_block_when_build_equivalence_blocks` asserts `BLOCK`, `build_equivalence_not_equivalent`, and `build_identity_mismatch`. `tests/test_release_control_plane_ci_gate.py::test_block_when_equivalent_build_equivalence_has_mismatch_findings` asserts contradictory `EQUIVALENT` payloads return `BLOCK`.

### 2. Gate ALLOWs when RAG gate is NO-GO

**Risk:** A release with failed ML/RAG gates proceeds because the CI gate only validates JSON shape.

**Inspection:** The checker validates the RAG export and requires `release_decision == "PASS"`.

**Disposition:** NOT-A-BUG

**Evidence:** `tests/test_release_control_plane_ci_gate.py::test_block_when_rag_gate_result_is_no_go` and `test_block_when_release_manifest_decision_blocks`.

### 3. Gate ALLOWs when release manifest is BLOCK

**Risk:** Release manifest fail-closed decision is ignored by CI.

**Inspection:** The checker reuses `release_manifest.validate_manifest_payload(...)` and requires `release_decision == "ALLOW"`.

**Disposition:** NOT-A-BUG

**Evidence:** `tests/test_release_control_plane_ci_gate.py::test_block_when_release_manifest_decision_blocks`.

### 4. Gate ignores missing SBOM/provenance evidence

**Risk:** Supply-chain evidence is optional in practice.

**Inspection:** The checker emits `missing_sbom_digest`, `missing_provenance_digest`, `unsupported_digest_format`, and `attestation_not_verified` as fail-closed reasons.

**Disposition:** NOT-A-BUG

**Evidence:** `tests/test_release_control_plane_ci_gate.py::test_block_on_invalid_digest_format` and `test_block_when_attestation_not_verified`.

### 5. Workflow requires App Store secrets in normal PR or tag validation

**Risk:** CI becomes fragile or blocks ordinary release-control-plane validation on protected credentials.

**Inspection:** The new `release-control-plane-fixture-gate` job uses only checkout and local Python fixture generation. It does not use `secrets.*`, Fastlane, or App Store Connect.

**Disposition:** NOT-A-BUG

**Evidence:** `tests/test_release_control_plane_ci_gate.py::test_workflow_integration_does_not_require_app_store_secrets`.

### 6. Workflow mutates upload/deploy behavior outside PR-5 scope

**Risk:** PR-5 silently changes deployment dependencies or upload automation.

**Inspection:** The fixture job is not added to production deploy `needs`, does not call Fastlane, and does not upload App Store artifacts.

**Disposition:** NOT-A-BUG

**Evidence:** `tests/test_release_control_plane_ci_gate.py::test_workflow_integration_does_not_alter_app_store_upload_behavior`.

### 7. Normal PR CI path breaks

**Risk:** Release-control-plane validation destabilizes unrelated PR checks.

**Inspection:** CD workflow still triggers only on `push` to `main` and `v*` tags. The new job is inside CD and is non-secret fixture validation.

**Disposition:** NOT-A-BUG

**Evidence:** `.github/workflows/cd.yml` keeps `on.push.branches: [main]` and `tags: ['v*']`; pre-commit `check-github-workflows` passed.

### 8. Checker accepts malformed JSON

**Risk:** Invalid evidence files are treated as absent or ignored.

**Inspection:** `_load_evidence(...)` reports `malformed_*` reason codes and returns `BLOCK`. Post-open review also found that existing files containing `{}` bypassed validation because empty dictionaries were treated as falsey.

**Disposition:** FIXED

**Commit:** `62b0a2bc2`

**Evidence:** `tests/test_release_control_plane_ci_gate.py::test_block_on_malformed_json` and `test_empty_evidence_objects_are_invalid_not_allowed`.

### 9. Checker accepts invalid digest/hash format

**Risk:** A non-OCI digest or malformed SHA-256 hash bypasses release evidence checks.

**Inspection:** The checker reuses release-manifest regexes and maps digest/hash validation failures to `unsupported_digest_format`. Post-open review also found the output schema was too strict for blocked malformed summary strings.

**Disposition:** FIXED

**Commit:** `62b0a2bc2`

**Evidence:** `tests/test_release_control_plane_ci_gate.py::test_block_on_invalid_digest_format` and `test_schema_allows_raw_malformed_summary_values_for_block_outputs`.

### 10. Reason ordering is nondeterministic

**Risk:** CI evidence changes across runs, making review and mapping unreliable.

**Inspection:** `REASON_ORDER`, `_stable_reason_codes(...)`, and `_stable_findings(...)` define deterministic ordering.

**Disposition:** NOT-A-BUG

**Evidence:** `tests/test_release_control_plane_ci_gate.py::test_reason_code_ordering_is_deterministic` and `test_output_json_is_deterministic`.

### 11. Fixture evidence leaks into production release path

**Risk:** The fixture job is mistaken for real production release evidence.

**Inspection:** Fixture files are generated under `$RUNNER_TEMP/release-control-plane-fixture`, not under `artifacts/release/`, and the docs state production artifact wiring is deferred.

**Disposition:** NOT-A-BUG

**Evidence:** `.github/workflows/cd.yml` fixture root uses `${RUNNER_TEMP}`; `docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md` documents fixture-only workflow integration and deferred protected-environment wiring.

### 12. Ledger closes App Store readiness incorrectly

**Risk:** PR-5 overclaims production readiness.

**Inspection:** Ledger marks PR-5 active but states full App Store readiness is not complete and the train is not production-ready.

**Disposition:** NOT-A-BUG

**Evidence:** `tests/test_release_control_plane_ci_gate.py::test_ledger_marks_pr4_merged_and_pr5_active`.

### 13. Runtime/API/OpenAPI/iOS behavior changes

**Risk:** CI governance PR drifts into product runtime.

**Inspection:** Touched files are limited to `.github/workflows/cd.yml`, docs, `scripts/ci/check_release_control_plane.py`, and tests.

**Disposition:** NOT-A-BUG

**Evidence:** `git diff --name-only origin/main...HEAD` lists no `app/`, `core/`, `ios/`, OpenAPI, billing, or frontend runtime files.

### 14. Mapping/checklists are used instead of fixing findings

**Risk:** Review artifacts are treated as proof before underlying bugs are fixed.

**Inspection:** Pre-push MyPy found a real checker type-boundary issue. Code was fixed before mapping artifacts were added.

**Disposition:** FIXED

**Commit:** `eb798b4d9`

**Evidence:** `scripts/ci/check_release_control_plane.py` now type-checks `_sha256_file(...)` without `Any` leakage; `. .venv/bin/activate && mypy --no-incremental --cache-dir=/dev/null scripts/ci/check_release_control_plane.py` passed; subsequent `make validate-changed`, `pre-commit run --all-files`, and pre-push hooks passed.

### 15. Embedded evidence paths escape `artifacts/`

**Risk:** A release evidence payload points to `artifacts/../outside.json`, bypasses the string prefix guard, and makes the CI gate trust metadata outside allowed artifact locations.

**Inspection:** Post-open review found the path guard used a string prefix check and did not normalize POSIX path parts.

**Disposition:** FIXED

**Commit:** `78a800f7f`

**Evidence:** `scripts/ci/check_release_control_plane.py` now rejects absolute paths, non-`artifacts` roots, and any `..` path part using `PurePosixPath`; `tests/test_release_control_plane_ci_gate.py::test_evidence_paths_reject_parent_directory_escape` covers `artifacts/../leak.json`.

## Synthesis

Most likely failure: protected production artifact wiring is mistaken as complete because fixture validation exists.

Most dangerous failure: the checker returns `ALLOW` while build equivalence, RAG, manifest, or supply-chain evidence is incoherent.

Hidden assumption: later protected-environment work will publish real evidence artifacts into the production tag path before deploy.

Revised plan: keep the checker fail-closed, keep workflow integration fixture-only in this PR, and explicitly defer protected production artifact wiring in docs, PR body, and ledger.

## Decision

`proceed` — plan is sound after premortem inspection of actual code, workflow, docs, and tests.

Unresolved P0/P1: none.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `. .venv/bin/activate && pytest -q tests/test_release_control_plane_ci_gate.py` PASS (`24 passed`)
- `. .venv/bin/activate && pytest -q tests/test_release_manifest.py` PASS (`20 passed`)
- `. .venv/bin/activate && pytest -q tests/test_build_equivalence.py` PASS (`22 passed`)
- `. .venv/bin/activate && pytest -q tests/test_rag_release_gates_runner.py` PASS (`48 passed`)
- `. .venv/bin/activate && pytest -q tests/test_check_docker_provenance_attestation.py` PASS (`12 passed`)
- `. .venv/bin/activate && pytest -q tests/test_repo_policy_guards.py` PASS (`14 passed`)
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md docs/release/RELEASE_CONTROL_PLANE_CI_GATE.schema.json docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md docs/roadmap/BACKLOG_LEDGER.md` PASS
- `make validate-changed` PASS (`44 passed`)
- `pre-commit run --all-files` PASS
- Pre-push hook PASS

## Pre-merge Checklist

- [x] Checker is fail-closed on missing/malformed evidence
- [x] Checker requires manifest `ALLOW`
- [x] Checker requires RAG `PASS`
- [x] Checker requires build equivalence `EQUIVALENT`
- [x] Checker requires verified supply-chain evidence
- [x] Fixture workflow requires no App Store secrets
- [x] Fixture workflow does not mutate App Store upload behavior
- [x] No runtime/API/OpenAPI/iOS files changed
- [x] No unresolved P0/P1 premortem findings
