<!-- markdownlint-disable MD034 -->
# PR 1477 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below; resolve conversations on GitHub after mapping.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: `019f002e02d9e6fab89574b89633de191b53b409`
Evidence: `scripts/ci/docker_image_telemetry.py:23-25`; `scripts/ci/docker_image_telemetry.py:77-93`; `scripts/ci/docker_image_telemetry.py:187-219`; `.github/workflows/build.yml:65-90`; `.github/workflows/docker-image.yml:53-78`; `.github/workflows/trivy.yml:64-94`; `tests/test_docker_image_telemetry.py:43-95`; `tests/test_python_supply_chain_controls.py:207-226`
Reason: The remaining review delta is now fixed on-branch: docker CLI calls are timeout-bounded, JSON-array `COPY` inputs are included in telemetry evidence, shell-form `COPY` assumptions are documented in code, the Docker telemetry workflows now honor the backlog's warning/regression-only contract, and the Trivy apt install step now uses `set -euo pipefail`. This closes the concrete Sourcery and CodeRabbit follow-ups, and it closes the remaining workflow-contract issues originally identified by cubic.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#pullrequestreview-4135809211 -> 019f002e02d9e6fab89574b89633de191b53b409
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#pullrequestreview-4135810855 -> 019f002e02d9e6fab89574b89633de191b53b409
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#pullrequestreview-4135812976 -> 019f002e02d9e6fab89574b89633de191b53b409
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#pullrequestreview-4135818093 -> 019f002e02d9e6fab89574b89633de191b53b409
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#discussion_r3106664624 -> 019f002e02d9e6fab89574b89633de191b53b409
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#discussion_r3106669576 -> 019f002e02d9e6fab89574b89633de191b53b409
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#discussion_r3106669577 -> 019f002e02d9e6fab89574b89633de191b53b409
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#discussion_r3106669582 -> 019f002e02d9e6fab89574b89633de191b53b409

Disposition: FIXED
Commit: `d3fd45f4d1f09b144632fc1c81798fed9d4a0ba3`
Evidence: `Dockerfile:194-221`; `tests/test_python_supply_chain_controls.py:194-203`
Reason: The production-stage Dockerfile now temporarily switches back to `USER root` only for the pip-removal block and then returns to `USER pulseplate`, which resolves the real runtime-break risk identified by cubic and also removes the malformed heredoc/`RUN` layout that CodeRabbit flagged on the same block.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#discussion_r3106666747 -> d3fd45f4d1f09b144632fc1c81798fed9d4a0ba3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#discussion_r3106669575 -> d3fd45f4d1f09b144632fc1c81798fed9d4a0ba3

Disposition: FIXED
Commit: `2805c4243e67716c3d25845542d017c67f916592`
Evidence: `scripts/ci/docker_image_telemetry.py:96-119`; `tests/test_docker_image_telemetry.py:62-74`
Reason: cubic found that Docker history sizes like `65.4kB`/`12MB` could be misparsed; the helper now normalizes Docker-style unit aliases before conversion and the new regression test locks that behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#discussion_r3106664334 -> 2805c4243e67716c3d25845542d017c67f916592
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1477#discussion_r3106669572 -> 2805c4243e67716c3d25845542d017c67f916592

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`

### Local validation evidence

- [x] `pre-commit run --all-files`
- [x] `make lint`
- [x] `make typecheck`
- [x] `make test-fast`
- [x] Targeted telemetry and supply-chain tests
- [x] Accelerated full-suite coverage plus `diff-cover` equivalent completed
- [ ] Canonical local `make verify`
  Evidence: `AGENTS.md:8-20`; `AGENTS.md:492-500`
  Reason: the canonical local gate remains unchecked in this artifact, so merge truth must still come from current-head CI rather than any partial local substitute.
<!-- markdownlint-enable MD034 -->
