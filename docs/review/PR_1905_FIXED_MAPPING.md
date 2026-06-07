# PR 1905 Fixed Mapping

## Summary

This PR fixes the `main` CI dependency-security failure by removing generated
`pip==26.1.2` unsafe-package stanzas from repo-managed lock surfaces. The fix
keeps all other dependency pins unchanged and restores the existing GHSA-58qw
policy guard.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/fix_main_ci_pip_pin_guard.json`
- Packet id: `ccb21b6d284c`
- Branch: `fix/main-pip-lock-pin`
- Head commit: `ee22afcd572940d653aff63d626617ac0268e2d2`

## Scope

IN:

- `requirements-dev.txt`
- `requirements-lock.txt`

OUT:

- app/core runtime code
- OpenAPI artifacts
- Dockerfile
- dependency source `.in` files
- orchestration docs beyond this required review artifact

## Agent Execution Log

- `agent-coordinator`: PASS. Confirmed `main` CI root cause and approved focused branch from `origin/main`.
- `dev-operator`: PASS. Confirmed committed diff, pre-commit evidence, and push/PR plan.
- `backend-engineer`: PASS. Confirmed lock-surface-only supply-chain fix; no backend runtime impact.
- `qa-engineer-agent`: PASS. Accepted QA gate; noted PR CI may not run the exact pip-pin guard.
- `bug-hunter`: PASS. No P0 code defects; P1 process risk is explicit guard evidence before merge claims.
- `security-auditor`: PASS. Confirmed GHSA-58qw policy alignment and no supply-chain regression.
- `cursor-specialist-agent`: PASS. No Cursor/agent docs update required in this narrow hotfix.
- `architecture-specialist`: PASS. Approved two-file micro PR; no architectural invariant violation.

## Skill Execution Log

- `pulseplate-workflow`: coordinator-first setup and scoped preflight.
- `pulseplate-orchestration-dispatch`: bootstrap packet and role dispatch manifest.
- `pulseplate-gates`: focused guards, changed-file validation, and pre-commit evidence.
- `pulseplate-security-guardrail`: GHSA/no unsafe pip pin policy check.
- `create-pr`: branch push and PR creation.
- `babysit`: PR readiness follow-up and failed gate triage.

## Experiment Runner Evidence

Not applicable: tiny lock-surface hotfix; all decisions were driven by deterministic CI failure, existing GHSA policy, and PulsePlate role-agent review results.

## Risk Fix Matrix

| Risk ID | Failure mode | Fix | Regression test | Evidence command | Fix commit SHA | Evidence | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PIP-PIN-001` | Repo-managed lock surfaces pin `pip`, violating GHSA-58qw no-pin policy and failing `main` `test-main`. | Removed generated `pip==26.1.2` stanzas from `requirements-dev.txt` and `requirements-lock.txt`. | `test_repo_managed_lock_surfaces_do_not_pin_pip`. | `.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip tests/test_install_locked_python_requirements.py` | `ee22afcd572940d653aff63d626617ac0268e2d2` | `requirements-dev.txt:260`; `requirements-lock.txt:514`; `tests/test_dependency_security_guard.py:584`; `docs/security/GHSA-58qw-9mgm-455v-pip.md:30` | FIXED |
| `PIP-PIN-002` | Lockfile-only PR could appear green without explicit pip-pin guard evidence. | Recorded explicit focused guard and install-lock validation; current-head CI remains required before merge readiness. | Focused guard + install-lock tests. | `pre-commit run --all-files`; `make validate-changed` | `ee22afcd572940d653aff63d626617ac0268e2d2` | PR body validation section; this artifact `## Tests / Bounded Checks` | FIXED |

## Tests / Bounded Checks

- `python3 scripts/orchestration/check_preflight.py --path requirements-dev.txt --path requirements-lock.txt` - PASS.
- `.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip tests/test_install_locked_python_requirements.py` - PASS.
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS.
- `gh pr checks 1905` - current-head CI mostly PASS; `PR Body Phase2 gates` and `Merge readiness gate` failed only because this canonical artifact was missing before this commit.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- No actionable review comments

## Bot Review Summary

- CodeRabbit walkthrough / release-notes comments: NOT-A-BUG. Evidence: advisory walkthrough and release notes only; CodeRabbit status reports `Review skipped`, with no actionable code-review thread.
- Sourcery review: NOT-A-BUG. Evidence: Sourcery review says changes look great and requests no code change.
- Cubic review: NOT-A-BUG. Evidence: cubic reports `No issues found` across 2 files.
- Codecov comment: NOT-A-BUG. Evidence: Codecov reports all modified and coverable lines are covered by tests.

## Deferred / Follow-ups

None.

## Merge Readiness

Not merge-ready yet. Pending after this artifact commit:

- Current-head CI rerun with `PR Body Phase2 gates` PASS.
- Current-head CI rerun with `Merge readiness gate` PASS or expected pending status until final strict merge pass.
- Review/bot comments remain no-actionable.
- Mandatory wait-window and final strict merge-readiness pass per `AGENTS.md`.
