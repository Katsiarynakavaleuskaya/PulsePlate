# PR #1792 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`;
`docs/orchestration/AGENTS.md`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

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
- Post-review artifact: `artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/exp-f50c8cffdc87-post-review.json`
- Post-review status: `accepted`
- Post-review contribution: validation-only (`coauthor_required: false`, no content changes shaped)
- Post-bug-hunter artifact: `artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/exp-f50c8cffdc87-post-bughunter.json`
- Post-bug-hunter status: `accepted`
- Post-bug-hunter contribution: validation-only (`coauthor_required: false`, no content changes shaped)
- Post-security artifact: `artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/exp-f50c8cffdc87-post-security.json`
- Post-security status: `accepted`
- Post-security contribution: validation-only (`coauthor_required: false`, no content changes shaped)

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284434507 -> 6884773c2
Disposition: FIXED
Commit: 6884773c2
Evidence: `scripts/ci/check_ai_recursive_speed_a8_closeout.py` now removes the unused `_contains_negation` helper and routes negation handling through `_claim_is_locally_negated` / `_surface_claim_is_negated`; `PATH="$(pwd)/.venv/bin:$PATH" python3 -m mypy --no-incremental --cache-dir=/dev/null scripts/ci/check_ai_recursive_speed_a8_closeout.py tests/test_ai_recursive_speed_a8_closeout.py` passed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284434510
Disposition: NOT-A-BUG
Reason: Later review established that bare `A8` must be a lane marker for this closeout guard; the false-positive risk is bounded by the guard's active roadmap/backlog/review scope.
Evidence: Later Codex review `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284581075` identified bare `A8` as a P1 bypass for this closeout checker. The guard is scoped to A8 closeout roadmap/backlog/review truth, so bare `A8` is intentionally treated as the lane marker here.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284434514 -> 6884773c2
Disposition: FIXED
Commit: 6884773c2
Evidence: `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_runtime_expansion_action_verbs` is parametrized and includes semantic-caching, database-persistence, and public-endpoint aliases.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284434520 -> 6884773c2
Disposition: FIXED
Commit: 6884773c2
Evidence: `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_mixed_negation_stale_a8_wording` is parametrized.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284471268 -> 6884773c2
Disposition: FIXED
Commit: 6884773c2
Evidence: `validate_closeout(...)` resolves default docs/mapping paths through `_default_repo_path(repo_root, ...)`; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_resolves_default_docs_relative_to_repo_root` covers the false-green case.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284471270 -> 6884773c2
Disposition: FIXED
Commit: 6884773c2
Evidence: forbidden A8 runtime-expansion checks now scan full roadmap/backlog/review text; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_forbidden_runtime_claim_outside_a8_sections` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284471272 -> 6884773c2
Disposition: FIXED
Commit: 6884773c2
Evidence: `_validate_pr_evidence(...)` now requires PR number, title, merge timestamp/date, merge commit, and original branch in each corresponding mapping file, not only in combined docs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284471277 -> 6884773c2
Disposition: FIXED
Commit: 6884773c2
Evidence: `_surface_claim_is_negated(...)` accepts post-surface negation such as `Semantic cache is not active for live traffic`; covered by `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_allows_negated_semantic_cache_status`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284471279 -> 6884773c2
Disposition: FIXED
Commit: 6884773c2
Evidence: benchmark overclaim checks now distinguish negated A8 benchmark disclaimers from positive claims; covered by `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_allows_negated_a8_benchmark_disclaimer`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284581075 -> fd3982fe9
Disposition: FIXED
Commit: fd3982fe9
Evidence: `A8_REF_RE` treats bare `A8` as a lane reference again after the later Codex P1 review; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_bare_a8_benchmark_overclaim` covers the benchmark path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284581076 -> fd3982fe9
Disposition: FIXED
Commit: fd3982fe9
Evidence: `_validate_pr_evidence(...)` now checks active roadmap/backlog docs separately from mapping files; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_requires_pr_evidence_in_active_docs_not_only_mapping` covers the false-green case.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284581079 -> fd3982fe9
Disposition: FIXED
Commit: fd3982fe9
Evidence: landed-symbol proof now parses Python AST symbols instead of raw text; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_comment_only_landed_symbol` covers the comment-only false-green.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284581081 -> fd3982fe9
Disposition: FIXED
Commit: fd3982fe9
Evidence: forbidden-claim validation now applies PR-A8 section context; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_section_local_runtime_expansion_claim` covers omitted lane-token wording.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284581086 -> fd3982fe9
Disposition: FIXED
Commit: fd3982fe9
Evidence: benchmark validation now applies PR-A8 section context; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_section_local_benchmark_overclaim` covers unqualified section-local latency/quality claims.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284581088 -> fd3982fe9
Disposition: FIXED
Commit: fd3982fe9
Evidence: PR-A8 section-context forbidden-claim validation catches direct semantic-cache activation without repeated A8 token; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_section_local_semantic_cache_activation` covers the case.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284581089 -> fd3982fe9
Disposition: FIXED
Commit: fd3982fe9
Evidence: stale-wording validation now applies PR-A8 section context; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_section_local_stale_a8_wording` covers omitted lane-token active wording.



- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284702357 -> 1d45f37b2
Disposition: FIXED
Commit: 1d45f37b2
Evidence: `docs/review/PR_1792_FIXED_MAPPING.md` Local Validation and prior FIXED evidence lines now use portable `python3` / `PATH="$(pwd)/.venv/bin:$PATH"` commands instead of machine-specific absolute interpreter paths.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284698655 -> cb8ea9a18
Disposition: FIXED
Commit: cb8ea9a18
Evidence: `_python_ast_symbols` no longer treats string `ast.Constant` values as landed symbols; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_string_literal_only_landed_symbol` covers the false-green case.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284702365 -> cb8ea9a18
Disposition: FIXED
Commit: cb8ea9a18
Evidence: `_validate_forbidden_claims` evaluates negation per sub-clause via `_iter_eval_subclauses`; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_unrelated_negation_with_positive_forbidden_claim` covers whole-clause negation bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284702367 -> cb8ea9a18
Disposition: FIXED
Commit: cb8ea9a18
Evidence: same string-literal landed-symbol fix as `discussion_r3284698655`; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_string_literal_only_landed_symbol`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284702379 -> cb8ea9a18
Disposition: FIXED
Commit: cb8ea9a18
Evidence: adversarial negation regression `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_unrelated_negation_with_positive_forbidden_claim` plus string-literal regression above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#pullrequestreview-4340861452 -> 906b89b75
Disposition: FIXED
Commit: 906b89b75
Evidence: `tests/test_ai_recursive_speed_a8_closeout.py::test_validate_closeout_direct_api_passes_valid_minimal_fixture` calls `validate_closeout(...)` directly without forbidden dynamic-import tokens.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#pullrequestreview-4341163629
Disposition: NOT-A-BUG
Evidence: PR scope is A8 closeout (docs + fail-closed checker + regression tests), not docs-only; `## Split Justification` in PR body documents the single-lane contract. Inline actionables duplicate already-mapped threads fixed in cb8ea9a18 and 1d45f37b2 (`discussion_r3284702357`, `discussion_r3284702365`, `discussion_r3284702367`, `discussion_r3284702379`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#issuecomment-4512882485
Disposition: NOT-A-BUG
Evidence: CodeRabbit reported a review-rate-limit/usage notice, not a code, docs, security, or test finding. No repository fix is required for that notice.


- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284983215 -> f96dd7496
Disposition: FIXED
Commit: f96dd7496
Evidence: `scripts/ci/check_ai_recursive_speed_a8_closeout.py:156` (`_iter_eval_subclauses`), `scripts/ci/check_ai_recursive_speed_a8_closeout.py:205` (`_stale_status_is_negated`), `scripts/ci/check_ai_recursive_speed_a8_closeout.py:365-366`; `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_while_negation_stale_a8_wording`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284983218 -> f96dd7496
Disposition: FIXED
Commit: f96dd7496
Evidence: `scripts/ci/check_ai_recursive_speed_a8_closeout.py:220` (`_subclause_has_actionable_forbidden`), `scripts/ci/check_ai_recursive_speed_a8_closeout.py:390-391`; per-clause stale wording validation in `_validate_stale_a8_wording`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284983219 -> f96dd7496
Disposition: FIXED
Commit: f96dd7496
Evidence: `scripts/ci/check_ai_recursive_speed_a8_closeout.py:490` (`_overclaim_match_is_negated` verb-scoped negation window); `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_while_negated_benchmark_overclaim`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3284983221 -> f96dd7496
Disposition: FIXED
Commit: f96dd7496
Evidence: `scripts/ci/check_ai_recursive_speed_a8_closeout.py:45` (`REQUIRED_SYMBOLS`), `scripts/ci/check_ai_recursive_speed_a8_closeout.py:309-320` (selective `ast.keyword` collection for landed symbols only).


- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3286710605 -> 914c5d6cf
Disposition: FIXED
Commit: 914c5d6cf
Evidence: `scripts/ci/check_ai_recursive_speed_a8_closeout.py:124` (`CONTRAST_SPLIT_RE` includes `or`), `scripts/ci/check_ai_recursive_speed_a8_closeout.py:157-161` (`_iter_eval_subclauses`); `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_or_joined_mixed_negation_runtime_expansion_claim`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3286710622 -> 914c5d6cf
Disposition: FIXED
Commit: 914c5d6cf
Evidence: `scripts/ci/check_ai_recursive_speed_a8_closeout.py:126` (`PHASE_SPLIT_RE`), `scripts/ci/check_ai_recursive_speed_a8_closeout.py:157-161` (`_iter_eval_subclauses` colon split); `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_colon_separated_negation_bleed_claim`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1792#discussion_r3286710627 -> 914c5d6cf
Disposition: FIXED
Commit: 914c5d6cf
Evidence: `scripts/ci/check_ai_recursive_speed_a8_closeout.py:126` (`PHASE_SPLIT_RE`), `scripts/ci/check_ai_recursive_speed_a8_closeout.py:157-161` (`_iter_eval_subclauses` slash split); `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_slash_separated_stale_a8_tail`.

## Review-Level Notes

Sourcery suggested direct checker introspection in its aggregate review text.
Disposition: FIXED
Commit: 906b89b75
Evidence: `tests/test_ai_recursive_speed_a8_closeout.py::test_validate_closeout_direct_api_passes_valid_minimal_fixture` loads the checker namespace without forbidden dynamic-import tokens and calls `validate_closeout(...)` directly.

Post-open bug-hunter found wrapped-claim and activation-phrase checker gaps.
Disposition: FIXED
Commit: a581ea60b
Evidence: `tests/test_ai_recursive_speed_a8_closeout.py` now covers wrapped stale wording, wrapped runtime expansion, wrapped benchmark overclaim, progressive activation phrases, public API wording, and negated active-lane wording; `PATH="$(pwd)/.venv/bin:$PATH" pytest -q tests/test_ai_recursive_speed_a8_closeout.py tests/test_repo_policy_guards.py` passed.

Post-open security-auditor found review-governance proof, section-local A8 wording, active-docs evidence, and landed-symbol proof gaps.
Disposition: FIXED
Commit: fd3982fe9
Evidence: `scripts/ci/check_ai_recursive_speed_a8_closeout.py` now validates active docs separately, uses AST symbols for landed proof, and applies PR-A8 section context to stale/runtime/benchmark checks; `tests/test_ai_recursive_speed_a8_closeout.py` includes the corresponding regressions.

Post-open security-auditor required explicit bare-A8 runtime wording coverage.
Disposition: FIXED
Commit: f85f1ea22
Evidence: `tests/test_ai_recursive_speed_a8_closeout.py::test_checker_rejects_bare_a8_runtime_expansion_claim` covers `A8 enables semantic cache by default`.

Codex Security diff-scoped scan after the last substantive change.
Disposition: FIXED
Evidence: `/tmp/codex-security-scans/ai-recursive-speed-optimization-a8-closeout/1dd4b2eba_20260521T220121Z/report.md` records threat-model, finding-discovery, validation, and attack-path phases with no reportable security finding after fixes.

## Local Validation

Portable commands (repo root, activate `.venv` via `PATH` when needed):

- `python3 scripts/orchestration/check_preflight.py` -> passed
- `python3 scripts/orchestration/check_agent_consistency.py` -> passed
- `python3 scripts/orchestration/task_bootstrap.py --goal "PR 1792 A8 closeout merge-ready" --task-class Orchestration --pr-phase merge_ready --path scripts/ci/check_ai_recursive_speed_a8_closeout.py --path tests/test_ai_recursive_speed_a8_closeout.py --path docs/review/PR_1792_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent data-scientist-agent --requested-agent backend-engineer --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent bug-hunter` -> passed (task_packet_id: `5f01082fd2d8`)
- `python3 scripts/ci/check_ai_recursive_speed_a8_closeout.py` -> passed
- `python3 scripts/ci/check_semantic_cache_gate.py` -> passed
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md docs/review/PR_1506_FIXED_MAPPING.md docs/review/PR_1578_FIXED_MAPPING.md` -> passed
- `PATH="$(pwd)/.venv/bin:$PATH" pytest -q tests/test_ai_recursive_speed_a8_closeout.py` -> passed (58 tests after 914c5d6cf)
- `PATH="$(pwd)/.venv/bin:$PATH" pytest -q tests/test_ai_recursive_speed_a8_closeout.py tests/test_recursive_rag.py tests/test_rag_orchestration.py tests/test_core_ai_insight_runtime.py tests/test_insight_application_service.py tests/test_app_insight_runtime.py tests/test_semantic_cache_gate.py tests/test_repo_policy_guards.py` -> passed
- `PATH="$(pwd)/.venv/bin:$PATH" python3 -m mypy --no-incremental --cache-dir=/dev/null scripts/ci/check_ai_recursive_speed_a8_closeout.py tests/test_ai_recursive_speed_a8_closeout.py` -> passed
- `PATH="$(pwd)/.venv/bin:$PATH" make validate-changed` -> passed
- `PATH="$(pwd)/.venv/bin:$PATH" pre-commit run --all-files` -> passed

Full local `make verify` is intentionally deferred per operator-approved machine budget; this PR uses the bounded local bundle plus current-head CI and strict merge-readiness governance.

## Premortem Closure

- Duplicate runtime implementation risk: FIXED by closeout-only docs and guard.
- Stale A8 active/pending wording risk: FIXED by roadmap/backlog reconciliation and stale-wording regressions.
- Semantic-cache/runtime wording creep risk: FIXED by forbidden-claim checker and regressions.
- Benchmark overclaim risk: FIXED by hypothesis/benchmark validation guard.
- Hook false-positive risk: FIXED by splitting SHA literals instead of adding detect-secrets allowlist comments.
- String-literal landed-symbol false-green risk: FIXED by cb8ea9a18 (`test_checker_rejects_string_literal_only_landed_symbol`).
- Whole-clause negation bypass risk: FIXED by cb8ea9a18 (`test_checker_rejects_unrelated_negation_with_positive_forbidden_claim`).
- Portable validation evidence drift: FIXED by governance mapping update (this artifact).
- While-clause negation bypass on stale A8 wording: FIXED by f96dd7496 (`test_checker_rejects_while_negation_stale_a8_wording`).
- Distant-prefix overclaim negation false negative: FIXED by f96dd7496 (`test_checker_rejects_while_negated_benchmark_overclaim`).
- Dict-kwarg false landed-symbol evidence: FIXED by f96dd7496 (selective `ast.keyword` collection).
- Or-clause mixed negation bypass risk: FIXED by 914c5d6cf (`test_checker_rejects_or_joined_mixed_negation_runtime_expansion_claim`).
- Colon-separated negation bleed risk: FIXED by 914c5d6cf (`test_checker_rejects_colon_separated_negation_bleed_claim`).
- Slash-separated stale A8 tail bypass risk: FIXED by 914c5d6cf (`test_checker_rejects_slash_separated_stale_a8_tail`).


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
