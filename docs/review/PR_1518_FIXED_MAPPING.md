# PR #1518 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact was created immediately after the PR was opened per repo
governance. Record every actionable human/bot disposition here before resolving
threads on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1518#pullrequestreview-4172051984
  Disposition: NOT-A-BUG
  Evidence: `scripts/ci/check_docker_provenance_attestation.py:22`; `docs/deploy/DOCKER.md:128`; `tests/test_check_docker_provenance_attestation.py:105`.
  Reason: This lane intentionally preserves fail-closed exact-predicate verification for the GitHub/GHCR SPDX SBOM predicate observed in the failing main CD run. Making the predicate configurable would widen deploy-policy surface beyond this narrow main-stabilization fix and belongs in a separately governed policy-change PR if needed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1518#pullrequestreview-4172295944
  Disposition: NOT-A-BUG
  Evidence: Current-head GitHub CI for `5b393083a3ea5c824c1629b5ce1def5a3c101198` passed PR tests, coverage, lint, security, and diff coverage; manual `/review` found no P0/P1/P2 code issues.
  Reason: Sourcery reported a weekly account rate limit, not a code or documentation defect in this PR. The earlier Sourcery code suggestion is mapped above with a disposition.

## Implementation Evidence

Commit: cf55a9f4e
Evidence: `pytest -q tests/test_check_docker_provenance_attestation.py` -> 12 passed; `pytest -q tests/test_check_docker_provenance_attestation.py tests/test_python_supply_chain_controls.py` -> 54 passed; live GHCR proof verified the failed main digest with predicate `https://spdx.dev/Document/v2.3`.
Reason: `main` CD run `24892330541` failed because the verifier expected the unversioned SPDX predicate `https://spdx.dev/Document`, while GitHub-signed SPDX SBOM attestations for the pushed image use the versioned predicate `https://spdx.dev/Document/v2.3`.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Mandatory wait-window satisfied (final check pass completed, then waited >=1 review cycle after latest bot/review activity)
  Evidence: pending post-open review cycle.
- [ ] Current-head CI is green for PR branch head
  Evidence: pending current-head CI after this mapping artifact update; previous current-head pass had only `test-pr (3.13)` still in progress.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending current-head CI after this mapping artifact update; previous current-head pass had only `test-pr (3.13)` still in progress.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: no review-thread resolution has been performed yet.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: Sourcery high-level configurability comment and Sourcery weekly rate-limit review are mapped above as NOT-A-BUG; CodeRabbit status is PASS and its latest comment reports only account rate limiting, with no code findings.
- [x] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed before the initial push.
- [ ] `make verify` green on latest pushed head
  Evidence: full local `make verify`/full diff-cover intentionally not re-run for this lane by operator decision to avoid duplicating the 10k-test workload locally; local evidence is limited to PR-specific tests and PR-specific diff-cover, with GitHub current-head CI as the heavy signal.
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: post-open review packet `artifacts/orchestration/task_packets/10bed8a9d3b7.json`; local body/artifact gate `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1518 --body "$(cat /tmp/pr1518_body_current.md)"` passed; targeted regression suites passed before PR open.

## Deferred / Follow-ups

- None.
