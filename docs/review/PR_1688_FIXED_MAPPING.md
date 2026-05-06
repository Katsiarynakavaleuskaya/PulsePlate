# PR 1688 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1688>

## Summary

PR #1688 wires production release-control-plane evidence artifacts into the
production tag path and keeps App Store/Fastlane upload automation out of
scope.

## Discussion Thread Pass

- [x] Initial post-open coordinator bootstrap completed.
- [x] Internal QA / bug-hunter / security / premortem pass completed against
  actual changed files.
- [x] Premortem P0/P1 findings fixed before mapping.
- [ ] External bot/human discussion-thread pass completed.

## Fixed in Commit Mapping

### Internal Premortem: production evidence artifact could belong to a different tag commit

Disposition: FIXED
Commit: `0bc019fd0`
Evidence:

- `.github/workflows/cd.yml` resolves the production tag commit and fails
  closed when `release_manifest.json` `build_identity.git_sha` differs.
- `tests/test_production_release_evidence_wiring.py::test_production_job_rejects_evidence_for_different_tag_commit`
  covers the workflow contract.

### Internal Premortem / Sidecar Review: production evidence artifact could come from an ungoverned source run

Disposition: FIXED
Commit: `38676dde6`
Evidence:

- `.github/workflows/cd.yml` runs `gh run view` before `gh run download` and
  requires source run `completed`, `success`, matching `headSha`,
  `workflow_dispatch`, and release-control-plane workflow naming.
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_WIRING.md` documents the
  source-run provenance requirements and fail-closed behavior.
- `tests/test_production_release_evidence_wiring.py::test_production_job_verifies_evidence_run_provenance_before_download`
  covers the workflow contract.
- Focused validation after the fix:
  `. .venv/bin/activate && pytest -q tests/test_production_release_evidence_wiring.py tests/test_release_control_plane_ci_gate.py tests/test_build_equivalence.py`
  PASS (`61 passed`).

## Validation

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `. .venv/bin/activate && pytest -q tests/test_production_release_evidence_wiring.py` PASS (`13 passed`)
- `. .venv/bin/activate && pytest -q tests/test_release_control_plane_ci_gate.py` PASS (`26 passed`)
- `. .venv/bin/activate && pytest -q tests/test_release_manifest.py` PASS (`20 passed`)
- `. .venv/bin/activate && pytest -q tests/test_build_equivalence.py` PASS (`22 passed`)
- `. .venv/bin/activate && pytest -q tests/test_rag_release_gates_runner.py` PASS (`48 passed`)
- `. .venv/bin/activate && pytest -q tests/test_check_docker_provenance_attestation.py` PASS (`12 passed`)
- `. .venv/bin/activate && pytest -q tests/test_repo_policy_guards.py` PASS (`14 passed`)
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/release/PRODUCTION_RELEASE_EVIDENCE_WIRING.md docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md docs/roadmap/BACKLOG_LEDGER.md` PASS
- `make validate-changed` PASS (`61 passed`)
- `pre-commit run --all-files` PASS
- Pre-push hooks PASS before PR open.

## Machine-Heavy Deferral

Full local `make verify` intentionally not run. This is the operator-approved
bounded-check path for a machine-heavy CI/release-governance PR.

## Deferred / Follow-ups

- App Store Connect upload and Fastlane protected upload mutation remain
  deferred to a later explicitly scoped protected-environment PR.
- The real release evidence artifact is produced by a separate governed release
  ceremony/run before the production tag deploy attempt.
