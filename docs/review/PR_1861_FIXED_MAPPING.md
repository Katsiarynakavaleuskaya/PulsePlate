# PR #1861 - Fixed in Commit Mapping

**Title:** `test: stabilize KPP xdist collection`
**Branch:** `codex/nightly-xdist-security-outcomes-order`
**Scope:** Stabilize pytest-xdist collection order for the Experiment Runner KPP
security-sensitive header test.
**Primary commit:** `59f94a63e`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Implementation Evidence

Disposition: FIXED
Commit: `59f94a63e`
Evidence: `tests/test_experiment_slack_kpp_renderer.py` now derives
`SECURITY_SENSITIVE_OUTCOME_CASES` with deterministic ordering before pytest
parametrization, while production `SECURITY_SENSITIVE_OUTCOMES` remains a
`frozenset`.

## Role-Agent / Premortem Pass

- `agent-coordinator` - completed; decision: complete mandatory role passes
  before implementation, keep scope test-only, and leave Trivy #602 out of
  scope.
- `dev-operator` - completed; validation plan required hash-seed collection,
  xdist execution, `make validate-changed`, and `pre-commit run --all-files`.
- `architecture-specialist` - completed; required test-only deterministic
  parametrization and preserving the production renderer contract.
- `qa-engineer-agent` - completed; required fixed hash-seed collection checks,
  xdist checks, full renderer module validation, and no skips or xfails.
- `bug-hunter` - completed; confirmed the root cause as direct parametrization
  from a `frozenset` and classified the low coverage result as downstream
  collection-abort fallout.
- `security-auditor` - completed; approved only a test-only stable
  parametrization with unchanged security-sensitive membership and no Trivy
  scope expansion.
- `cursor-specialist-agent` - completed; confirmed no `.cursor/agents`, memory,
  or workflow instruction update is needed for this narrow fix.
- `pulseplate-premortem-risk-review` - completed; decision: proceed. The xdist
  collection risk is FIXED by focused validation, and the production membership
  and Trivy scope risks are NOT-A-BUG for this PR.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/b2abaffcd011.json`
- Branch start: synced `main` at `4d47c3b97`, then created
  `codex/nightly-xdist-security-outcomes-order`.
- Colleague-owned `.cursor/agents/*.md` edits were stashed before branch work
  and are not part of this PR.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/artifacts/orchestration/experiments/nightly-xdist-security-outcomes-oracle-packet.json`.
- Artifact: `artifacts/orchestration/experiments/results/nightly-xdist-security-outcomes-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`.
- Result: accepted; 2/2 oracle commands passed; shared tree untouched;
  `mutated_paths=[]`; `source_diff_paths=["tests/test_experiment_slack_kpp_renderer.py"]`;
  `coauthor_required=true`.
- Commit trailer used:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` on
  `59f94a63e`.
- Squash-merge note: preserve
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` in the final
  merge commit message.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path tests/test_experiment_slack_kpp_renderer.py --path scripts/orchestration/experiment_slack_kpp_renderer.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `PYTHONHASHSEED=0 .venv/bin/python -m pytest --collect-only -vv tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers` - PASS.
- `PYTHONHASHSEED=1 .venv/bin/python -m pytest --collect-only -vv tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers` - PASS.
- `PYTHONHASHSEED=3 .venv/bin/python -m pytest --collect-only -vv tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers` - PASS.
- `.venv/bin/python -m pytest -q tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_outcomes_frozen` - PASS.
- `PYTHONHASHSEED=0 .venv/bin/python -m pytest -q -n 2 --dist=loadscope tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_outcomes_frozen` - PASS.
- `PYTHONHASHSEED=1 .venv/bin/python -m pytest -q -n 2 --dist=loadscope tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_outcomes_frozen` - PASS.
- `.venv/bin/python -m pytest -q -n 4 --dist=loadscope tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers` - PASS.
- `.venv/bin/python -m pytest -q tests/test_experiment_slack_kpp_renderer.py` - PASS.
- `make validate-changed` - PASS after commit.
- `pre-commit run --all-files` - PASS.
- Pre-push hooks - PASS, including pip-audit, backend tests, full-repo bandit,
  and Docker build skip for no Docker changes.

## Machine-Heavy Gate Deferral

Full local `make verify` was started and passed `verify-env`, lint, mypy, and
`test-fast`, then entered the full coverage suite via
`coverage run -m pytest -q`. It was stopped at roughly 3% suite progress under
the operator-approved machine-heavy exception. This artifact does not claim
local full-verify readiness.

Merge readiness still requires current-head CI parity, post-open role passes,
Codex Security diff scan, no unresolved review threads, no actionable bot
findings, strict merge-readiness checks, and the mandatory wait-window.
