# PR 1990 Fixed Mapping

## Lane Start Provenance

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1990
- Branch: `codex/bandit-lower-severity-inventory-baseline`
- Base: `origin/main` at `74fddbcee3d207f40703386c0f76fa66efe0fbaa`
- Starter packet: `artifacts/orchestration/task_packets/ee3353e7b384.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Operator exception: PR3 branch started while current-head `main` was pending
  with no failed jobs. Before PR open, canonical `CI` for `74fddbcee` completed
  successfully.

## Scope

This PR is limited to Bandit lower-severity inventory reporting:

- shared Bandit JSON summary helper,
- CI/security workflow wiring for grouped warning output,
- HIGH fail-closed preservation,
- workflow/parser/exclude guard coverage,
- security evidence and backlog tracking for phased remediation.

Out of scope: dependency bumps, requirements cleanup, eval/data locks, legacy
extraction, FoodDB, auth/BOLA, frontend/iOS/macOS runtime behavior, pyproject
migration, mass `# nosec`, and MEDIUM gate tightening.

## Discussion Thread Pass

No GitHub review threads existed when this artifact was created.

Post-open review order remains required before merge readiness:

1. `qa-engineer-agent`
2. `bug-hunter`
3. `security-auditor`
4. Codex Security diff scan
5. CodeRabbit, if authenticated
6. `pulseplate-pr-review`

## Premortem Closure

- Finding: scheduled Security Scan could keep stale inline parsing and create
  false-green Bandit evidence.
  - Disposition: FIXED
  - Commit: `38e287899`
  - Evidence: `.github/workflows/security.yml` uses
    `scripts/ci/summarize_bandit_report.py`.
- Finding: lower-severity reporting could accidentally weaken HIGH fail-closed
  behavior.
  - Disposition: FIXED
  - Commit: `38e287899`
  - Evidence: `scripts/ci/summarize_bandit_report.py`,
    `tests/test_summarize_bandit_report.py`, and
    `tests/guards/test_security_devtooling_regression_guards.py`.
- Finding: the inventory could become a substitute for remediation.
  - Disposition: DEFERRED
  - Backlog:
    `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-bandit-lower-severity-remediation`
  - Evidence: `docs/security/BANDIT_LOWER_SEVERITY_INVENTORY.md`.

## Experiment Runner Evidence

- Accepted artifact:
  `artifacts/orchestration/experiments/results/exp-5662555828dd.json`
- Status: accepted
- Shared tree: untouched
- Source diff: applied in isolated checkout
- Oracle commands:
  - `python -m pytest -q tests/test_summarize_bandit_report.py tests/guards/test_security_devtooling_regression_guards.py -k bandit`
  - `python -m pytest -q tests/test_python_supply_chain_controls.py -k bandit`
- Commit attribution: `38e287899` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Fixed in Commit Mapping

- Initial implementation -> `38e287899`
- Premortem false-green Security Scan parser finding -> `38e287899`
- Premortem HIGH fail-closed preservation finding -> `38e287899`
- Premortem lower-severity remediation backlog finding -> `38e287899`

## Tests

- `python3 scripts/orchestration/check_preflight.py` - pass
- `python3 scripts/orchestration/check_agent_consistency.py` - pass
- `.venv/bin/python -m pytest -q tests/test_summarize_bandit_report.py tests/guards/test_security_devtooling_regression_guards.py tests/test_python_supply_chain_controls.py tests/test_ci_workflow_pr_size_governance_contract.py`
  - pass, 106 tests
- `.venv/bin/python -m pytest -q tests/guards/test_security_devtooling_regression_guards.py tests/test_python_supply_chain_controls.py`
  - pass, 69 tests
- `make validate-changed`
  - pass; selected the changed Bandit/security test surface after commit
- `PATH=".../.venv/bin:$PATH" bash scripts/ci_bandit.sh --exclude "tests,tests_strict,htmlcov,.git,.venv,venv,node_modules,.mypy_cache,.pytest_cache" --output /tmp/bandit-report.json`
  - pass; 0 HIGH findings and 37,577 below-HIGH grouped findings
- `pre-commit run --all-files` - pass
- Push hooks - pass, including backend pre-push tests, full-repo Bandit
  pre-push, and docker build test

## Machine-Heavy Deferral

Operator-approved exception: full local `make verify` was not run for this
CI/tooling security PR. Narrow local gates, pre-commit, pre-push hooks,
Experiment Runner oracle evidence, and current-head CI are the validation
signals for this lane.

## Security Notes

HIGH severity Bandit findings remain fail-closed. Missing or malformed Bandit
JSON fails the shared helper. LOW/MEDIUM findings remain warning-only and are
now grouped for remediation. No new suppressions or allowlist entries were
added.

## Merge Readiness

Not merge-ready at artifact creation. Required before merge:

- current-head PR CI complete and passing,
- no unresolved actionable review or bot comments,
- post-open role passes complete,
- Codex Security diff scan and `pulseplate-pr-review` complete,
- strict merge-readiness with auth passes,
- mandatory wait-window satisfied.
