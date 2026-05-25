# PR #1827 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`;
`docs/orchestration/AGENTS.md`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open pass refreshed after CodeRabbit, Sourcery, Codex Review, QA,
bug-hunter, and security-auditor activity.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/8245eb73c1c8.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/ai-rag-hardening-a2-closeout`
- Worktree: isolated closeout worktree; local path intentionally omitted from
  committed governance evidence
- Coordinator order: `agent-coordinator -> architecture-specialist -> data-scientist-agent -> backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor -> dev-operator`

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-bdeb5cf56f40.json`
- Status: `accepted`
- Oracles:
  - `python -B scripts/ci/check_ai_rag_hardening_a2_closeout.py`
  - `python -B scripts/ci/check_semantic_cache_gate.py`
  - focused pytest set (`54 passed`)
- Contribution: `oracle_review`
- Co-author required: yes
- Commit trailer used: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
- Post-review artifact: `artifacts/orchestration/experiments/results/exp-bdeb5cf56f40-post-review.json`
- Post-review status: `accepted`
- Post-review contribution: `fixed_mapping_review`
- Post-review co-author required: yes
- Post-review commit trailer used: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
- Artifact references are local ignored governance evidence only; no
  `artifacts/orchestration/` files are tracked by this PR.

## Premortem Disposition

- FIXED: A2 duplicate-runtime risk. Evidence: PR #1827 scope is closeout-only,
  and `scripts/ci/check_ai_rag_hardening_a2_closeout.py` rejects runtime scope
  expansion claims.
- FIXED: semantic-cache gate-open ambiguity. Evidence:
  `scripts/ci/check_ai_rag_hardening_a2_closeout.py` validates the exact
  `closed / false / false / true` marker set and duplicate/conflicting marker
  regression tests.
- FIXED: comment/string spoof risk for landed RAG evidence. Evidence:
  AST-based landed-symbol checks and regression tests in
  `tests/test_ai_rag_hardening_a2_closeout.py`.
- FIXED: historical PR #1415 merge-readiness ambiguity. Evidence:
  `docs/review/PR_1415_FIXED_MAPPING.md` now uses post-merge historical wording.
- FIXED: advisory role-agent drift. Evidence: the first data-scientist output
  was treated as untrusted draft input; the role was rerun read-only and the
  resulting implementation was accepted only after coordinator, architecture,
  backend, QA, bug-hunter, security, dev-operator, local gates, and Experiment
  Runner review.

## Local Validation

- PASS: `python scripts/orchestration/check_preflight.py`
- PASS: `python scripts/orchestration/check_agent_consistency.py`
- PASS: `python scripts/ci/check_ai_rag_hardening_a2_closeout.py`
- PASS: `python scripts/ci/check_semantic_cache_gate.py`
- PASS: `python scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md docs/review/PR_1415_FIXED_MAPPING.md`
- PASS: `python -m pytest -q tests/test_ai_rag_hardening_a2_closeout.py tests/test_rag_orchestration.py tests/test_vector_rag.py tests/test_insight_rag_response_fields.py tests/test_semantic_cache_gate.py tests/test_repo_policy_guards.py`
- PASS: `python -m mypy --no-incremental --cache-dir=/dev/null scripts/ci/check_ai_rag_hardening_a2_closeout.py tests/test_ai_rag_hardening_a2_closeout.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks, including changed-file mypy, pip-audit, backend tests,
  full-repo Bandit, and docker build test

Full local `make verify` is intentionally deferred under the
operator-approved machine-heavy PR exception. This PR uses narrow local gates
plus current-head CI and strict merge-readiness governance.

## Post-Open Agent Review Disposition

- FIXED: QA P1 `pr_scope_guard` red. Evidence: PR body now includes `## Split Justification`.
- FIXED: QA/Bug/Security stale post-open disposition. Evidence: this artifact now maps bot activity and review comments, and the PR body mirror was refreshed.
- FIXED: QA/Bug/Security stale commit bookkeeping. Evidence: PR body commit breakdown now includes `69857f392`, `6e105d974`, and `ca589415a`.
- FIXED: Security P1 checker failure on class-method tests. Evidence: `ca589415a` accepts pytest-discoverable `Test*` class methods while rejecting nested/dead-scope and skip/xfail cases.
- NOT-A-BUG: Security P2 packet/result artifact references. Reason: Phase2 governance validates local ignored artifact references as evidence pointers. Evidence: artifact files are not tracked, and this artifact explicitly records them as local ignored governance evidence only. Worktree path text was removed.

## Codex Security Evidence

- Phase: `threat-model` completed using repository threat-model guidance from
  `AGENTS.md` and PR-local security boundaries.
- Phase: `security-scan` / finding discovery completed against
  `origin/main...HEAD`.
- Phase: `validation` completed for the no-candidate result.
- Result: no reportable security findings.
- Local scan ids: `pr1827_1e1a05228fb7_20260525T104758Z`; refreshed after checker hardening as `pr1827_db19fb52b_20260525T111945Z`, `pr1827_f802efe2c_20260525T115151Z`, `pr1827_9e96f799d_20260525T122420Z`, and `pr1827_afc897fc2_20260525T125555Z`
- Evidence: no runtime route, provider, cache, persistence, OpenAPI, database,
  Redis/GPTCache, or semantic-cache serving surface is added; semantic-cache
  gate checker passed; full pre-commit and pre-push security hooks passed.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297552749 -> ca589415a
Disposition: FIXED
Commit: ca589415a
Evidence: `_module_function_names(...)` now only accepts module-scope runtime functions; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_nested_runtime_function_marker_spoof` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297552751 -> ca589415a
Disposition: FIXED
Commit: ca589415a
Evidence: `_discoverable_test_function_nodes(...)` accepts pytest-discoverable module tests and `Test*` class methods only, while rejecting skipped, xfailed, and nested/dead-scope markers. Regression tests cover nested required tests, function-level skip, and module-level xfail.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297552753 -> ca589415a
Disposition: FIXED
Commit: ca589415a
Evidence: `_module_class_nodes(...)` restricts `RAGDegradedReason` proof to module-scope classes; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_nested_enum_marker_spoof` covers nested class spoofing.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297552755 -> ca589415a
Disposition: FIXED
Commit: ca589415a
Evidence: standalone `closed` is no longer a generic negation token; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_closed_token_runtime_expansion_bypass` covers the false-negative path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#pullrequestreview-4355977247 -> ca589415a
Disposition: FIXED
Commit: ca589415a
Evidence: aggregate Codex review actionables are mapped to the four inline FIXED comments above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297688482 -> b65d30c3e
Disposition: FIXED
Commit: b65d30c3e
Evidence: `_has_disabled_test_collection(...)` now rejects `__test__ = False`; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_module_dunder_test_false_for_required_tests` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297688488 -> b65d30c3e
Disposition: FIXED
Commit: b65d30c3e
Evidence: `_iter_scope_statements(...)` and `_assigned_value(...)` now inspect conditional and annotated `pytestmark`; regression tests cover annotated and conditional module disables.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297688494 -> b65d30c3e
Disposition: FIXED
Commit: b65d30c3e
Evidence: `historical` was removed from the generic negation regex; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_historical_token_runtime_expansion_bypass` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297688497 -> db19fb52b
Disposition: FIXED
Commit: db19fb52b
Evidence: call-keyword proof is scoped to target functions and actual `asyncio.to_thread` targets; regression tests reject dead-helper call spoofing.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297688500 -> b65d30c3e
Disposition: FIXED
Commit: b65d30c3e
Evidence: `_disabling_marker_aliases(...)` resolves alias-bound skip/xfail decorators; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_alias_bound_skipped_required_test` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297688507 -> b65d30c3e
Disposition: FIXED
Commit: b65d30c3e
Evidence: `_module_level_skip_call(...)` now rejects `pytest.skip(..., allow_module_level=True)`; the module-level skip regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297688512 -> b65d30c3e
Disposition: FIXED
Commit: b65d30c3e
Evidence: `_class_has_uncollectable_constructor(...)` rejects required tests inside non-collectable `Test*` classes; the uncollectable class regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#pullrequestreview-4356131280 -> db19fb52b
Disposition: FIXED
Commit: db19fb52b
Evidence: aggregate Codex review actionables from the `1e1a05228f` review are mapped to the seven inline FIXED comments above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297730632 -> db19fb52b
Disposition: FIXED
Commit: db19fb52b
Evidence: `_name_rebound_after_definition(...)` rejects required test rebinding after collection-visible definitions; the required-test rebound regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297730636 -> db19fb52b
Disposition: FIXED
Commit: db19fb52b
Evidence: runtime class/function proof now rejects module-level rebinding after required definitions; the runtime-symbol rebound regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297730641 -> db19fb52b
Disposition: FIXED
Commit: db19fb52b
Evidence: subject_id propagation proof is bound to `_run_orchestration` retrieval calls and `_build_knowledge_candidates`; dead-helper subject_id spoofing is rejected.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297730646 -> db19fb52b
Disposition: FIXED
Commit: db19fb52b
Evidence: degraded-reason AST proof is scoped to `_run_orchestration` and `_retrieve_vector_from_db`; out-of-target dead-helper references are rejected.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297730650 -> db19fb52b
Disposition: FIXED
Commit: db19fb52b
Evidence: required-test validation now rejects in-body `pytest.skip` and `pytest.xfail` calls; the in-test skip regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297730655 -> db19fb52b
Disposition: FIXED
Commit: db19fb52b
Evidence: local-path leakage detection now catches punctuation-prefixed `worktrees/` and `artifacts/orchestration`; the punctuation-prefixed worktree regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#pullrequestreview-4356178979 -> db19fb52b
Disposition: FIXED
Commit: db19fb52b
Evidence: aggregate Codex review actionables from the `bf982c7d1d` review are mapped to the six inline FIXED comments above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297874930 -> f802efe2c
Disposition: FIXED
Commit: f802efe2c
Evidence: `_iter_scope_statements(...)` is now used by rebinding checks and walks nested executable blocks; the nested runtime-symbol rebound regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297874934 -> f802efe2c
Disposition: FIXED
Commit: f802efe2c
Evidence: the scope walker descends into `if`, loops, try/except/finally, with, and match blocks; the try-block pytestmark regression covers non-`if` disables.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297874939 -> f802efe2c
Disposition: FIXED
Commit: f802efe2c
Evidence: `_imported_disabling_call_aliases(...)` and `_module_level_skip_call(...)` detect imported and assigned skip aliases; the imported-alias module skip regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297874942 -> f802efe2c
Disposition: FIXED
Commit: f802efe2c
Evidence: call-proof extraction now preserves exact callee identity instead of dropping namespaces; the similar-method call spoof regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297874948 -> f802efe2c
Disposition: FIXED
Commit: f802efe2c
Evidence: `_assigned_names(...)` now treats `import` and `from ... import ...` bindings as rebinding evidence; the import-rebinding regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297874955 -> f802efe2c
Disposition: FIXED
Commit: f802efe2c
Evidence: `_function_test_attribute_disabled_after_definition(...)` rejects falsy function `.__test__` overrides after required test definitions; the post-definition `__test__` override regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297874957 -> f802efe2c
Disposition: FIXED
Commit: f802efe2c
Evidence: `_is_falsy_constant(...)` now treats falsey `__test__` constants as disabling, not just literal `False`; the module `__test__ = 0` regression covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3297874959 -> f802efe2c
Disposition: FIXED
Commit: f802efe2c
Evidence: `_truthy_constant_aliases(...)` resolves simple true aliases for `allow_module_level`; the imported-alias module skip regression covers non-literal truthy allow-module-level.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#pullrequestreview-4356337666 -> f802efe2c
Disposition: FIXED
Commit: f802efe2c
Evidence: aggregate Codex review actionables from the `6ef16db12e` review are mapped to the eight inline FIXED comments above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024837 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_bound_target_names(...)` and `_assigned_names(...)` now inspect tuple/list/starred targets; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_destructuring_runtime_symbol_rebound` covers destructuring rebinding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024840 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_has_disabled_test_collection(...)` now walks statement ASTs for module-level skip calls; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_assignment_wrapped_module_level_skip` covers assignment-wrapped collection disable.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024845 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_function_body_has_disabling_test_call(...)` now includes function-local disabling aliases; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_function_local_skip_alias` covers local `pytest.skip` aliasing.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024849 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_assigned_names(...)` now records wildcard imports as a fail-closed rebinding sentinel; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_wildcard_import_runtime_symbol_rebound` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024851 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_pytest_module_aliases(...)` resolves `import pytest as ...`; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_import_pytest_as_alias_module_level_skip` covers module-level skip through an alias.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024855 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_class_method_rebound_after_class_definition(...)` and `_class_method_test_attribute_disabled_after_class_definition(...)` reject module-scope class-method mutation; class-method rebinding and `.__test__` override regressions cover this path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024858 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_module_level_skip_call(...)` now treats `pytest.xfail(..., allow_module_level=True)` as collection-disabling; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_module_level_pytest_xfail` covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024863 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_assigned_names(...)` now inspects `ast.NamedExpr` targets; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_namedexpr_runtime_symbol_rebound` covers assignment-expression rebinding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024867 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_node_has_disabling_test_marker(...)` now resolves subscripted decorator aliases; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_computed_decorator_alias` covers `DISABLE[0]`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024870 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_call_allows_module_level(...)` and `_mapping_has_truthy_allow_module_level(...)` inspect `**{...}` expansions; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_kwargs_expanded_allow_module_level` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298024875 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: `_check_overclaims(...)` now splits soft conjunctions such as `and`; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_overclaim_after_conjunction_negation` covers negation-masked overclaims.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#pullrequestreview-4356511330 -> 9e96f799d
Disposition: FIXED
Commit: 9e96f799d
Evidence: aggregate Codex review actionables from the `d773c0f7d` review are mapped to the eleven inline FIXED comments above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298170259 -> afc897fc2
Disposition: FIXED
Commit: afc897fc2
Evidence: `_static_truthiness(...)` and `_is_truthy_or_unknown(...)` now detect computed truthy `allow_module_level`; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_computed_truthy_allow_module_level` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298170265 -> afc897fc2
Disposition: FIXED
Commit: afc897fc2
Evidence: `__test__` disabling checks now use deterministic static truthiness and fail closed on unknown values; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_computed_falsy_dunder_test_values` covers module and function override variants.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298170271 -> afc897fc2
Disposition: FIXED
Commit: afc897fc2
Evidence: `_truthy_allow_module_level_mapping_aliases(...)` resolves kwargs mapping aliases before module-level skip checks; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_kwargs_alias_allow_module_level` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298170273 -> afc897fc2
Disposition: FIXED
Commit: afc897fc2
Evidence: `_node_has_disabling_test_marker(...)` now treats subscripted tuple/list marker expressions as disabling aliases; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_subscripted_decorator_alias_assignment` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298170277 -> afc897fc2
Disposition: FIXED
Commit: afc897fc2
Evidence: `_slice(...)` now rejects duplicate closeout anchors before section validation; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_duplicate_closeout_anchor` covers decoy-anchor spoofing.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298170282 -> afc897fc2
Disposition: FIXED
Commit: afc897fc2
Evidence: `_callable_name(...)` resolves `getattr(pytest, "skip"/"xfail")` calls; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_getattr_based_test_skip` covers module-level and in-test variants.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298170288 -> afc897fc2
Disposition: FIXED
Commit: afc897fc2
Evidence: `_reachable_nodes_in_function(...)` excludes statements after `return` and constant-false branches from runtime proof checks; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_unreachable_runtime_proof_after_return` covers unreachable call/reference proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298170291 -> afc897fc2
Disposition: FIXED
Commit: afc897fc2
Evidence: `blocked` and `deferred` were removed as blanket negation tokens; stale blocked wording and deferred overclaim regressions cover the false-negative paths.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#discussion_r3298170294 -> afc897fc2
Disposition: FIXED
Commit: afc897fc2
Evidence: `LOCAL_PATH_RE` is now case-insensitive; `tests/test_ai_rag_hardening_a2_closeout.py::test_checker_rejects_capitalized_worktrees_leakage` covers the bypass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#pullrequestreview-4356675240 -> afc897fc2
Disposition: FIXED
Commit: afc897fc2
Evidence: aggregate Codex review actionables from the `7ec4728c5` review are mapped to the nine inline FIXED comments above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#issuecomment-4533488800
Disposition: NOT-A-BUG
Reason: CodeRabbit reported a review-capacity/rate-limit notice, not a code, docs, test, or security finding.
Evidence: comment body says review limit/usage credits were exhausted.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1827#pullrequestreview-4355948535
Disposition: NOT-A-BUG
Reason: Sourcery reported a weekly diff-character rate-limit notice, not a code, docs, test, or security finding.
Evidence: review body asks to retry later or upgrade due rate limit.

## Merge Readiness

Not merge-ready yet. Required before merge: current-head CI, post-open
bootstrap, QA/bug-hunter/security-auditor pass, Codex Security
threat-model/security-scan/validation, CodeRabbit/Sourcery/Cubic no-actionables
or dispositions, strict review-thread disposition, merge-readiness wrapper with
auth, and final wait-window.
