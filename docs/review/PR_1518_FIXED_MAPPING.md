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

- No actionable review comments

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
  Evidence: pending current-head CI after this mapping artifact update.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending current-head CI after this mapping artifact update.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: no review-thread resolution has been performed yet.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending post-open bot review pass.
- [x] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed before the initial push.
- [ ] `make verify` green on latest pushed head
  Evidence: attempted locally; verify-env, lint, mypy, and test-fast passed, but the full coverage stage was terminated with `Terminated: 15` before diff-cover completion.
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: post-open review packet `artifacts/orchestration/task_packets/10bed8a9d3b7.json`; local body/artifact gate `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1518 --body "$(cat /tmp/pr1518_body_current.md)"` passed; targeted regression suites passed before PR open.

## Deferred / Follow-ups

- None.
