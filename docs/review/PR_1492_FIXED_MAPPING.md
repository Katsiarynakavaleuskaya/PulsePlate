# PR #1492 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1492#discussion_r3123468456 -> 8f0e04ff4a47625e33b06e43cc1672718927ab96
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1492#discussion_r3123470365 -> 8f0e04ff4a47625e33b06e43cc1672718927ab96
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1492#discussion_r3123483703 -> 8f0e04ff4a47625e33b06e43cc1672718927ab96
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1492#discussion_r3123483729 -> 8f0e04ff4a47625e33b06e43cc1672718927ab96
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1492#discussion_r3123483739 -> 8f0e04ff4a47625e33b06e43cc1672718927ab96
Disposition: FIXED
Commit: 8f0e04ff4a47625e33b06e43cc1672718927ab96
Evidence: `scripts/ci/fetch_docker_image_baseline.py:19`, `scripts/ci/fetch_docker_image_baseline.py:47`, `scripts/ci/fetch_docker_image_baseline.py:153`, `scripts/ci/fetch_docker_image_baseline.py:229`, `scripts/ci/docker_image_telemetry.py:258`, `tests/test_fetch_docker_image_baseline.py:169`, `docs/deploy/DOCKER.md:141`, `docs/roadmap/BACKLOG_LEDGER.md:645`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1492#discussion_r3123483705 -> 2b9b969b95dcfb3a3ffce692ac29f37ba2247a51
Disposition: FIXED
Commit: 2b9b969b95dcfb3a3ffce692ac29f37ba2247a51
Evidence: `docs/review/PR_1492_FIXED_MAPPING.md:23`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1492#discussion_r3123568932 -> 4bab743e4c3cab9ad57ebcb3ea7f747db6fda24c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1492#discussion_r3123568939 -> 4bab743e4c3cab9ad57ebcb3ea7f747db6fda24c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1492#discussion_r3123568960 -> 4bab743e4c3cab9ad57ebcb3ea7f747db6fda24c
Disposition: FIXED
Commit: 4bab743e4c3cab9ad57ebcb3ea7f747db6fda24c
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:645`, `scripts/ci/docker_image_telemetry.py:265`, `scripts/ci/fetch_docker_image_baseline.py:281`, `tests/test_docker_image_telemetry.py:109`.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: pending after remediation head and current review-cycle reruns.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending after remediation head and current review-cycle reruns.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending current remediation for open review threads.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending current remediation for open CodeRabbit/Sourcery/Codex findings.
- [ ] Pre-commit green on latest pushed head
  Evidence: pending after remediation head is committed.
- [ ] `make verify` green on latest pushed head
  Evidence: not run for this lane; GitHub current-head checks remain the heavy signal.

## Deferred / Follow-ups

- hard image-size budget cap / failure threshold
- `docs/roadmap/BACKLOG_LEDGER.md` line 540 (`P1: Shared Safety audit script after install-profile split`)
- provenance / attestation recovery
- Dagger or alternate control-plane work
