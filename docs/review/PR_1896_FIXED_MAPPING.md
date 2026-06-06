# PR #1896 Fixed In Commit Mapping

PR: `feat(ai): add semantic cache shadow admission harness`
Branch: `codex/semantic-cache-shadow-admission-harness-v1`
Base: `origin/main` at `86e40c9f9f188ca0f74e720169c0b88cbe0cabaf`
Implementation commit: `d5723e888`

## Scope

This PR adds Semantic Cache Shadow Admission Harness v1: an internal-only,
deterministic shadow/offline report over the already-merged Semantic Cache
Offline Admission Runner v1. The report projects safe semantic-cache admission
labels onto synthetic `/insight`, RAG, degraded retrieval, verification-disabled,
missing/blocked bundle, philosophical runtime, and mismatch path labels.

## Out Of Scope

Runtime serving, cache read/write, `/insight` wiring, public API, OpenAPI, DB,
Redis/GPTCache clients, embeddings, vector search, provider calls, frontend/iOS,
Slack, GraphRAG, and semantic-cache gate opening remain out of scope.

## Lane Start Provenance

- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch/worktree: `codex/semantic-cache-shadow-admission-harness-v1` /
  `worktrees/semantic-cache-shadow-admission-harness-v1`
- Packet: `artifacts/orchestration/task_packets/ac8ad07cad01.json`
- Required pre-open role order completed:
  `agent-coordinator -> architecture-specialist -> security-auditor -> backend-engineer -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent`.

## Pre-Open Findings

### Role Findings

- `agent-coordinator`: FIXED. Evidence: scope stayed internal-only with no
  runtime serving, public API, OpenAPI, DB, provider, frontend/iOS, Slack,
  GraphRAG, or gate-opening changes.
- `architecture-specialist`: FIXED. Evidence:
  `core/ai/semantic_cache_shadow_admission_harness.py` is a pure composer and
  `scripts/ci/check_semantic_cache_shadow_admission_harness.py` owns report IO
  and schema validation.
- `security-auditor`: FIXED. Evidence: authority flags remain false, semantic
  cache gate stays closed, raw-leak checks scan report/schema text, and source
  refs are repo-relative guarded.
- `backend-engineer`: FIXED. Evidence: the harness reuses #1892 stable safe
  report output rather than serializing SC-G2 records with raw/normalized query
  material.
- `qa-engineer-agent`: FIXED. Evidence:
  `tests/core/ai/test_semantic_cache_shadow_admission_harness.py` covers
  byte-stable rendering, canonical path ordering, path-label projection,
  provenance coverage, closed authority, raw-leak rejection, schema drift,
  source-ref traversal, CLI write confinement, and import/call boundaries.
- `bug-hunter`: FIXED. Evidence: Docs Phase1 deletion/schema-only paths are
  guarded, workflow route-contract suites include the focused test, and
  generated report/schema equality prevents stale report false greens.
- `cursor-specialist-agent`: FIXED. Evidence: generated report/schema were
  produced through the checker, not hand-authored, and `make validate-changed`
  was rerun after a real branch diff existed.

### Premortem Findings

- PM-1 raw/normalized query leakage through SC-G2 serialization: FIXED in
  `d5723e888`. Evidence: the harness consumes #1892 stable safe output and
  `tests/core/ai/test_semantic_cache_shadow_admission_harness.py` rejects raw
  prompt/query/context/answer samples.
- PM-2 shadow labels being misread as runtime cache authority: FIXED in
  `d5723e888`. Evidence: final status is `shadow_report_only`, backend status is
  `no_selection`, and tests reject authority drift.
- PM-3 Docs Phase1 missing schema/deletion-only drift: FIXED in `d5723e888`.
  Evidence: `scripts/ci/check_docs_phase1_gates.py`, `.github/workflows/ci.yml`,
  `tests/test_docs_phase1_gates.py`, and
  `tests/test_ci_workflow_pr_size_governance_contract.py` cover the new
  report/schema and deletion-aware targets.
- PM-4 runtime scope creep through RAG/philosophy imports: FIXED in
  `d5723e888`. Evidence: path cases use synthetic labels/fingerprints only and
  the AST import/call guard covers the core harness.
- PM-5 `validate-changed` false signal before commit: FIXED operationally.
  Evidence: the final `make validate-changed` run after commit selected the new
  changed Python/test guard surface and passed.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-2c12875da225.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-2c12875da225.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- `shared_tree_untouched=true`
- `coauthor_required=false`
- Oracle commands executed: `2`
- Oracle commands: `python scripts/ci/check_semantic_cache_shadow_admission_harness.py --check`; `python -m pytest -q tests/core/ai/test_semantic_cache_shadow_admission_harness.py tests/test_docs_phase1_gates.py tests/test_ci_workflow_pr_size_governance_contract.py`

## Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_semantic_cache_shadow_admission_harness.py --check`
- PASS: `python3 scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- PASS: focused pytest for
  `tests/core/ai/test_semantic_cache_shadow_admission_harness.py`,
  `tests/core/ai/test_semantic_cache_offline_admission_runner.py`,
  `tests/core/ai/test_exact_fuzzy_cache.py`,
  `tests/core/ai/test_cache_observability.py`,
  `tests/core/ai/test_bounded_insight_semantic_cache.py`,
  `tests/core/ai/test_semantic_cache_backend_selection.py`,
  `tests/test_docs_phase1_gates.py`,
  `tests/test_ci_workflow_pr_size_governance_contract.py`,
  `tests/test_semantic_cache_gate.py`,
  `tests/test_rag_orchestration.py`,
  `tests/test_philosophical_runtime.py`, and
  `tests/test_insight_application_service.py`.
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS after review-driven fixes in `ea2d5e498`:
  `python3 scripts/ci/check_semantic_cache_shadow_admission_harness.py --check`
- PASS after review-driven fixes in `ea2d5e498`: focused pytest for the
  semantic-cache shadow/offline, SC-G2/SC-G3/SC-G4/SC-G5, Docs Phase1,
  workflow route-contract, semantic-cache gate, RAG orchestration,
  philosophical runtime, and insight application service suites.
- PASS after review-driven fixes in `ea2d5e498`: `make validate-changed`
- PASS after review-driven fixes in `ea2d5e498`: `pre-commit run --all-files`
- PASS: pre-push hooks, including changed-files mypy, pip-audit, backend
  pre-push tests, full-repo Bandit, and Docker build test.

Full local `make verify` was not run under the operator-approved machine-heavy
path. Current-head CI parity remains required before merge readiness.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Pre-open role order completed.
- Premortem completed and findings fixed/dispositioned above.
- Experiment Runner oracle-only evidence completed.
- Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass completed.
- Codex Security diff scan / finding discovery completed.
- `pulseplate-pr-review` completed.

Post-open review threads must be recorded below with `FIXED`, `NOT-A-BUG`, or
`DEFERRED` disposition before resolution.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#pullrequestreview-4442302334 -> e04544951
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367074456 -> e04544951
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367074458 -> e04544951
Disposition: FIXED
Commit: e04544951
Evidence: Cubic identified two mapping/body format issues in `docs/review/PR_1896_FIXED_MAPPING.md`; the artifact now includes the exact canonical Phase2 checkboxes and a valid GitHub review-thread mapping entry instead of non-canonical no-actionable prose.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367098827 -> bbc2f897a
Disposition: FIXED
Commit: bbc2f897a
Evidence: `tests/helpers/semantic_cache_import_guard.py` no longer globally allowlists `core.ai.semantic_cache_offline_admission_runner`; `tests/core/ai/test_semantic_cache_shadow_admission_harness.py` now passes the allowance only for the shadow harness and asserts the default guard still rejects that import.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367098828
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor e04544951 HEAD` passes on the current branch, so the Cubic Phase2 proof commit is reachable from the current PR history; `GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1896 --require-auth` also passed before this update for the resolved Cubic threads.
Reason: The concern described a stale/sibling-head evaluation; the current branch history contains the referenced proof commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367098829 -> 22542bbf3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#pullrequestreview-4442351938 -> 22542bbf3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367101076 -> 22542bbf3
Disposition: FIXED
Commit: 22542bbf3
Evidence: `core/ai/semantic_cache_shadow_admission_harness.py` now validates fingerprints with `_DIGEST_PREFIX_RE`, and `tests/core/ai/test_semantic_cache_shadow_admission_harness.py` rejects bare `sha256:` labels.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367098830 -> bbc2f897a
Disposition: FIXED
Commit: bbc2f897a
Evidence: `core/ai/semantic_cache_shadow_admission_harness.py`, `scripts/ci/check_semantic_cache_shadow_admission_harness.py`, and the generated report/schema now include evidence-asset lineage fields for asset type, upstream assets, artifact fingerprint, idempotency key, replay behavior, and admission behavior with focused tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367141396
Disposition: NOT-A-BUG
Evidence: `git show HEAD:docs/review/PR_1896_FIXED_MAPPING.md` shows the
`bug-hunter` evidence line already uses `guarded`; local
`docs/review/PR_1896_FIXED_MAPPING.md` lines 53-55 also contain `guarded`, not
`guarde`.
Reason: The CodeRabbit typo finding is stale against the current PR head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367141892 -> ea2d5e498
Disposition: FIXED
Commit: ea2d5e498
Evidence: `core/ai/semantic_cache_shadow_admission_harness.py` now passes the
requested `produced_at` into the offline runner projection and includes
`produced_at` in the stable report payload; the generated report/schema include
the top-level ISO UTC field, and
`tests/core/ai/test_semantic_cache_shadow_admission_harness.py` proves a
non-default timestamp changes the stable evidence fingerprint.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367141893 -> ea2d5e498
Disposition: FIXED
Commit: ea2d5e498
Evidence: `core/ai/semantic_cache_shadow_admission_harness.py` now computes
real `sha256:<64 lowercase hex>` upstream fingerprints from the offline runner
report, verification contracts, and semantic-cache gate document; the checker
and schema enforce that digest shape, with focused test coverage for upstream
fingerprint drift.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367141894 -> ea2d5e498
Disposition: FIXED
Commit: ea2d5e498
Evidence: `missing_bundle_fail_closed_shadow` now uses
`not_evaluated_missing_bundle` instead of `admission_blocked_candidate`; the
generated report shows `lookup_decision=not_evaluated`,
`false_hit_is_false_hit=false`, `stop_serving=false`, and focused tests assert
the fail-closed-before-cache-evaluation behavior.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1896#discussion_r3367143853 -> ea2d5e498
Disposition: FIXED
Commit: ea2d5e498
Evidence:
`scripts/ci/check_semantic_cache_shadow_admission_harness.py` and
`docs/orchestration/contracts/SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT.schema.json`
now use the same strict idempotency-key pattern
`^idem:semantic-cache-shadow-admission-harness:[a-f0-9]{16}$`.

## Post-Open Role And Security Evidence

- `qa-engineer-agent`: PASS at `4ede03652`; Phase2 body/artifact validation,
  strict review-thread disposition guard, shadow checker, semantic-cache
  closed-gate check, focused harness/offline/docs/workflow tests, and diff
  whitespace checks passed with no raw leakage or runtime/cache/public surface
  widening.
- `bug-hunter`: PASS at `4ede03652`; found no blocker in deterministic
  fingerprinting/report stability, evidence-asset lineage, scoped
  offline-runner import guard, checker/schema consistency, raw-leak protection,
  or semantic-cache authority boundaries.
- `security-auditor`: PASS at `4ede03652`; confirmed closed semantic-cache
  gate, false runtime/cache authority flags, label-only/no-selection backend
  context, deterministic safe evidence-asset metadata, repo-relative source
  refs, no provider/network/cache/storage calls, and no public
  API/OpenAPI/DB/frontend/iOS/Slack/vector/GraphRAG widening.
- Codex Security diff scan: PASS/no findings at final head `4ede03652`. Final
  report:
  `/tmp/codex-security-scans/BMI-App_2025_clean/pr1896-shadow-admission-final-20260606T101959Z/report.md`.
- `pulseplate-pr-review`: PASS with one advisory large-diff note.
  Disposition: NOT-A-BUG. Evidence: generated report/schema account for most
  of the line count; this PR is intentionally medium-scope and `make
  validate-changed`, focused semantic-cache suites, Phase2 gates, and
  pre-commit passed before the later review-driven fixes.

## Merge Readiness

- Not claimed.
- Current-head CI, bot review state, strict disposition checks, strict
  merge-readiness checks, and wait-window remain pending.
