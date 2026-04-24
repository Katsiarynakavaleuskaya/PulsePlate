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

- No actionable review comments

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Mandatory wait-window satisfied
  Evidence: pending post-open review/CI cycle on PR `#1515`.
- [ ] Current-head CI is green for PR branch head
  Evidence: pending current-head GitHub checks after artifact commit.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending current-head GitHub checks after artifact commit.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending post-open review pass.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending CodeRabbit and bot review cycle.
- [ ] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed before initial push; must be
  rerun after artifact commit.
- [ ] `make verify` green on latest pushed head
  Evidence: pending final hard gate before merge claim.
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: `qa-engineer-agent` pass completed and findings fixed in commit `bf8d5297d`; `bug-hunter` still pending after the follow-up push.

Post-open QA notes:

- `qa-engineer-agent` found `.github/scripts/parse-safety-report.py` could trip
  E402 after adding the repo-root import path; fixed in commit `bf8d5297d`.
- `qa-engineer-agent` found `scripts/ci/run_safety_audit.py` could parse stale
  per-manifest JSON if Safety failed before overwriting a prior report; fixed
  in commit `bf8d5297d` and covered by `test_run_audit_removes_stale_report_before_safety_execution`.
- QA fix evidence: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py` -> 55 passed; `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/flake8 .github/scripts/parse-safety-report.py scripts/ci/run_safety_audit.py` -> passed.

## Deferred / Follow-ups

- Docker workflow build-path consolidation / reuse image digest from the analyst
  report remains a separate follow-up candidate after this Safety slice.
- Dagger remains deferred until Docker baseline/provenance work stays stable.
- SBOM/VEX signed security artifacts remain blocked by release-truth criteria.
