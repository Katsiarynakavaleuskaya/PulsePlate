# PR 1595 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1595
- Branch: `codex/design-export-lock-and-manifest-hardening`
- Scope: PR-7 Design Export Lock And Manifest Hardening

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- Status: Draft PR opened for CodeRabbit / bot / human review.
- Review threads resolved by this artifact: none yet.
- Actionable review comments: pending review intake.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 646121873
Evidence: `scripts/design_guard.py` validates locked `core_lock.path` through the repo-relative path resolver, and `tests/test_design_invariant_guard.py` covers absolute and repo-escaping locked core paths.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1595#qa-engineer-agent-core-lock-path -> 646121873

Disposition: FIXED
Commit: 12bc14f4a
Evidence: `scripts/design_guard.py` now validates every non-empty `core_lock.path`, including deferred core locks, before hash enforcement; `tests/test_design_invariant_guard.py` covers absolute and repo-escaping deferred core paths.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1595#bug-hunter-deferred-core-path -> 12bc14f4a

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `pytest -q tests/test_design_invariant_guard.py`
- PASS: `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json`
- PASS: `pytest -q tests/test_repo_policy_guards.py`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks during `git push`

## Heavy Local Gate Disposition

- Disposition: DEFERRED by explicit operator instruction.
- Evidence: `make verify` passed `verify-env`, flake8, mypy, and deterministic smoke tests before the diff-coverage full coverage pytest was operator-aborted at 37% to protect CPU.
- Terminal evidence: `make: *** [diff-cov] Terminated: 15`
- Heavy signal substitute: GitHub current-head CI for PR #1595.

## Deferred / Follow-ups

- Icon-core L4 master asset remains blocked/deferred. PR-7 does not create or claim `assets/brand/icon/core/v1.0/icon_core_v1.svg`.
- PR-8 Storybook parity remains the next design epic slice and is not widened into PR-7.
