# PR 1809 Fixed Mapping

## Summary

PR #1809 hardens the Experiment Runner environment bootstrap path so
oracle-only tooling can import, validate, and write result artifacts without
eagerly importing FastAPI-bound `app.security` exports.

## Scope

- `app/security/__init__.py`
- `scripts/orchestration/render_codex_start_prompt.py`
- `scripts/orchestration/start_pr_lane.sh`
- `scripts/orchestration/local_session_bootstrap.sh`
- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
- `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.md`
- `tests/test_experiment_runner.py`
- `tests/test_start_pr_lane.py`
- `tests/test_local_session_bootstrap.py`
- `tests/test_render_codex_start_prompt.py`
- `docs/review/PR_1809_FIXED_MAPPING.md`

## Lane Start Provenance

- Preflight/starter: `scripts/orchestration/start_pr_lane.sh` -> PASS
- Packet: `artifacts/orchestration/task_packets/2abbc8ea25a0.json`
- Post-open packet: `artifacts/orchestration/task_packets/6199236be550.json`
- Role order: `agent-coordinator -> architecture-specialist -> cursor-specialist-agent -> security-auditor -> data-scientist-agent -> qa-engineer-agent -> bug-hunter -> dev-operator`
- PR opened non-draft: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1809`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Discussion Threads And Bot Comments

- No actionable GitHub review threads were present at artifact creation time.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1809#issuecomment-4527689647
  - Disposition: NOT-A-BUG
  - Evidence: CodeRabbit could not start review because the account/organization hit review usage limits. This is not a code finding. Do not count the `CodeRabbit` status as completed review evidence; treat it as skipped/rate-limited until a later review is available.
- Sourcery review comment at `2026-05-24T07:13:58Z`
  - Disposition: NOT-A-BUG
  - Evidence: Sourcery weekly diff-character rate-limit notice only; no code finding or requested action.
- Cubic generated an informational PR summary. No action requested at artifact creation time.

## Role-Agent Findings

| Role | Finding | Disposition | Evidence |
| --- | --- | --- | --- |
| agent-coordinator | Startup authority stayed `check_preflight.py -> task_bootstrap.py -> agent-coordinator`; Experiment Runner joined after bootstrap as oracle-only evidence. | FIXED | Packet `artifacts/orchestration/task_packets/2abbc8ea25a0.json`; post-open packet `artifacts/orchestration/task_packets/6199236be550.json`. |
| architecture-specialist | Lazy `app.security` exports preserve tooling/runtime separation; branch needed refresh from current `origin/main` before push. | FIXED | Commit `5d2159900`; `git merge --ff-only origin/main`; `app/security/__init__.py:17`; focused pytest suite. |
| security-auditor | No security issue found in the static lazy export map, diagnostics, sandbox/control-plane boundaries, or runner mutation boundary. | FIXED | Commit `5d2159900`; `app/security/__init__.py:17`; `app/security/__init__.py:161`; `tests/test_experiment_runner.py::test_security_fastapi_bound_exports_have_repo_python_diagnostic`. |
| data-scientist-agent | Evidence wording needed to clarify that the runner sandbox command uses repo `.venv/bin` on `PATH`, not bare host Python. | FIXED | PR body `Experiment Runner Evidence` reproduction note; Experiment Runner artifact `artifacts/orchestration/experiments/results/exp-4827e84eac44.json`. |
| qa-engineer-agent | Missing blocked-FastAPI end-to-end artifact-writing regression and package `dir()` smoke. | FIXED | Commit `5d2159900`; `tests/test_experiment_runner.py:235`; `tests/test_experiment_runner.py:273`. |
| bug-hunter | Missing actionable diagnostic test for explicit FastAPI-bound `app.security` exports. | FIXED | Commit `5d2159900`; `app/security/__init__.py:161`; `tests/test_experiment_runner.py:251`. |
| dev-operator | PR-scoped gates must be used instead of full `make verify` under the machine-heavy exception. | FIXED | `make validate-changed` -> PASS; `pre-commit run --all-files` -> PASS; full `make verify` deferred in PR body. |
| post-open qa-engineer-agent | Canonical mapping artifact was missing and PR body mirror was stale after PR number assignment; code/test side looked acceptable. | FIXED | This artifact; PR body mirror update pending this commit; `tests/test_experiment_runner.py:235`; `tests/test_experiment_runner.py:251`; `tests/test_experiment_runner.py:273`. |
| post-open bug-hunter | Canonical mapping artifact was missing; CodeRabbit status is pass but review was skipped and must not be counted as completed review evidence. | FIXED | This artifact records the CodeRabbit rate-limit comment as NOT-A-BUG and preserves it as incomplete bot-review evidence. |
| post-open bug-hunter | Prompt wording incorrectly implied `$PWD/.venv/bin/python` is normal inside an isolated worktree; this recreates the env drift being fixed. | FIXED | This mapping commit; `scripts/orchestration/render_codex_start_prompt.py`; `tests/test_render_codex_start_prompt.py`; `tests/test_local_session_bootstrap.py`. |
| post-open security-auditor | No issues found in final committed diff; merge state remained unstable, so security pass is not a merge-readiness claim. | FIXED | Subagent PASS; `app/security/__init__.py:17`; `app/security/__init__.py:161`; `tests/test_experiment_runner.py:194`; `tests/test_experiment_runner.py:235`; `tests/test_experiment_runner.py:273`. |
| CodeRabbit CLI review | Mapping artifact had `## Merge Readiness Notes` but lacked an explicit canonical `## Merge Readiness` checklist. | FIXED | This mapping update adds the checklist with unchecked pre-merge items while preserving that this artifact is not a merge-ready claim. |
| Codex Security diff scan | No reportable security findings in lazy export map, diagnostics, sandbox/control-plane boundary, or runner mutation boundary. | FIXED | Local report `/tmp/codex-security-scans/BMI-App_2025_clean/pr1809-6f5f916b8-20260524T0735Z/report.md`; focused security smoke and pytest passed. |
| pulseplate-pr-review / bug-triage | Advisory large-diff risk and env-drift regression were reviewed; env-drift prompt issue was fixed, large-diff risk covered by split rationale and targeted gates. | FIXED | `/tmp/pulseplate_pr1809_review_report.md`; `make validate-changed`; focused pytest; this mapping artifact. |
| repeat type-focused QA | Direct mypy with `--explicit-package-bases` found test helper typing gaps around packet `metrics`/`budgets` dict unpacking and cleanup wrapper return type. | FIXED | Typed helper accessors added in `tests/test_experiment_runner.py`; direct mypy now reports `Success: no issues found in 6 source files`; focused pytest passed. |

## Post-Open Agent Launch Evidence

- Post-open packet: `artifacts/orchestration/task_packets/6199236be550.json`
- `qa-engineer-agent`: launched as subagent `019e58d7-6541-7552-9ff7-29a5c568d834`
- `bug-hunter`: launched as subagent `019e58d7-7b02-7720-91c0-4eddbe7c0400`
- `security-auditor`: launched as subagent `019e58d7-8fe8-7fa1-8bbf-1e50e25b4807`
- Post-open security-auditor PASS: no issues found; `gh pr view` still reported `mergeStateStatus: UNSTABLE`, so this is not a merge-readiness claim.
- Post-open QA/bug findings about missing mapping and stale PR body are fixed by this artifact and the follow-up PR body mirror update.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-4827e84eac44.json`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- `mutated_paths`: `[]`
- `promotion_ready`: `false`
- `shared_tree_untouched`: `true`
- `contribution_kind`: `commit_decision`
- `coauthor_required`: `true`
- Co-author trailer present in commit `5d2159900`: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Premortem Risk Fix Matrix

| Risk ID | Failure mode | Fix | Regression test | Evidence command | Disposition |
| --- | --- | --- | --- | --- | --- |
| PM-1809-001 | Experiment Runner imports fail before CLI parsing because `app.security` eagerly imports FastAPI-bound exports. | `app.security` now exposes submodules and public symbols through static lazy maps. | `test_experiment_runner_import_does_not_require_fastapi`; `test_experiment_runner_help_does_not_require_fastapi`. | `.venv/bin/python -m pytest -q tests/test_experiment_runner.py tests/test_start_pr_lane.py tests/test_local_session_bootstrap.py tests/test_render_codex_start_prompt.py` -> PASS. | FIXED |
| PM-1809-002 | Sandbox-only tooling imports pull FastAPI indirectly through package exports. | `execution_sandbox` and package `dir()` paths stay lightweight. | `test_security_sandbox_import_does_not_require_fastapi`; `test_security_package_dir_does_not_require_fastapi`. | Focused pytest suite -> PASS. | FIXED |
| PM-1809-003 | Explicit FastAPI-bound runtime exports fail with raw `No module named fastapi`, causing invalid `Not applicable` evidence. | FastAPI-bound lazy imports raise an actionable repo-Python diagnostic with active interpreter, `VENV_PYTHON`, and `.venv` guidance. | `test_security_fastapi_bound_exports_have_repo_python_diagnostic`. | Focused pytest suite -> PASS. | FIXED |
| PM-1809-004 | Oracle-only result artifact cannot be written in a tooling-only environment. | Runner artifact path remains FastAPI-light through result writing. | `test_oracle_only_main_writes_result_artifact_without_fastapi`. | Focused pytest suite -> PASS. | FIXED |
| PM-1809-005 | Startup prompts regress by treating Experiment Runner as lane-start authority or using bare host Python. | Starter/local bootstrap/rendered prompts keep coordinator-first authority and add repo Python / `VENV_PYTHON` runner guidance. | Starter/bootstrap prompt tests. | Focused pytest suite -> PASS. | FIXED |
| PM-1809-006 | Lazy export hardening weakens normal FastAPI-facing runtime exports. | Runtime symbols still resolve when repo environment has FastAPI installed. | `test_security_package_fastapi_bound_exports_still_resolve`. | Focused pytest suite -> PASS. | FIXED |
| PM-1809-007 | Isolated worktree prompts point agents at `$PWD/.venv/bin/python`, which may not exist and can recreate env drift. | Prompt guidance now requires an absolute `VENV_PYTHON` printed by starter/bootstrap or another explicit repo Python, and warns against `$PWD/.venv/bin/python` in isolated worktrees. | Prompt/bootstrap tests assert the safer wording. | Focused pytest suite -> PASS after this fix. | FIXED |
| PM-1809-008 | Test helper typing gaps surface only under stricter direct mypy invocation, not normal runtime pytest. | Packet `metrics`/`budgets` overrides now use typed helper accessors and the cleanup wrapper monkeypatch uses an explicit broad return type. | Direct mypy over changed Python/test files. | `mypy --explicit-package-bases ...` -> PASS. | FIXED |

## Bounded Check Evidence

| Command | Result |
| --- | --- |
| `python scripts/orchestration/check_preflight.py --path <changed paths>` | PASS |
| `python scripts/orchestration/check_agent_consistency.py` | PASS: `OK: agent docs and files are consistent.` |
| `python scripts/orchestration/check_experiment_runner_identity.py` | PASS |
| `.venv/bin/python -m pytest -q tests/test_experiment_runner.py tests/test_start_pr_lane.py tests/test_local_session_bootstrap.py tests/test_render_codex_start_prompt.py` | PASS |
| `.venv/bin/python -m pytest -q tests/test_agent_control_plane_mvp.py tests/test_execution_sandbox.py tests/test_agent_input_guard.py tests/test_rate_limit_test_client_guards.py tests/test_env_guards.py` | PASS |
| `.venv/bin/python -m pytest -q tests/test_experiment_runner_identity_policy.py tests/test_experiment_promote.py tests/test_experiment_bootstrap.py` | PASS |
| `make validate-changed` | PASS |
| `pre-commit run --all-files` | PASS |
| Pre-push hooks | PASS: detect-secrets, mypy changed files, pip-audit, backend tests, full-repo Bandit, docker build test |
| Direct mypy on touched Python/test files | PASS: `Success: no issues found in 6 source files` after type-focused repeat review |

## Fixed in Commit Mapping

- No actionable review comments

## Commit Evidence

- Environment/import hardening and focused tests: `5d2159900`.
- Experiment Runner co-author trailer: `5d2159900`.
- Fixed mapping artifact and isolated-worktree prompt wording correction: this mapping commit.

## Deferred / Follow-ups

- Separate future threat-model PR for any possible Experiment Runner mutation access to `scripts/ci/**`.

## Merge Readiness Notes

- This artifact is not a merge-ready claim.
- Required before merge readiness: PR body mirror refresh, current-head CI, review-thread disposition guard with auth, strict merge-readiness wrapper with auth, no actionable bot comments, and mandatory wait window.

## Merge Readiness

- [x] PR body mirror refreshed from canonical mapping artifact.
- [x] Local PR-scoped gates passed: preflight, agent consistency, Experiment Runner identity, focused pytest, `make validate-changed`, and `pre-commit run --all-files`.
- [x] Compensating review completed for skipped/rate-limited bots: `pulseplate-pr-review`, `bug-triage`, Codex Security diff scan, and CodeRabbit CLI review.
- [ ] Current-head CI passing with all required checks green and no pending jobs.
- [ ] Review-thread disposition guard with auth passed after latest bot/human activity.
- [ ] Strict merge-readiness wrapper with auth passed after latest bot/human activity.
- [ ] No actionable bot comments remain.
- [ ] Mandatory wait window elapsed after latest bot/review activity.
