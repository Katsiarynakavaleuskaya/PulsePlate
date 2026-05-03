# PR #1642 Fixed in Commit Mapping

## Summary

PR #1642 fixes CD attestation verification sequencing so Docker attestation
verification only runs after build, provenance attestation, SBOM generation,
and SBOM attestation all succeed.

## Root Cause

SBOM attestation failed due to Rekor timeout (`InternalError: error creating
tlog entry`), but verification still ran because the workflow condition only
checked `steps.build.outcome == 'success'`.

## Scope

* `.github/workflows/cd.yml` — add step IDs + update verify conditions
* `tests/test_cd_attestation_workflow_contract.py` — new contract tests
* `tests/test_python_supply_chain_controls.py` — update existing assertion

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1642#discussion_r3177853609 -> b77949f96
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1642#pullrequestreview-4216082023 -> b77949f96
Disposition: FIXED
Commit: b77949f96
Evidence: docs/review/PR_1642_FIXED_MAPPING.md:28 (mapping format corrected)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1642#discussion_r3178073945
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1642#pullrequestreview-4216274296
Disposition: NOT-A-BUG
Evidence: scripts/orchestration/review_mapping_artifact.py:111 (parser validates section-level, not per-line)
Reason: Multiple URL->SHA lines sharing a single Disposition block is the expected canonical format

## Validation

* `pytest -q tests/test_cd_attestation_workflow_contract.py` — 3 passed
* `pytest -q tests/test_python_supply_chain_controls.py` — 41 passed
* `pytest -q tests/test_cd_workflow_production_deploy_gate.py` — 4 passed
* `pytest -q tests/test_check_docker_provenance_attestation.py` — 12 passed
* `make test-fast` — all passed
* `pre-commit run --all-files` — 16/16 passed

## Review Thread Disposition

| Thread | Disposition | Evidence |
|--------|-------------|----------|
| `#discussion_r3177853609` (Cubic: canonical mapping format) | FIXED | Commit `b77949f96` — mapping format corrected |
| `#discussion_r3178073945` (Cubic: per-line disposition block) | NOT-A-BUG | `review_mapping_artifact.py:111` — parser validates section-level |
