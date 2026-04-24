# PR #1515 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 87651c7b6
Evidence: `python -m pytest -q tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py` -> 59 passed; `pre-commit run --all-files` -> passed. The fix validates Safety JSON object shape, writes deterministic summaries on missing reports and schema drift, fails closed on non-zero Safety exits without parsed findings, and removes the absolute local Python path from the task packet.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1515#discussion_r3137934491 -> 87651c7b6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1515#discussion_r3137934498 -> 87651c7b6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1515#discussion_r3137934504 -> 87651c7b6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1515#pullrequestreview-4170706538 -> 87651c7b6

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Mandatory wait-window satisfied
  Evidence: pending post-open review/CI cycle on PR `#1515`.
- [ ] Current-head CI is green for PR branch head
  Evidence: pending current-head GitHub checks after mapping update.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending current-head GitHub checks after mapping update.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending post-open review pass.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: CodeRabbit review summary `pullrequestreview-4170706538` mapped to
  the same FIXED commit as the three inline comments.
- [ ] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed before initial push; must be
  rerun after artifact commit.
- [ ] Heavy full-suite signal accepted from GitHub current-head checks
  Evidence: local `make verify` was intentionally stopped after user direction
  to avoid agent-side 90-minute machine load; targeted PR-surface pytest and
  pre-commit remain the local gates for this lane.
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: `qa-engineer-agent` pass completed and findings fixed in commit `bf8d5297d`; `bug-hunter` pass completed and findings fixed in commit `87651c7b6`.

Post-open QA notes:

- `qa-engineer-agent` found `.github/scripts/parse-safety-report.py` could trip
  E402 after adding the repo-root import path; fixed in commit `bf8d5297d`.
- `qa-engineer-agent` found `scripts/ci/run_safety_audit.py` could parse stale
  per-manifest JSON if Safety failed before overwriting a prior report; fixed
  in commit `bf8d5297d` and covered by `test_run_audit_removes_stale_report_before_safety_execution`.
- QA fix evidence: `python -m pytest -q tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py` -> 55 passed; `python -m flake8 .github/scripts/parse-safety-report.py scripts/ci/run_safety_audit.py` -> passed.
- `bug-hunter` found non-object Safety JSON, missing-report summaries, and
  non-zero Safety exits without parsed findings were not all fail-closed with
  deterministic evidence; fixed in commit `87651c7b6`.

## Deferred / Follow-ups

- Docker workflow build-path consolidation / reuse image digest from the analyst
  report remains a separate follow-up candidate after this Safety slice.
- Dagger remains deferred until Docker baseline/provenance work stays stable.
- SBOM/VEX signed security artifacts remain blocked by release-truth criteria.
