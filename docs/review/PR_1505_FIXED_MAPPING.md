# PR #1505 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1505>
Branch: `codex/main-py312-containment`
Date: 2026-04-23

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- Status: CodeRabbit review comments are dispositioned below before thread
  resolution.
- Current implementation commit: `d9fa18f42`.
- Bot-comment fix commit: `6c7611074`.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1505#discussion_r3131238664
Disposition: NOT-A-BUG
Evidence: `.github/workflows/ci.yml:1021`; `.github/workflows/ci.yml:1023`; `.github/workflows/ci.yml:1103`; `tests/test_ci_workflow_pr_size_governance_contract.py:216`; `docs/orchestration/MAIN_CI_PY312_CONTAINMENT_PACKET_2026-04-23.md:37`
Reason: the requested alternatives would change the accepted lane contract: splitting adds matrix/topology surface, and increasing the timeout would change the required-check display identity away from `test-main (3.12, 60)`. This PR intentionally preserves the existing matrix identity and contains only xdist exposure for Python 3.12.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1505#discussion_r3131238679 -> 6c7611074
Disposition: FIXED
Commit: 6c7611074
Evidence: `docs/orchestration/MAIN_CI_PY312_CONTAINMENT_PACKET_2026-04-23.md:5` now avoids committing a machine-specific absolute path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1505#discussion_r3131238691 -> 6c7611074
Disposition: FIXED
Commit: 6c7611074
Evidence: `docs/review/PR_1505_FIXED_MAPPING.md:9` and `docs/review/PR_1505_FIXED_MAPPING.md:10` now include the required checked Discussion Thread Pass entries.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1505#discussion_r3131238703 -> 6c7611074
Disposition: FIXED
Commit: 6c7611074
Evidence: `docs/review/PR_1505_FIXED_MAPPING.md:55` now records the Merge Readiness wait-window gate.

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `. .venv/bin/activate && pytest -q tests/test_ci_workflow_pr_size_governance_contract.py::test_main_branch_xdist_fallback_stays_scoped_to_unstable_interpreters` PASS.
- `pre-commit run --all-files` PASS.
- `make validate-changed` PASS: no changed Python files.
- `make verify` attempted: verify-env, flake8, mypy, and smoke tests passed;
  diff-cov full pytest terminated with `make: *** [diff-cov] Terminated: 15`
  around 22%, so PR #1505 remains draft/not merge-ready pending current-head CI.

## Deferred Follow-up

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-py312-xdist-root-cause-hardening`
  tracks root-cause xdist hardening after this containment lane.

## Merge Readiness

- [ ] Final check pass completed after latest bot/review activity.
- [ ] Waited at least one review cycle before merge.
- Latest bot/review activity currently tracked: CodeRabbit review comments at
  2026-04-23T13:44:14Z.
- Required wait-window rule: after the latest bot/review activity, perform one
  final check pass and wait at least one review cycle before merge.
