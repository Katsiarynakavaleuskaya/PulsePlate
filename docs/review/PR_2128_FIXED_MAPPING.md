# PR 2128 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2128

Branch: `codex/fix-ci-lifecycle-guard-hang-issue`

## Summary

PR #2128 is the owner lane replacing Codex PRs #2123 through #2127. The
replacement keeps the diff limited to the legacy-growth CI guard, its focused
tests, and this canonical review artifact. Public APIs, OpenAPI, application
runtime, setup/dependency work, Docker manifests, and colleague-owned lanes are
unchanged.

Implementation commits:

- `2356523bbbb51a41bee7296d4eb9e54a647454ec` - scope-aware, fail-closed AST resolver and deterministic regression coverage.
- `da4d3207b4a21cded1bb1ba2467d9e4dd6cb5b0d` - exact nested-import matrix requested by the unresolved #2125 review.
- `bcb9cf8616fcc8c0c1fbdf5b1447d2bf8a4f278d` - type-safe separation of lambda expressions from sync/async statement bodies after the exact pre-push MyPy finding.

Main synchronization:

- `30e3d6630f5ea523bef79d0305bc16a9d6fd1356` merges fresh `origin/main` at `b432aeb78a6b18cdedf760bb7872daf9241dacd6`, including colleague-owned setup remediation PR #2133, without rebasing or rewriting the published owner history.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [ ] Current-head GitHub CI, current-head bot pass, strict merge wrapper, and mandatory review wait-window remain pending.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 2356523bbbb51a41bee7296d4eb9e54a647454ec
Evidence: `scripts/ci/check_legacy_growth_guard.py:1677`, `scripts/ci/check_legacy_growth_guard.py:1896`, and `scripts/ci/check_legacy_growth_guard.py:2326` replace duplicate module-wide lookup helpers with one statement-ordered lexical resolver; `tests/test_legacy_growth_guard.py:876`, `tests/test_legacy_growth_guard.py:987`, and repeated-run assertions prove namespace detection, local shadowing, sibling-scope isolation, and no state leak.
Reason: The replacement eliminates the duplicate namespace classifier and the module-wide alias map that misclassified function-local bindings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2123#pullrequestreview-4694128916 -> 2356523bbbb51a41bee7296d4eb9e54a647454ec
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2123#pullrequestreview-4694160448 -> 2356523bbbb51a41bee7296d4eb9e54a647454ec
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2123#discussion_r3578873209 -> 2356523bbbb51a41bee7296d4eb9e54a647454ec

Disposition: FIXED
Commit: 2356523bbbb51a41bee7296d4eb9e54a647454ec
Evidence: `scripts/ci/check_legacy_growth_guard.py:2408` uses a shared union-typed function-header visitor for `ast.FunctionDef` and `ast.AsyncFunctionDef`; `tests/test_legacy_growth_guard.py:742` through `tests/test_legacy_growth_guard.py:791` cover sync/async definitions inside module-level `if`, `try`, `with`, and `for` while preserving nested-local exclusions.
Reason: Sync and async conditional module definitions now share one type-safe implementation without passing an async node to a sync-only helper.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2124#pullrequestreview-4694131105 -> 2356523bbbb51a41bee7296d4eb9e54a647454ec
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2124#discussion_r3578846067 -> 2356523bbbb51a41bee7296d4eb9e54a647454ec

Disposition: FIXED
Commit: da4d3207b4a21cded1bb1ba2467d9e4dd6cb5b0d
Evidence: `tests/test_legacy_growth_guard.py:971` and `tests/test_legacy_growth_guard.py:972` add the reviewer-requested `nested-module-plain` and `nested-importlib-intermediate` cases; the focused five-case nested-alias matrix and the complete legacy-growth guard suite pass.
Reason: The review explicitly requested one or two stronger nested-import regressions; the replacement adds two exact suggested patterns without widening the guard into interprocedural call/return analysis.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2125#pullrequestreview-4694140672 -> da4d3207b4a21cded1bb1ba2467d9e4dd6cb5b0d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2125#discussion_r3578854849 -> da4d3207b4a21cded1bb1ba2467d9e4dd6cb5b0d

Disposition: FIXED
Commit: 2356523bbbb51a41bee7296d4eb9e54a647454ec
Evidence: `scripts/ci/check_legacy_growth_guard.py:886` restricts binding counts to module-scope names and documents that function parameters are intentionally excluded; `tests/test_legacy_growth_guard.py:2540` proves a shadowed parameter cannot suppress a module registrar string.
Reason: Function parameters no longer count as module bindings, while module-level definitions and imports remain visible to the guard.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2126#pullrequestreview-4694137225 -> 2356523bbbb51a41bee7296d4eb9e54a647454ec

Disposition: FIXED
Commit: 2356523bbbb51a41bee7296d4eb9e54a647454ec
Evidence: `scripts/ci/check_legacy_growth_guard.py:2532` implements a finite monotonic conflict lattice; `tests/test_legacy_growth_guard.py:1668`, `tests/test_legacy_growth_guard.py:1696`, and `tests/test_legacy_growth_guard.py:1716` prove termination, order independence, repeated-run determinism, and fail-closed conflict handling. Exact-list assertions intentionally preserve the deterministic guard diagnostic contract.
Reason: The replacement removes first-writer semantics while retaining exact diagnostics as a stronger CI guard contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2128#pullrequestreview-4694141608 -> 2356523bbbb51a41bee7296d4eb9e54a647454ec

## Replacement Findings

| Source PR | Source head | Replacement evidence | Disposition |
| --- | --- | --- | --- |
| #2123 | `5105374e41d1d5cb65fc9e4e87ac6bbbb61531fd` | One lexical resolver covers `legacy_app.__dict__`, mapping calls, dynamic member lookup, local shadowing, and sibling scopes. | FIXED in `2356523bbbb51a41bee7296d4eb9e54a647454ec` |
| #2124 | `c22a6bd3064dd710749ed711c5f77c835157a60b` | Conditional module sync/async definitions use shared union-typed visitors, retain nested-local exclusions, and separate lambda expressions from statement bodies for exact pre-push MyPy parity. | FIXED in `2356523bbbb51a41bee7296d4eb9e54a647454ec` and `bcb9cf8616fcc8c0c1fbdf5b1447d2bf8a4f278d` |
| #2125 | `ff6557744c2f338c1a215654a6179fcbfef14dcb` | Nested direct imports, aliased `importlib`, aliased `import_module`, plain imports, and intermediate imported-module bindings are covered by the focused matrix. | FIXED in `2356523bbbb51a41bee7296d4eb9e54a647454ec` and `da4d3207b4a21cded1bb1ba2467d9e4dd6cb5b0d` |
| #2126 | `cfbc41b04e72e3f8d8d5a2bccb48b2ae13e18294` | Module binding counts exclude function parameters; the registrar-name shadow regression remains fail-closed. | FIXED in `2356523bbbb51a41bee7296d4eb9e54a647454ec` |
| #2127 | `a635f9f5445f39487d15884bfdd504cba107fb22` | Reassigned or unresolved `getattr(app, method)` becomes a deterministic dynamic registration fact; parameter shadowing remains scoped. | FIXED in `2356523bbbb51a41bee7296d4eb9e54a647454ec` |
| #2128 | `e0c6d68143e53d2cd95a93b35d7f6fc0a9b091e5` | Lifecycle aliases use a finite conflict lattice that cannot oscillate or silently keep only the first binding. | FIXED in `2356523bbbb51a41bee7296d4eb9e54a647454ec` |

## Premortem Closure

- Namespace aliases could leak across function, class, lambda, comprehension, or sibling scopes. FIXED by lexical local-name ownership, statement-order snapshots, and shadowing regressions.
- A conditional legacy binding could disappear at a branch join. FIXED by possible-reference lattice values and conditional/try/loop/with/match regressions.
- Reassigned or unresolved `getattr` could fail open. FIXED by deterministic dynamic facts for API-key namespace and route-registration surfaces.
- Lifecycle alias resolution could oscillate or depend on assignment order. FIXED by the finite monotonic conflict lattice and repeated-run/order-independence tests.
- A shared sync/async/lambda local-binding visitor could pass an `ast.expr` through a statement-only list and fail pre-push MyPy. FIXED by commit `bcb9cf8616fcc8c0c1fbdf5b1447d2bf8a4f278d`, which visits lambda bodies directly and iterates only sync/async statement bodies.
- Source-review evidence could be mapped before the exact nested-import matrix existed. FIXED by commit `da4d3207b4a21cded1bb1ba2467d9e4dd6cb5b0d`; mapping was created only afterward.

Decision: publish the consolidated replacement on owner PR #2128, then close #2123 through #2127 unmerged as superseded only after the replacement commits, tests, and this mapping are visible on GitHub.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/pr2128-legacy-growth-guard-post-main-result.json`
- Experiment: `exp-81724cfa1074`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- Backend: explicit `apple-container`; no `auto` selection and no Docker execution.
- Guest/runtime: `linux_arm64`, Apple Container `1.1.0`, immutable image digest `sha256:cefe9cfa20a89e2b24b4041c50d02f9bc202664d44e81470f962d5b72f063e13`.
- Isolation: `apple_internal_no_dns_plus_linux_unshare`; preflight `passed`.
- PASS: `python scripts/ci/check_legacy_growth_guard.py`.
- PASS: `python -m pytest -q tests/test_legacy_growth_guard.py`.
- PASS: `python -m pytest -q tests/test_review_pattern_oracles.py`.
- Negative controls: `promotion_ready=false`, `mutated_paths=[]`, and `shared_tree_untouched=true`.
- Authority: local, gitignored, evidence-only; it grants no merge, review-thread, promotion, or runtime authority.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/005d4877dd27.json`
- Goal: consolidate Codex PRs #2123 through #2127 into owner PR #2128 with scope-aware fail-closed legacy-growth analysis and deterministic tests.
- Candidate paths: `scripts/ci/check_legacy_growth_guard.py`, `tests/test_legacy_growth_guard.py`.
- Declared role order completed: `agent-coordinator -> security-auditor -> backend-engineer`.
- Additional premortem review completed: `cursor-specialist-agent -> architecture-specialist`.

## Implementation Evidence

- `git diff --name-only origin/main...HEAD` contains only `scripts/ci/check_legacy_growth_guard.py`, `tests/test_legacy_growth_guard.py`, and this mapping artifact.
- `scripts/ci/check_legacy_growth_guard.py:1677` owns lexical binding visibility, cloning, shadowing, and deterministic branch joins.
- `scripts/ci/check_legacy_growth_guard.py:1825` keeps lambda expressions type-distinct from sync/async statement bodies.
- `scripts/ci/check_legacy_growth_guard.py:1896` owns statement-ordered API-key reference analysis for sync and async scopes.
- `scripts/ci/check_legacy_growth_guard.py:2529` owns lifecycle reference fixed-point resolution.
- `tests/test_legacy_growth_guard.py:774`, `tests/test_legacy_growth_guard.py:975`, `tests/test_legacy_growth_guard.py:987`, `tests/test_legacy_growth_guard.py:1668`, and `tests/test_legacy_growth_guard.py:2312` cover the consolidated source findings and negative controls.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py` with exact scoped paths.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: complete `tests/test_legacy_growth_guard.py`.
- PASS: direct `scripts/ci/check_legacy_growth_guard.py` execution.
- PASS: `tests/test_review_pattern_oracles.py`.
- PASS: focused mypy for `scripts/ci/check_legacy_growth_guard.py` and `tests/test_legacy_growth_guard.py` with explicit package bases.
- PASS: exact pre-push MyPy hook for `scripts/ci/check_legacy_growth_guard.py` after commit `bcb9cf8616fcc8c0c1fbdf5b1447d2bf8a4f278d`.
- PASS: pre-push `pip-audit` after merging colleague-owned PR #2133 through fresh `origin/main`; no setup/dependency file was edited in the owner commits.
- PASS: `git diff --check`.
- PASS: `make validate-changed`.
- PASS: exact pre-commit-selected backend-test path with `BRANCH_DIFF_MODE=1`.
- PASS: `pre-commit run --all-files`.
- PASS: commit hooks, including Black, Ruff, detect-secrets, backend changed-file tests, and conventional-commit validation.
- Not run: local `make verify`, prohibited by the repository machine-budget rule. Canonical current-head CI remains required.

## Security Review

- The native Codex Security scan was stopped at the operator's direction after repeated continuity failures. It remained incomplete and unsealed and is not claimed as PASS or used as merge evidence.
- No further native Codex Security scan will be started for this lane.
- Repository-native security-auditor review, changed-file Bandit hooks, deterministic guard tests, and the explicit Apple Container Oracle remain the bounded local evidence.
- Current-head GitHub security/governance checks remain authoritative before merge readiness.

## Post-Open Review Closure

- Pending after the replacement head is published: `qa-engineer-agent -> bug-hunter -> security-auditor`.
- Native Codex Security diff scan/finding discovery: operator-directed stop; no PASS claim and no restart.
- Pending after role closure: `pulseplate-pr-review`.

## Merge Readiness

Not ready at artifact creation. Required before merge:

- Publish the replacement commits and this canonical artifact to the existing #2128 branch with a normal fast-forward push.
- Mirror `## Discussion Thread Pass`, `### Fixed in Commit Mapping`, and `## Merge Readiness` in the PR body.
- Close #2123 through #2127 unmerged only after published replacement evidence exists.
- Require terminal current-head CI, diff coverage at least 97%, and all required backend/security/governance jobs.
- Require no actionable CodeRabbit, Sourcery, or Cubic comments and no unresolved review threads.
- Pass the strict authenticated merge wrapper and the mandatory review wait-window.
- Do not absorb setup/dependency PR #2133 or Docker source-manifest work from #2117/#2120 into this lane.

## Deferred / Follow-ups

- Colleague PR #2133 is merged and synchronized through merge commit `30e3d6630f5ea523bef79d0305bc16a9d6fd1356`; its setup/dependency diff remains colleague-owned rather than duplicated in the owner commits.
- Docker source-manifest `review_by` work remains in the separate #2117/#2120 line.
- PR #2119 starts only after #2128 is merged and `main` is synchronized.
