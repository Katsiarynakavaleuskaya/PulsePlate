# PR #1526 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:81-84`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141715407 -> e226cecbbbb954e86f66510e517c5b1ed2c54a0b
  Disposition: FIXED
  Evidence: `tests/test_docker_workflow_build_path_contract.py::test_docker_entrypoint_keeps_bodyfat_hidden_but_routable` proves the Docker entrypoint app keeps `/api/v1/bodyfat` hidden from canonical OpenAPI while `POST /api/v1/bodyfat` remains routable with status 200. No backend bootstrap change was required because `app.main:app` reuses `legacy_app.app`, where the bodyfat router is already registered.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141715409 -> e226cecbbbb954e86f66510e517c5b1ed2c54a0b
  Disposition: FIXED
  Evidence: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-runtime-slimming-after-build-path-consolidation` records Owner, Priority, Target PR, Reason, Links, and DoD for the deferred base-image/dependency-profile slimming lane; `docs/deploy/DOCKER.md` now links to that concrete ledger anchor.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#pullrequestreview-4175343676 -> e226cecbbbb954e86f66510e517c5b1ed2c54a0b
  Disposition: FIXED
  Evidence: This CodeRabbit review summary contained the two actionable inline comments already mapped above. Both threads have disposition replies and are resolved on GitHub; CodeRabbit also confirmed both findings as addressed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141780565 -> d847f90d35a9ff1ef500cab7ed5d36f701ebbec3
  Disposition: FIXED
  Evidence: `docs/review/PR_1526_FIXED_MAPPING.md` refreshes the actionable review-summary mapping and bot-comment evidence; CodeRabbit marked this outdated thread addressed after commit `d847f90d35a9ff1ef500cab7ed5d36f701ebbec3`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141780570 -> 3f16ba258da14e6526b5304ccf4e53001cee4ef5
  Disposition: FIXED
  Evidence: `tests/test_docker_workflow_build_path_contract.py::test_build_workflow_owns_docker_validation_contract` now asserts the exact `/api/v1/bodyfat` OpenAPI exclusion predicate instead of an ambiguous positive substring.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141780571 -> 3f16ba258da14e6526b5304ccf4e53001cee4ef5
  Disposition: FIXED
  Evidence: `tests/test_docker_workflow_build_path_contract.py::test_docker_entrypoint_keeps_bodyfat_hidden_but_routable` now asserts `application/json` content type before each `.json()` call.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141780573 -> 3f16ba258da14e6526b5304ccf4e53001cee4ef5
  Disposition: FIXED
  Evidence: `tests/test_docker_workflow_build_path_contract.py::test_trivy_workflow_is_out_of_band_image_security_lane` now forbids both `pull_request` and `pull_request_target` triggers in addition to `push`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#pullrequestreview-4175400759 -> 3f16ba258da14e6526b5304ccf4e53001cee4ef5
  Disposition: FIXED
  Evidence: This CodeRabbit review summary contained the three active test-contract comments mapped above plus the already-addressed mapping evidence comment.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Mandatory wait-window satisfied
  Evidence: draft PR opened; implementation and review cycle pending.
- [ ] Current-head CI is green for PR branch head
  Evidence: pending current-head GitHub checks after mapping artifact push.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending current-head GitHub checks after mapping artifact push.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: no review threads existed when this artifact was seeded.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: CodeRabbit comments `discussion_r3141715407`, `discussion_r3141715409`, `discussion_r3141780565`, `discussion_r3141780570`, `discussion_r3141780571`, `discussion_r3141780573`, and review summaries `pullrequestreview-4175343676` and `pullrequestreview-4175400759` are mapped above with FIXED dispositions and commit evidence.
- [x] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files`, commit hooks, and pre-push hooks passed for `4406fc0bb` (`ci(docker): consolidate validation path`).
- [ ] Heavy full-suite signal accepted from GitHub current-head checks
  Evidence: local `make verify` intentionally deferred under the operator-approved machine-heavy exception for this CI/tooling lane.
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: `qa-engineer-agent` completed a conditional pass with no required file changes; `bug-hunter` completed a false-green review on `9b213dfe0` with no workflow/test code edits required.

## Deferred / Follow-ups

- Docker base-image changes and API-core dependency-profile slimming remain separate follow-up candidates after build-path consolidation: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-runtime-slimming-after-build-path-consolidation`.
- Dagger remains deferred until the GitHub Actions Docker baseline is stable after this lane.
- SBOM/VEX signed security artifacts remain blocked by release-truth criteria.
