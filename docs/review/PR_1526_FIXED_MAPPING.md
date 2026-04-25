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
Commit: e226cecbbbb954e86f66510e517c5b1ed2c54a0b
Evidence: `tests/test_docker_workflow_build_path_contract.py::test_docker_entrypoint_keeps_bodyfat_hidden_but_routable` proves the Docker entrypoint app keeps `/api/v1/bodyfat` hidden from canonical OpenAPI while `POST /api/v1/bodyfat` remains routable with status 200. No backend bootstrap change was required because `app.main:app` reuses `legacy_app.app`, where the bodyfat router is already registered.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141715409 -> e226cecbbbb954e86f66510e517c5b1ed2c54a0b
Disposition: FIXED
Commit: e226cecbbbb954e86f66510e517c5b1ed2c54a0b
Evidence: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-runtime-slimming-after-build-path-consolidation` records Owner, Priority, Target PR, Reason, Links, and DoD for the deferred base-image/dependency-profile slimming lane; `docs/deploy/DOCKER.md` now links to that concrete ledger anchor.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#pullrequestreview-4175343676 -> e226cecbbbb954e86f66510e517c5b1ed2c54a0b
Disposition: FIXED
Commit: e226cecbbbb954e86f66510e517c5b1ed2c54a0b
Evidence: This CodeRabbit review summary contained the two actionable inline comments already mapped above. Both threads have disposition replies and are resolved on GitHub; CodeRabbit also confirmed both findings as addressed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141780565 -> d847f90d35a9ff1ef500cab7ed5d36f701ebbec3
Disposition: FIXED
Commit: d847f90d35a9ff1ef500cab7ed5d36f701ebbec3
Evidence: `docs/review/PR_1526_FIXED_MAPPING.md` refreshes the actionable review-summary mapping and bot-comment evidence; CodeRabbit marked this outdated thread addressed after commit `d847f90d35a9ff1ef500cab7ed5d36f701ebbec3`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141780570 -> 3f16ba258da14e6526b5304ccf4e53001cee4ef5
Disposition: FIXED
Commit: 3f16ba258da14e6526b5304ccf4e53001cee4ef5
Evidence: `tests/test_docker_workflow_build_path_contract.py::test_build_workflow_owns_docker_validation_contract` now asserts the exact `/api/v1/bodyfat` OpenAPI exclusion predicate instead of an ambiguous positive substring.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141780571 -> 3f16ba258da14e6526b5304ccf4e53001cee4ef5
Disposition: FIXED
Commit: 3f16ba258da14e6526b5304ccf4e53001cee4ef5
Evidence: `tests/test_docker_workflow_build_path_contract.py::test_docker_entrypoint_keeps_bodyfat_hidden_but_routable` now asserts `application/json` content type before each `.json()` call.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141780573 -> 3f16ba258da14e6526b5304ccf4e53001cee4ef5
Disposition: FIXED
Commit: 3f16ba258da14e6526b5304ccf4e53001cee4ef5
Evidence: `tests/test_docker_workflow_build_path_contract.py::test_trivy_workflow_is_out_of_band_image_security_lane` now forbids both `pull_request` and `pull_request_target` triggers in addition to `push`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#pullrequestreview-4175400759 -> 3f16ba258da14e6526b5304ccf4e53001cee4ef5
Disposition: FIXED
Commit: 3f16ba258da14e6526b5304ccf4e53001cee4ef5
Evidence: This CodeRabbit review summary contained the three active test-contract comments mapped above plus the already-addressed mapping evidence comment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#pullrequestreview-4175405610 -> 687b0d21a4f3fb81d33f19ef2bd1170124ceb24e
Disposition: FIXED
Commit: 687b0d21a4f3fb81d33f19ef2bd1170124ceb24e
Evidence: `docs/review/PR_1526_FIXED_MAPPING.md` now replaces stale seed-time thread evidence with current mapped-thread evidence.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141794105 -> 687b0d21a4f3fb81d33f19ef2bd1170124ceb24e
Disposition: FIXED
Commit: 687b0d21a4f3fb81d33f19ef2bd1170124ceb24e
Evidence: `docs/review/PR_1526_FIXED_MAPPING.md` now leaves the final merge-readiness checklist items unchecked until the final merge cycle while preserving the existing evidence text.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#pullrequestreview-4175411572 -> 687b0d21a4f3fb81d33f19ef2bd1170124ceb24e
Disposition: FIXED
Commit: 687b0d21a4f3fb81d33f19ef2bd1170124ceb24e
Evidence: This CodeRabbit review summary contained the final merge-readiness checklist and stale-evidence comments mapped above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#discussion_r3141817225 -> cccae3499871af83ef9943f3050916aaa45bfe5a
Disposition: FIXED
Commit: cccae3499871af83ef9943f3050916aaa45bfe5a
Evidence: `docs/review/PR_1526_FIXED_MAPPING.md` now rewords the pre-commit evidence as a `4406fc0bb` head snapshot instead of the latest pushed head and adds explicit `Commit:` proof to each FIXED block.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1526#pullrequestreview-4175428859 -> cccae3499871af83ef9943f3050916aaa45bfe5a
Disposition: FIXED
Commit: cccae3499871af83ef9943f3050916aaa45bfe5a
Evidence: This CodeRabbit review summary contained the stale latest-head evidence comment mapped above.

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
  Evidence: CodeRabbit review threads are mapped in `## Fixed in Commit Mapping`;
  GitHub thread-resolution status is tracked against those dispositions during
  the final merge cycle.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: CodeRabbit comments `discussion_r3141715407`, `discussion_r3141715409`, `discussion_r3141780565`, `discussion_r3141780570`, `discussion_r3141780571`, `discussion_r3141780573`, `discussion_r3141794105`, `discussion_r3141817225`, and review summaries `pullrequestreview-4175343676`, `pullrequestreview-4175400759`, `pullrequestreview-4175405610`, `pullrequestreview-4175411572`, and `pullrequestreview-4175428859` are mapped above with FIXED dispositions and commit evidence.
- [ ] Pre-commit green on head snapshot `4406fc0bb`
  Evidence: `pre-commit run --all-files`, commit hooks, and pre-push hooks passed for `4406fc0bb` (`ci(docker): consolidate validation path`).
- [ ] Heavy full-suite signal accepted from GitHub current-head checks
  Evidence: local `make verify` intentionally deferred under the operator-approved machine-heavy exception for this CI/tooling lane.
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: `qa-engineer-agent` completed a conditional pass with no required file changes; `bug-hunter` completed a false-green review on `9b213dfe0` with no workflow/test code edits required.

## Deferred / Follow-ups

- Docker base-image changes and API-core dependency-profile slimming remain separate follow-up candidates after build-path consolidation: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-runtime-slimming-after-build-path-consolidation`.
- Dagger remains deferred until the GitHub Actions Docker baseline is stable after this lane.
- SBOM/VEX signed security artifacts remain blocked by release-truth criteria.
