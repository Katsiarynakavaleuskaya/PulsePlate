# PR #1792 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`;
`docs/orchestration/AGENTS.md`.

- [ ] Discussion-thread pass completed after CodeRabbit/Sourcery/Cubic and human/bot review.
- [ ] Fixed in commit mapping completed after all actionable comments are dispositioned.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/a9d4e8cabcf7.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/ai-recursive-speed-optimization-a8-closeout`
- Worktree: `worktrees/ai-recursive-speed-optimization-a8-closeout`
- Coordinator order: `agent-coordinator -> architecture-specialist -> data-scientist-agent -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-f50c8cffdc87.json`
- Status: `accepted`
- Oracles:
  - `python scripts/ci/check_ai_recursive_speed_a8_closeout.py`
  - `python scripts/ci/check_semantic_cache_gate.py`
  - focused pytest set
- Contribution: `oracle_review`
- Co-author required: yes
- Commit trailer used: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Fixed in Commit Mapping

Post-open bot review findings are fixed or dispositioned below. Review threads must remain
open until the PR-body mirror and GitHub thread disposition pass are updated.

### Sourcery

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284434507 -> 6884773c2
Disposition: FIXED
Evidence: `scripts/ci/check_ai_recursive_speed_a8_closeout.py` now removes the unused `_contains_negation` helper and routes negation handling through `_claim_is_locally_negated` / `_surface_claim_is_negated`; `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null scripts/ci/check_ai_recursive_speed_a8_closeout.py tests/test_ai_recursive_speed_a8_closeout.py` passed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284434510 -> 6884773c2
Disposition: FIXED
Evidence: `A8_REF_RE` no longer accepts a bare `a8` token; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_does_not_treat_bare_a8_as_lane_reference` proves the false-positive guard.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284434514 -> 6884773c2
Disposition: FIXED
Evidence: `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_runtime_expansion_action_verbs` is parametrized and includes semantic-caching, database-persistence, and public-endpoint aliases.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284434520 -> 6884773c2
Disposition: FIXED
Evidence: `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_mixed_negation_stale_a8_wording` is parametrized.

Review-level note: Sourcery suggested direct checker introspection. Disposition: FIXED.
Commit: 246e08488
Evidence: `tests/test_ai_recursive_speed_a8_closeout.py::test_validate_closeout_direct_api_passes_valid_minimal_fixture` imports the checker module and calls `validate_closeout(...)` directly.

### Codex

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284471268 -> 6884773c2
Disposition: FIXED
Evidence: `validate_closeout(...)` resolves default docs/mapping paths through `_default_repo_path(repo_root, ...)`; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_resolves_default_docs_relative_to_repo_root` covers the false-green case.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284471270 -> 6884773c2
Disposition: FIXED
Evidence: forbidden A8 runtime-expansion checks now scan full roadmap/backlog/review text; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_forbidden_runtime_claim_outside_a8_sections` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284471272 -> 6884773c2
Disposition: FIXED
Evidence: `_validate_pr_evidence(...)` now requires PR number, title, merge timestamp/date, merge commit, and original branch in each corresponding mapping file, not only in combined docs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284471277 -> 6884773c2
Disposition: FIXED
Evidence: `_surface_claim_is_negated(...)` accepts post-surface negation such as `Semantic cache is not active for live traffic`; covered by `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_allows_negated_semantic_cache_status`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284471279 -> 6884773c2
Disposition: FIXED
Evidence: benchmark overclaim checks now distinguish negated A8 benchmark disclaimers from positive claims; covered by `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_allows_negated_a8_benchmark_disclaimer`.

### CodeRabbit

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#issuecomment-4512882485
Disposition: NOT-A-BUG
Evidence: CodeRabbit reported a review-rate-limit/usage notice, not a code, docs, security, or test finding. No repository fix is required for that notice.

## Local Validation

- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/orchestration/check_preflight.py` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/orchestration/check_agent_consistency.py` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/ci/check_ai_recursive_speed_a8_closeout.py` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/ci/check_semantic_cache_gate.py` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md docs/review/PR_1506_FIXED_MAPPING.md docs/review/PR_1578_FIXED_MAPPING.md` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_ai_recursive_speed_a8_closeout.py tests/test_recursive_rag.py tests/test_rag_orchestration.py tests/test_core_ai_insight_runtime.py tests/test_insight_application_service.py tests/test_app_insight_runtime.py tests/test_semantic_cache_gate.py tests/test_repo_policy_guards.py` -> passed
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null scripts/ci/check_ai_recursive_speed_a8_closeout.py tests/test_ai_recursive_speed_a8_closeout.py` -> passed
- `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH make validate-changed` -> passed after the implementation commit
- `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH pre-commit run --all-files` -> passed

Full local `make verify` is intentionally deferred per operator-approved machine budget; this PR uses the bounded local bundle plus current-head CI and strict merge-readiness governance.

## Premortem Closure

- Duplicate runtime implementation risk: FIXED by closeout-only docs and guard.
- Stale A8 active/pending wording risk: FIXED by roadmap/backlog reconciliation and stale-wording regressions.
- Semantic-cache/runtime wording creep risk: FIXED by forbidden-claim checker and regressions.
- Benchmark overclaim risk: FIXED by hypothesis/benchmark validation guard.
- Hook false-positive risk: FIXED by splitting SHA literals instead of adding detect-secrets allowlist comments.

## Merge Readiness

- [ ] Current-head CI is green for latest PR head.
- [ ] Required checks complete with no pending jobs.
- [ ] All review threads resolved on GitHub after disposition updates.
- [ ] No actionable CodeRabbit/Sourcery/Cubic comments remain.
- [ ] Codex Security threat-model, security-scan, and validation completed after PR open and after the last substantive change.
- [ ] `check_pr_body_phase2_gates.py` passes.
- [ ] `check_review_threads_disposition.py --require-auth` passes.
- [ ] Strict merge-readiness wrapper with auth passes.
- [ ] Final wait-window completed.
