# PR 1821 Fixed Mapping

## Summary

Human-owned replacement for Dependabot #1804. The PR updates Black and Ruff
quality-tooling pins without accepting the generated `pip==26.1.1` unsafe pin,
keeps `requirements.txt` unchanged, and retires the stale `ruff==0.15.13`
emergency wheel after private proxy proof for `ruff==0.15.14`.

## Lane Start Provenance

Packet: artifacts/orchestration/task_packets/b14c45845078.json

## Dependency Surfaces

- `requirements-dev.in`: `black~=26.5.1`, `ruff~=0.15.14`
- `requirements-dev.txt`: `black==26.5.1`, `ruff==0.15.14`
- `requirements-lock.txt`: `ruff==0.15.14`
- `constraints.txt`: `black>=26.5.1`, `ruff>=0.15.14`
- `requirements-all.txt`: `black>=26.5.1`, `ruff>=0.15.14`
- `requirements.txt`: no diff

## Agent Execution Log

- `agent-coordinator`: REPLACE Dependabot #1804; raw PR blocked by unsafe `pip==`.
- `architecture-specialist`: BLOCK raw PR; remove production lock drift; resolve stale ruff fallback.
- `security-auditor`: BLOCK raw PR; require no `pip==`, private proxy proof, and emergency manifest disposition.
- `qa-engineer-agent`: conditional accept after guard update for retired ruff fallback.
- `bug-hunter`: conditional go after false-green checks for `pip==`, `requirements.txt`, ruff fallback, and lock parity.
- `dev-operator`: isolated worktree, local gates, PR-open, and merge-readiness plan.
- Post-open `qa-engineer-agent`: PASS at rebased head `fcd881c4d`; no rebase QA issue, no production lock drift, bounded root `.venv` checks sufficient pending CI.
- Post-open `security-auditor`: PASS at rebased head `fcd881c4d`; no supply-chain blocker, no public fallback, no new secret-bearing value, no inline review comments.
- Post-open `bug-hunter`: final refresh recorded in this mapping; no dependency/profile regression, branch current, no inline comments, Phase2 and review-thread guard passed. Remaining blocker is current-head CI/strict readiness only.

## Skill Execution Log

- `pulseplate-premortem-risk-review`: actual dependency diff and PM-DEPS matrix reviewed.
- `pulseplate-pr-review`: pre-open review completed against dependency and governance surfaces.
- `pulseplate-gates`: bounded local gate bundle completed.
- `codex-security:security-scan`: diff-scoped supply-chain/security scan completed.
- `pulseplate-ledger`: not used; no deferrals.

## Experiment Runner Evidence

- Packet: local bootstrap artifact generated under `artifacts/orchestration/experiments/`; accepted result artifact below is the retained governance evidence.
- Artifact: `artifacts/orchestration/experiments/results/pr1804-quality-tooling-oracle-result.json`
- Status: accepted
- Mode: `oracle_only_governance_reviewer`
- Oracle commands executed: 7
- Co-author required: yes

## Premortem Risk Fix Matrix

| Risk ID | Failure mode | Fix | Regression test | Evidence command | Fix commit SHA | Evidence (file:line) | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PM-DEPS-001` | Source constraints and compiled locks drift. | Updated source and exact pins for Black/Ruff only. | Quality tooling guard. | `pytest -q tests/test_install_locked_python_requirements.py` | `d10f454c9` | `requirements-dev.in:33`; `requirements-dev.txt:15`; `requirements-lock.txt:164` | FIXED |
| `PM-DEPS-002` | Private Python index cannot serve the new pinned wheel. | Verified private proxy serves both exact wheels. | Installer preflight/full profile. | `pip download --isolated --index-url $PULSEPLATE_PYTHON_INDEX_URL ...` | `d10f454c9` | `requirements-dev.txt:15`; `requirements-dev.txt:227`; `constraints.txt:15`; `constraints.txt:19` | FIXED |
| `PM-DEPS-003` | Emergency wheel manifest becomes stale. | Retired stale `ruff==0.15.13`; no expansion. | Ruff private-proxy guard. | `test_repo_ruff_private_proxy_pin_is_not_stale_emergency_fallback` | `d10f454c9` | `scripts/ci/emergency_python_wheels.json:6`; `tests/test_install_locked_python_requirements.py:419` | FIXED |
| `PM-DEPS-004` | PR silently widens profile surface. | Human replacement excludes `requirements.txt` and CI YAML. | Diff audit. | `git diff --name-only origin/main...HEAD` | `d10f454c9` | `requirements-dev.in:33`; `requirements-lock.txt:164`; `requirements.txt` no diff | FIXED |
| `PM-DEPS-005` | Local `.venv` and CI diverge. | Ran installer and gates with repo `.venv`. | pip check and pre-commit. | `.venv/bin/python -m pip check` | `d10f454c9` | `requirements-dev.txt:15`; `requirements-dev.txt:227`; `tests/test_install_locked_python_requirements.py:441` | FIXED |
| `PM-DEPS-006` | Dependency update breaks import/runtime smoke. | Ran Black and Ruff checks. | Tool CLI smoke. | `.venv/bin/python -m black --check .`; `.venv/bin/python -m ruff check .` | `d10f454c9` | `requirements-dev.txt:15`; `requirements-dev.txt:227`; `tests/test_install_locked_python_requirements.py:456` | FIXED |
| `PM-DEPS-007` | Dependabot PR conflicts after another dependency PR lands. | Replaced stale Dependabot branch from current main and rebased after main advanced. | PR metadata/diff audit. | `gh pr view 1804 ...`; `git rev-list --left-right --count HEAD...origin/main` | `89401c210` | `docs/review/PR_1821_FIXED_MAPPING.md:25`; `docs/review/PR_1821_FIXED_MAPPING.md:104` | FIXED |
| `PM-DEPS-008` | Unsafe package pin appears unintentionally. | Removed generated `pip==26.1.1`; guard proves no repo-managed pip pin. | Pip-pin guard. | `pytest -q tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip` | `d10f454c9` | `requirements-dev.txt:261`; `tests/test_dependency_security_guard.py:584` | FIXED |
| `PM-DEPS-009` | Full `make verify` deferred without sufficient bounded evidence. | Ran bounded dependency, supply-chain, tooling, installer, validate-changed, and pre-commit gates. | Current-head CI required before merge. | `make validate-changed`; `pre-commit run --all-files` | `89401c210` | `docs/review/PR_1821_FIXED_MAPPING.md:75`; `docs/review/PR_1821_FIXED_MAPPING.md:104` | FIXED |

## Security Review

Codex Security scan found no surviving reportable vulnerability after fixes:
forbidden `pip==` was removed, public-index fallback was not introduced, stale
ruff emergency fallback was retired with guard coverage, and runtime lock drift
was eliminated.

## Tests / Bounded Checks

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `pytest -q tests/test_install_locked_python_requirements.py` PASS
- `pytest -q tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py` PASS
- `pytest -q tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip` PASS
- `.venv/bin/python -m black --check .` PASS
- `.venv/bin/python -m ruff check .` PASS
- `.venv/bin/python -m pip check` PASS
- `make validate-changed` PASS
- `pre-commit run --all-files` PASS
- Post-rebase root `.venv` focused guards PASS:
  `pytest -q tests/test_install_locked_python_requirements.py::test_repo_ruff_private_proxy_pin_is_not_stale_emergency_fallback tests/test_install_locked_python_requirements.py::test_repo_quality_tooling_profile_matches_dependabot_replacement_contract tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip`
- Post-rebase root `.venv` `black`, `ruff`, `pip check`, Phase2 body gate, and review-thread disposition guard PASS.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1821#discussion_r3295188970 -> 1141ca059
Disposition: FIXED
Evidence: PM-DEPS matrix now includes `Fix commit SHA` and `Evidence (file:line)` columns for every `FIXED` row (`docs/review/PR_1821_FIXED_MAPPING.md:54`).

## Deferred / Follow-ups

None.

## Merge Readiness

Not merge-ready yet. Post-open QA, security, and bug-hunter passes are recorded
for the rebased lane, with no dependency/profile regression found. Pending
current-head CI terminal status, strict review-thread guard, strict
merge-readiness wrapper, and final wait-window.
