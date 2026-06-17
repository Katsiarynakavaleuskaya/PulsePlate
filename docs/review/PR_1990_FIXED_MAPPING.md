# PR 1990 Fixed Mapping

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/ee3353e7b384.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/bandit-lower-severity-inventory-baseline`
- Base: `origin/main` at `74fddbcee3d207f40703386c0f76fa66efe0fbaa`
- Operator exception: PR3 branch started while current-head `main` was pending
  with no failed jobs. Before PR open, canonical `CI` for `74fddbcee` completed
  successfully.
- Packet creation was treated as provenance only, not role execution.

## Scope

- In scope: Bandit lower-severity summary tooling, CI/security workflow warning
  output, HIGH fail-closed preservation, workflow/exclude/parser guards,
  security evidence, and backlog tracking.
- Out of scope: dependency bumps, requirements cleanup, eval/data locks, legacy
  extraction, FoodDB, auth/BOLA, frontend/iOS/macOS runtime behavior, pyproject
  migration, mass `# nosec`, and MEDIUM gate tightening.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Post-open role order executed through `qa-engineer-agent` and `bug-hunter`.
- `security-auditor`, Codex Security diff scan, and `pulseplate-pr-review`
  remain required before merge readiness.
- Codex connector review had no actionable finding in its review body.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1990#pullrequestreview-4516481618 -> d4cafeadc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1990#pullrequestreview-4516545531 -> d4cafeadc
Disposition: FIXED
Commit: d4cafeadc
Evidence: `scripts/ci/summarize_bandit_report.py` uses `_severity_sort_key`, preserves `.github/workflows` bucketing, and escapes Bandit-derived raw display fields; `scripts/ci_bandit.sh` passes `--fail-on-high`; `tests/test_summarize_bandit_report.py` covers severity ordering, `.github/workflows` bucketing, workflow-command injection, and non-strict wrapper HIGH failure; `tests/guards/test_security_devtooling_regression_guards.py` asserts `--github-annotations` workflow wiring.

## Local Role Finding Disposition

- `qa-engineer-agent`: FIXED by `d4cafeadc`.
  Evidence: equal-count severity ordering and `--github-annotations` workflow
  guard regressions were added.
- `bug-hunter`: FIXED by `d4cafeadc`.
  Evidence: non-strict wrapper HIGH failure, Bandit-derived raw output command
  injection, `.github/workflows` path bucketing, docs Phase1 anchors, and
  parser-safe mapping/body shape were fixed or are fixed in this mapping update.

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
  - Commit: `38e287899`, `d4cafeadc`
  - Evidence: `scripts/ci/summarize_bandit_report.py`,
    `scripts/ci_bandit.sh`, `tests/test_summarize_bandit_report.py`, and
    `tests/guards/test_security_devtooling_regression_guards.py`.
- Finding: the inventory could become a substitute for remediation.
  - Disposition: DEFERRED
  - Backlog:
    `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-bandit-lower-severity-remediation`
  - Evidence: `docs/security/BANDIT_LOWER_SEVERITY_INVENTORY.md`.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-5662555828dd.json`

- Status: accepted
- Shared tree: untouched
- Source diff: applied in isolated checkout
- Oracle commands:
  - `python -m pytest -q tests/test_summarize_bandit_report.py tests/guards/test_security_devtooling_regression_guards.py -k bandit`
  - `python -m pytest -q tests/test_python_supply_chain_controls.py -k bandit`
- Commit attribution: `38e287899` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Tests

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `.venv/bin/python -m pytest -q tests/test_summarize_bandit_report.py tests/guards/test_security_devtooling_regression_guards.py tests/test_python_supply_chain_controls.py tests/test_ci_workflow_pr_size_governance_contract.py`
  - 106 tests
- PASS:
  `.venv/bin/python -m pytest -q tests/guards/test_security_devtooling_regression_guards.py tests/test_python_supply_chain_controls.py`
  - 69 tests
- PASS:
  `.venv/bin/python -m pytest -q tests/test_summarize_bandit_report.py tests/guards/test_security_devtooling_regression_guards.py tests/test_python_supply_chain_controls.py`
  - 82 tests
- PASS:
  `.venv/bin/python -m pytest -q tests/test_summarize_bandit_report.py tests/guards/test_security_devtooling_regression_guards.py -k 'bandit or summarize'`
  - 17 tests
- PASS: `python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/BANDIT_LOWER_SEVERITY_INVENTORY.md docs/roadmap/BACKLOG_LEDGER.md docs/review/PR_1990_FIXED_MAPPING.md`
- PASS: `make validate-changed`
- PASS:
  `PATH=".../.venv/bin:$PATH" bash scripts/ci_bandit.sh --exclude "tests,tests_strict,htmlcov,.git,.venv,venv,node_modules,.mypy_cache,.pytest_cache" --output /tmp/bandit-report.json`
  - 0 HIGH findings and 37,577 below-HIGH grouped findings
- PASS: `pre-commit run --all-files`
- PASS: push hooks, including backend pre-push tests, full-repo Bandit
  pre-push, and docker build test

## Machine-Heavy Deferral

- Operator-approved deferral: full local `make verify` was not run for this
  CI/tooling security PR.
- Required narrow local gates above were run.
- Current-head CI is the heavy verification signal before merge.

## Security Notes

HIGH severity Bandit findings remain fail-closed. Missing or malformed Bandit
JSON fails the shared helper. LOW/MEDIUM findings remain warning-only and are
now grouped for remediation. No new suppressions or allowlist entries were
added.

## Merge Readiness

- [ ] Current-head PR CI complete and passing.
- [ ] No unresolved actionable review or bot comments.
- [ ] Post-open `security-auditor` pass complete.
- [ ] Codex Security diff scan and `pulseplate-pr-review` complete.
- [ ] Strict merge-readiness with auth passes.
- [ ] Mandatory wait-window satisfied.
