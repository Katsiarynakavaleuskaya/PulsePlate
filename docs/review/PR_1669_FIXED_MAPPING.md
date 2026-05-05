# PR #1669 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1669
Branch: `test/security-devtooling-regression-guards`
Title: `test(guards): add regression guards for dev tooling and eval artifact safety`

## Summary

Preventive guard PR for the security/dev-tooling regression classes found across
PR #1664, PR #1665, PR #1666, and PR #1667.

Scope is guard/tests/docs only:

- Makefile compose project-name shell-safety regression guard.
- Optional RAG/vector dependency-profile security coverage guard.
- Eval sidecar symlink-safe fail-closed write guard.
- Eval validity strict validation and defensive-copy guard.
- Diff-scoped docs local `/Users/...` path leakage guard.
- Minimal AGENTS/dependency policy documentation.

## Discussion Thread Pass

No external review threads existed at PR open time.

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

## Fixed in Commit Mapping

### Preventive guard implementation

Disposition: FIXED
Commit: c0cdf1ba2
Evidence:

- `tests/guards/test_security_devtooling_regression_guards.py` adds focused preventive guards.
- `AGENTS.md` and `scripts/AGENTS.md` document eval/dev-tooling regression policy.
- `docs/DEPENDENCY_MANAGEMENT.md` documents the optional RAG/vector profile security coverage registry.

Thread mapping:

- Pre-open preventive PR; no review thread URL to map.

### Local gate false-positive correction

Disposition: FIXED
Commit: 2194a3a3a
Evidence:

- `make validate-changed` exposed that the new docs leakage guard blocked the
  intentional placeholder `/Users/...` in policy text.
- `tests/guards/test_security_devtooling_regression_guards.py` now uses a
  local absolute path regex that allows the placeholder while still rejecting
  real `/Users/<name>/...` paths.

Thread mapping:

- Local pre-push gate finding; no review thread URL to map.

## Merge Readiness

Local gates run before opening PR:

- `python3 scripts/orchestration/check_preflight.py` -> PASS
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS
- `. .venv/bin/activate && python -m pytest -q tests/guards/test_security_devtooling_regression_guards.py tests/test_makefile_dev_python_migration.py tests/test_run_safety_audit.py tests/test_python_supply_chain_controls.py tests/test_ci_risk_profile.py tests/evals/test_judgment_validity_sidecar.py tests/evals/test_eval_validity_contract.py` -> PASS
- `pre-commit run --all-files` -> PASS after black reformatted `tests/guards/test_security_devtooling_regression_guards.py` and the hook was rerun cleanly
- `make validate-changed` -> PASS; after commit it ran `tests/guards/test_security_devtooling_regression_guards.py` and reported `10 passed`
- Push pre-push hooks -> PASS, including `pip-audit`, backend pre-push pytest, full-repo Bandit, and docker build test

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
