# PR 1947 Fixed in Commit Mapping

## Discussion Thread Pass

- [x] PR opened non-draft.
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [ ] Cubic review thread resolved after pushed FIXED evidence exists.
- [ ] CodeRabbit produced a substantive no-actionable review after the latest head.
- [ ] Sourcery produced a substantive no-actionable review after the latest head.
- [ ] Current-head CI is green for required checks.
- [ ] Strict merge-readiness wrapper passed with GitHub auth.
- [ ] Mandatory wait-window elapsed after latest bot/review activity.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1947#discussion_r3398140208 -> 2dc7913f2b22d9d11e4c06b6de5e21f824c10ed0
Disposition: FIXED
Commit: 2dc7913f2b22d9d11e4c06b6de5e21f824c10ed0
Evidence: `.github/workflows/ci.yml:1192`; `.github/workflows/ci.yml:1218`; `.github/workflows/ci.yml:1242`; `tests/test_ci_workflow_pr_size_governance_contract.py:1795`; `tests/test_ci_workflow_pr_size_governance_contract.py:1862`
Reason: Cubic correctly found that the PR diagnostic override pointed `test-main` at public PyPI even though the locked installer blocks public hosts. The fix removes the public PyPI override, keeps `test-main` at `contents: read` and `actions: read`, blanks inherited proxy env at job scope, resolves the PR diagnostic proxy from credential-free repository variables only, fails closed when the PR index is missing or multi-line, and keeps protected non-PR runs on the existing `secrets || vars` fallback before `python-setup`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1947#issuecomment-4683578752
Disposition: NOT-A-BUG
Evidence: The comment is a CodeRabbit rate-limit and usage-credit notice, not a substantive review finding. It is not treated as a CodeRabbit PASS or no-actionable signal for merge readiness.
Reason: No code, test, documentation, or governance action is requested by this quota notice.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1947#pullrequestreview-4479342077
Disposition: NOT-A-BUG
Evidence: The review body is Sourcery's weekly diff-character rate-limit notice, not a substantive review finding. It is not treated as a Sourcery PASS or no-actionable signal for merge readiness.
Reason: No code, test, documentation, or governance action is requested by this quota notice.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1947#issuecomment-4683759628
Disposition: NOT-A-BUG
Evidence: Codecov reported that all modified and coverable lines were covered by tests for the previous head. Current-head Codecov remains a post-push signal and is not claimed here.
Reason: The comment contains no actionable code-review finding.

## Implementation Evidence

- `2dc7913f2b22d9d11e4c06b6de5e21f824c10ed0`: Removed the PR-only public PyPI override from `test-main`, kept read-only `contents` and `actions` permissions, blanked inherited proxy env at job scope, added a PR-only repository-vars resolver, added a protected `secrets || vars` resolver, and placed both resolver steps before `Setup Python environment`.
- `2dc7913f2b22d9d11e4c06b6de5e21f824c10ed0`: Extended `tests/test_ci_workflow_pr_size_governance_contract.py` to assert read-only actions permission, blank proxy env, PR resolver ordering, PR resolver vars-only behavior, no PR secrets references, empty-index failure, CR/LF rejection, protected secrets-or-vars fallback, and absence of `https://pypi.org/simple` / `pypi.org` in the `test-main` job.
- `3babb198fe65df6ebf75ca29496d1cf494d0e2cc`: After merging current `origin/main`, fixed a current-main A1b closeout guard failure by rewording the embedding/retrieval telemetry sentence with explicit gate-closed negative language. Evidence: `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md:81`.

## Current-Main CI Unblock Evidence

- Current-head CI failure observed in `test-main (3.11, 60)` after the package-proxy resolver and `Setup Python environment` had already succeeded.
- Raw failure pointer: `FAILED tests/test_ai_pro_quota_a1b_closeout.py::test_checker_passes_on_current_repository`; the checker rejected the prior backend-selection sentence as a non-fail-closed runtime-expansion claim.
- Root cause: current `origin/main` introduced `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md` wording that the A1b closeout guard classifies as an enabled semantic-cache/runtime-expansion claim.
- Fix: `3babb198fe65df6ebf75ca29496d1cf494d0e2cc` changes that sentence to state that no embedding backend or retrieval runtime is enabled. This preserves gate-closed semantics and does not authorize embeddings, vector search, provider wiring, semantic-cache serving, DB, API, web, or mobile runtime work.

## Startup And Role Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --path .github/workflows/ci.yml --path tests/test_ci_workflow_pr_size_governance_contract.py --path docs/review/PR_1947_FIXED_MAPPING.md`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: `python3 scripts/orchestration/task_bootstrap.py --goal "Finish PR #1947 CI diagnostic privilege fix" --task-class "CI/Security" --path .github/workflows/ci.yml --path tests/test_ci_workflow_pr_size_governance_contract.py --path docs/review/PR_1947_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase post_open_review --native-bridge-transport codex-native-subagents`; packet `artifacts/orchestration/task_packets/526f7b1d7d5b.json`.
- PASS: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/526f7b1d7d5b.json --pretty`; declared role order was `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> web-research-agent`.
- `agent-coordinator`: completed scope lock; allowed files were `.github/workflows/ci.yml`, `tests/test_ci_workflow_pr_size_governance_contract.py`, and `docs/review/PR_1947_FIXED_MAPPING.md`; Cubic P1 accepted as valid.
- `qa-engineer-agent`: reviewed the candidate and found it acceptable after commit/push, with the broader supply-chain test resource gap noted separately.
- `bug-hunter`: reviewed the candidate and found no code-level blocker after the public PyPI override was removed and the proxy resolver was guarded.
- `security-auditor`: first pass blocked on missing explicit empty-index and CR/LF assertions; second pass passed after those test assertions were added.
- `cursor-specialist-agent`: passed role-order/tooling review; no process blocker.
- `web-research-agent`: passed as not applicable; no external research was needed for this repo-local CI fix.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/526f7b1d7d5b.json`

## Premortem Finding Closure

- PM-1947-001: Public PyPI remains in the PR diagnostic path and `test-main` keeps failing before dependency installation. Disposition: FIXED by `2dc7913f2b22d9d11e4c06b6de5e21f824c10ed0`; evidence `.github/workflows/ci.yml:1218`, `tests/test_ci_workflow_pr_size_governance_contract.py:1862`.
- PM-1947-002: Removing public PyPI accidentally re-exposes workflow-level private proxy secrets to PR-controlled code. Disposition: FIXED by blank job-level proxy env plus a PR resolver that references only repository `vars`; evidence `.github/workflows/ci.yml:1195`, `.github/workflows/ci.yml:1220`, `tests/test_ci_workflow_pr_size_governance_contract.py:1798`.
- PM-1947-003: Missing or multi-line repository variables produce misleading CI behavior or unsafe `$GITHUB_ENV` writes. Disposition: FIXED by empty-index and CR/LF fail-closed guards in both resolver paths; evidence `.github/workflows/ci.yml:1227`, `.github/workflows/ci.yml:1231`, `.github/workflows/ci.yml:1251`, `.github/workflows/ci.yml:1255`.
- PM-1947-004: Mapping or PR body updates get ahead of the actual fix, or bot quota notices are treated as approvals. Disposition: FIXED by committing the workflow/test fix before this mapping, mapping Cubic to the post-comment fix commit, and recording quota notices as non-approval NOT-A-BUG entries.
- PM-1947-005: The security scan worklist helper excludes `.github/` and `tests/`, hiding this PR's actual review surface. Disposition: NOT-A-BUG for product code; evidence the Codex Security report records the helper limitation and uses a corrected explicit worklist for the two PR files.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/pr-1947-test-main-diagnostic-oracle-result.json`
- Experiment id: `exp-194fee1171ef`.
- Status: `accepted`.
- Runner mode: `oracle_only_governance_reviewer`.
- Contribution: `commit_decision`; commit `2dc7913f2b22d9d11e4c06b6de5e21f824c10ed0` includes the required trailer `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Oracle evidence: isolated checkout applied source diff for `.github/workflows/ci.yml` and `tests/test_ci_workflow_pr_size_governance_contract.py`; `git diff --check` returned `0`; `python3 -m py_compile tests/test_ci_workflow_pr_size_governance_contract.py` returned `0`; shared tree untouched.

## Codex Security Diff Scan

- Report: `/tmp/codex-security-scans/BMI-App_2025_clean/pr1947-localpatch-20260611T000000Z/report.md`.
- HTML: `/tmp/codex-security-scans/BMI-App_2025_clean/pr1947-localpatch-20260611T000000Z/report.html`.
- PASS: report format validation passed with `validate_report_format.py`.
- Result: no reportable findings. The scan reviewed the workflow privilege/proxy boundary and the regression-test contract. Validation and attack-path phases were skipped because discovery emitted no candidate findings.

## Validation Evidence

- PASS: `python3 -m py_compile tests/test_ci_workflow_pr_size_governance_contract.py`.
- PASS: YAML load sanity for `.github/workflows/ci.yml` confirmed `test-main` permissions, blank env, resolver ordering, and setup placement.
- PASS: `.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py` -> `27 passed`.
- PASS: `.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_python_supply_chain_controls.py::test_all_changed_python_install_surfaces_use_locked_installer tests/test_python_supply_chain_controls.py::test_proxy_backed_workflows_support_vars_or_secrets tests/test_python_supply_chain_controls.py::test_no_canonical_workflow_uses_unscoped_public_pip_install tests/test_ci_risk_profile.py::test_hidden_workflow_path_preserves_leading_dot_for_routing tests/test_ci_risk_profile.py::test_main_ci_diagnostic_is_scoped_to_main_ci_surfaces` -> `43 passed`.
- PASS: `git diff --check`.
- PASS: `make validate-changed` -> selected `tests/test_ci_workflow_pr_size_governance_contract.py`, `27 passed`.
- PASS after hook formatting rerun: `pre-commit run --all-files`.
- PASS during commit hooks for `2dc7913f2b22d9d11e4c06b6de5e21f824c10ed0`: YAML, whitespace, merge-conflict, large-file, yamllint, detect-secrets, workflow check, Black, Ruff, backend changed-file pytest, iOS syntax, and commitizen.
- PASS: `.venv/bin/python -m pytest -q tests/test_ai_pro_quota_a1b_closeout.py::test_checker_passes_on_current_repository`.
- PASS: `python3 scripts/ci/check_ai_pro_quota_a1b_closeout.py`.
- PASS: commit hooks for `3babb198fe65df6ebf75ca29496d1cf494d0e2cc`.
- Local validation gap: broader `.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_python_supply_chain_controls.py tests/test_ci_risk_profile.py` stopped at `tests/test_python_supply_chain_controls.py::test_pip_audit_helper_invokes_cpu_rag_vector_manifest` with return code `-9`, empty stdout/stderr; isolated rerun hung beyond 3 minutes and was killed. This is not claimed as passing evidence.
- Local machine-heavy exception: full local `make verify` was not run for this CI/tooling PR. Merge readiness must use the documented narrow local gates above plus current-head CI parity and strict wrapper evidence.

## Merge Readiness

- [ ] PR body mirror updated from this artifact.
- [ ] Branch pushed after `2dc7913f2b22d9d11e4c06b6de5e21f824c10ed0` and this mapping commit.
- [ ] Cubic thread `discussion_r3398140208` resolved only after pushed FIXED evidence exists.
- [ ] Current-head `test-main` matrix passed without public PyPI override failure.
- [ ] Current-head `PR Body Phase2 gates` passed.
- [ ] Current-head `Merge readiness gate` passed.
- [ ] Current-head required CI checks passed with no pending required jobs.
- [ ] CodeRabbit and Sourcery are either substantive no-actionable reviews or explicitly allowed dispositions under repo policy; quota notices alone are not PASS signals.
- [ ] `GH_TOKEN="$(gh auth token)" GITHUB_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_merge_ready.py --pr-number 1947 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth` passed after the latest review activity.
- [ ] Mandatory wait-window completed after latest bot/review activity.
