# PR #2049 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2049

Branch: `codex/fix-main-creative-telemetry-py313`

## Summary

This PR fixes the Python 3.13 main-CI creative-code telemetry import-isolation
test by moving the runtime-boundary assertion into a fresh interpreter. The
production contract is unchanged: importing `scripts.orchestration.creative_code_telemetry`
must not import `scripts.orchestration.creative_code_pr_promotion`.

## Scope

- Update `tests/test_creative_code_telemetry.py`.
- Replace the parent-process `sys.modules` assertion with a subprocess probe
  using `sys.executable`.
- Keep the child probe limited to importing
  `scripts.orchestration.creative_code_telemetry` and checking the child
  interpreter's `sys.modules`.

## Out Of Scope

No production orchestration code, PR promotion runtime behavior, import-boundary
weakening, `sys.modules` mutation, local full `make verify`, or unrelated
creative-code PR-5 work is in scope.

## Implementation Commits

- `788282272` - isolate the creative-code telemetry import-boundary test in a
  fresh interpreter and keep subprocess diagnostics bounded.

## Lane Start Provenance

- Base branch: `main`
- Branch: `codex/fix-main-creative-telemetry-py313`
- Base commit: `71af9d208b26435352fc821b79a2d78cebb319f5`
- Packet: `artifacts/orchestration/task_packets/192b00bc8106.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Pre-open role order executed:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> architecture-specialist`
- Packet creation was treated as provenance/routing only; role passes were
  executed explicitly before implementation.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Initial Review-State Notes

No actionable code review threads existed when this artifact was created. The
issue-level Codex, CodeRabbit, and Sourcery messages reported usage or review
limits rather than code defects. They remain external review-cap blockers for
merge readiness, not test-fix defects.

## Post-Open Role Review Evidence

Disposition: NOT-A-BUG

Finding: The mandatory post-open role passes did not report any required code
or security fix for the scoped test change.

Evidence:

- `qa-engineer-agent`: PASS for QA adequacy. It confirmed the fresh-interpreter
  probe covers the collection-order contamination from
  `tests/test_creative_code_pr_promotion.py`.
- `bug-hunter`: PASS at code level. It identified no required test fix; the
  only code-level caveat was non-blocking timeout diagnostic polish.
- `security-auditor`: PASS. It confirmed the subprocess posture uses
  `sys.executable`, argv-list execution, no shell, no `# nosec`, bounded output,
  and no production guard weakening.

## Premortem Finding Closure

Disposition: FIXED

Finding: The hotfix could false-green by cleaning or depending on the parent
pytest interpreter state instead of proving the telemetry import contract.

Evidence: `tests/test_creative_code_telemetry.py` now runs the import-boundary
probe in a fresh interpreter and does not mutate `sys.modules`.

Disposition: FIXED

Finding: The subprocess probe could violate repo subprocess policy.

Evidence: The test uses `[sys.executable, "-c", probe]`, no shell, no `# nosec`,
and the focused guard run
`tests/guards/test_subprocess_uses_absolute_binaries.py tests/guards/test_nosec_policy_guard.py`
passed.

Disposition: FIXED

Finding: Branch-scoped validation could false-pass before the file was committed.

Evidence: `make validate-changed` was rerun after commit `788282272`; it
selected `tests/test_creative_code_telemetry.py` and ran 13 tests successfully.

## Experiment Runner Evidence

- Runner mode: `oracle_only_governance_reviewer`
- Experiment ID: `exp-8142bcb7a773`
- Artifact: `artifacts/orchestration/experiments/results/creative-telemetry-py313-oracle.json`
- Status: accepted
- Shared tree untouched: true
- Mutated paths: []
- Source diff paths: `tests/test_creative_code_telemetry.py`
- Oracle commands:
  - `python -m pytest -q tests/test_creative_code_pr_promotion.py tests/test_creative_code_telemetry.py::test_telemetry_import_does_not_load_promotion_runtime_module -p no:cacheprovider` -> exit 0
  - `python -m pytest -q tests/guards/test_subprocess_uses_absolute_binaries.py tests/guards/test_nosec_policy_guard.py` -> exit 0
- Co-author trailer required and included in implementation commit:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Local Validation Evidence

- PASS: `env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/test_creative_code_pr_promotion.py tests/test_creative_code_telemetry.py::test_telemetry_import_does_not_load_promotion_runtime_module -p no:cacheprovider`
- PASS: `env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/test_creative_code_telemetry.py tests/test_creative_code_pr_promotion.py -p no:cacheprovider`
- PASS: `env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/guards/test_subprocess_uses_absolute_binaries.py tests/guards/test_nosec_policy_guard.py`
- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS during push hooks: `pip-audit`, backend pre-push pytest, and full-repo
  Bandit.
- Not run: local full `make verify`, per repo budget rule and operator request.
