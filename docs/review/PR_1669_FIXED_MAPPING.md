# PR #1669 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1669
Branch: `test/security-devtooling-regression-guards`
Title: `test(guards): add regression guards for dev tooling and eval artifact safety`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Sourcery high-level review feedback was reviewed and mapped below. CodeRabbit
reported no actionable comments, and Cubic reported no issues.

Role order used:

1. `agent-coordinator`
2. `architecture-specialist`
3. `security-auditor`
4. `dev-operator`
5. `qa-engineer-agent`
6. `bug-hunter`

Premortem frame applied before code freeze:

> It is 48 hours after PR-5 merged. Another Codex security finding appears for
> the same class of issue. Why did our new guard layer fail?

In-scope premortem fixes applied:

- Dynamic malicious-worktree Makefile probe instead of text-only shell guard.
- Registry-backed optional RAG/vector dependency assertions across security surfaces.
- Source-level invariant that predictable judgment sidecars use `_safe_write_text()`.
- Eval validator guard against coercive casts and mutable aliasing regressions.
- Diff-scoped docs path leakage guard to avoid historical `/Users/...` false positives.
- Sourcery feedback hardened the guard implementation itself: source checks now
  use AST-backed function extraction instead of brittle string slicing, and docs
  diff base selection is configurable with local fallbacks.

## Review Evidence

### Preventive guard implementation

Disposition: FIXED
Commit: c0cdf1ba2
Evidence:

- `tests/guards/test_security_devtooling_regression_guards.py` adds focused preventive guards.
- `AGENTS.md` and `scripts/AGENTS.md` document eval/dev-tooling regression policy.
- `docs/DEPENDENCY_MANAGEMENT.md` documents the optional RAG/vector profile security coverage registry.

### Local gate false-positive correction

Disposition: FIXED
Commit: 2194a3a3a
Evidence:

- `make validate-changed` exposed that the new docs leakage guard blocked the intentional placeholder `/Users/...` in policy text.
- `tests/guards/test_security_devtooling_regression_guards.py` now uses a local absolute path regex that allows the placeholder while still rejecting real machine-local absolute paths.

### Mapping artifact update

Disposition: FIXED
Commit: 9045512ee
Evidence:

- `docs/review/PR_1669_FIXED_MAPPING.md` records the PR-numbered governance artifact and local gate evidence.

### Sourcery guard robustness review

Disposition: FIXED
Commit: f8f7c5796
Evidence:

- `tests/guards/test_security_devtooling_regression_guards.py` now extracts guarded writer functions through `ast.FunctionDef` line spans instead of `str.index`.
- `tests/guards/test_security_devtooling_regression_guards.py` now supports `PULSEPLATE_DOCS_LEAKAGE_GUARD_BASE` and falls back across available local git refs before diffing docs changes.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: f8f7c5796
Evidence: `tests/guards/test_security_devtooling_regression_guards.py` replaces brittle source slicing and hard-coded docs diff base behavior in response to Sourcery review feedback.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1669#pullrequestreview-4230017026 -> f8f7c5796
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1669#discussion_r3190144728 -> f8f7c5796

## Merge Readiness

Local gates run before opening PR:

- `python3 scripts/orchestration/check_preflight.py` -> PASS
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS
- `. .venv/bin/activate && python -m pytest -q tests/guards/test_security_devtooling_regression_guards.py tests/test_makefile_dev_python_migration.py tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py tests/test_ci_risk_profile.py tests/evals/test_judgment_validity_sidecar.py tests/evals/test_eval_validity_contract.py` -> PASS
- `pre-commit run --all-files` -> PASS after black reformatted `tests/guards/test_security_devtooling_regression_guards.py` and the hook was rerun cleanly
- `make validate-changed` -> PASS; after commit it ran `tests/guards/test_security_devtooling_regression_guards.py` and reported `10 passed`
- `. .venv/bin/activate && python -m pytest -q tests/guards/test_security_devtooling_regression_guards.py` -> PASS after Sourcery robustness fix; reported `10 passed`
- `pre-commit run --all-files` -> PASS after Sourcery robustness fix
- `make validate-changed` -> PASS after Sourcery robustness fix; reported `10 passed`
- Push pre-push hooks -> PASS, including `pip-audit`, backend pre-push pytest, full-repo Bandit, and docker build test where path filters attached it

Full local `make verify` was not run by operator-approved machine-heavy exception
for guard/CI tooling PRs. Heavy-suite parity must come from current-head GitHub
sharded CI plus strict merge-readiness wrapper before merge.

Pending before merge readiness claim:

- Current-head GitHub CI complete and passing.
- CodeRabbit/Cubic/Sourcery no-actionables confirmed.
- `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1669` passes.
- `python3 scripts/orchestration/check_merge_ready.py --require-auth --pr-number 1669 --repo Katsiarynakavaleuskaya/PulsePlate` passes.

## Deferred / Follow-ups

No deferred code changes in this PR.

If future optional dependency profiles expand beyond `requirements-rag-vector*`,
the security profile registry can be generalized in a separate coordinator-owned
guard lane instead of widening this PR.
