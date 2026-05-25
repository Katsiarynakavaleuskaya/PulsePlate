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
- PASS: `python -m pytest -q tests/test_ai_rag_hardening_a2_closeout.py tests/test_rag_orchestration.py tests/test_vector_rag.py tests/test_insight_rag_response_fields.py tests/test_semantic_cache_gate.py tests/test_repo_policy_guards.py` (`60 passed`)
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
- Local scan id: `pr1827_1e1a05228fb7_20260525T104758Z`
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
