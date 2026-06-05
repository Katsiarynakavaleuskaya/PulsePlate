# PR 1884 Fixed in Commit Mapping

## Scope

This PR adds internal-only provenance attestation metadata to the existing
`VerificationBundle`. It records redacted digest/count metadata for verification
inputs without changing public API contracts, provider selection, DB schemas,
frontend, iOS, Slack/operator-plane authority, semantic cache, or GraphRAG.

## Lane Start Provenance

- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/verification-bundle-provenance-v1`
- Base: `origin/main` at `5f03b0ed59379ce34e6ca018c9822167c3b615f0`
- Packet: `artifacts/orchestration/task_packets/a47f9f3bad1e.json`
- Role dispatch:
  `scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/a47f9f3bad1e.json --mode runtime --implementation-owner security-auditor --implementation-owner backend-engineer --pretty`
- Required role order completed before implementation:
  `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> backend-engineer`
- Main health before start: `CI` run `26982624382` completed `success` on
  `5f03b0ed59379ce34e6ca018c9822167c3b615f0`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Resolved review threads are tracked below with disposition evidence.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#pullrequestreview-4432302250 -> ee8b58d65
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3359533605 -> ee8b58d65
Disposition: FIXED
Commit: ee8b58d65
Evidence: cubic identified that the canonical fixed-mapping artifact used the PR-body mirror heading level. `docs/review/PR_1884_FIXED_MAPPING.md` now uses `## Fixed in Commit Mapping`, the canonical artifact heading.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3361468672 -> 3a738e078faaa4f8458d1fa034a809c6a3f93efc
Disposition: FIXED
Commit: 3a738e078faaa4f8458d1fa034a809c6a3f93efc
Evidence: `docs/review/PR_1884_FIXED_MAPPING.md` now states that resolved review threads are tracked below with disposition evidence instead of claiming no threads were resolved.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3361491362 -> 3a738e078faaa4f8458d1fa034a809c6a3f93efc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3361498490 -> 3a738e078faaa4f8458d1fa034a809c6a3f93efc
Disposition: FIXED
Commit: 3a738e078faaa4f8458d1fa034a809c6a3f93efc
Evidence: `docs/review/PR_1884_FIXED_MAPPING.md` now records the `security-auditor` gate as completed after the exact local-path guard passed, removing the completed-vs-pending contradiction.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3359557877 -> 202eb70436653b2fc83f5bb107f9eb843839f481
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3359570145 -> 202eb70436653b2fc83f5bb107f9eb843839f481
Disposition: FIXED
Commit: 202eb70436653b2fc83f5bb107f9eb843839f481
Evidence: `docs/review/PR_1884_FIXED_MAPPING.md` now identifies `c3bd36235` as the Experiment Runner-shaped commit with the required `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer, instead of relying on an old review-merge commit reference.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3361451889 -> 202eb70436653b2fc83f5bb107f9eb843839f481
Disposition: FIXED
Commit: 202eb70436653b2fc83f5bb107f9eb843839f481
Evidence: `core/verification/registry.py` now returns the existing `rag_bundle` before constructing provenance-only `rag_bundle_missing` failures when `runtime_verification_enabled=False`, with regression coverage in `tests/test_remaining_modules.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3361468682 -> 202eb70436653b2fc83f5bb107f9eb843839f481
Disposition: FIXED
Commit: 202eb70436653b2fc83f5bb107f9eb843839f481
Evidence: `docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md` now cites PR `#1884`, implementation file:line references, the backlog ledger entry, and this review artifact for the internal-only provenance and public-response-boundary claims.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3361572631
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor ee8b58d65 HEAD`, `git merge-base --is-ancestor 3a738e078faaa4f8458d1fa034a809c6a3f93efc HEAD`, and `git merge-base --is-ancestor 202eb70436653b2fc83f5bb107f9eb843839f481 HEAD` all succeeded locally on the checked PR branch lineage.
Reason: The cited mappings are reachable on the current PR branch; the review comment compared against a stale reviewed head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3361572634 -> 17802c24cac855f405e84ac5b704d01efc4537c5
Disposition: FIXED
Commit: 17802c24cac855f405e84ac5b704d01efc4537c5
Evidence: `_LOCAL_PATH_RE` now redacts Linux CI/container roots such as `/workspace` and `/app` before hashing, with regression coverage in `tests/test_remaining_modules.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3361572636 -> 17802c24cac855f405e84ac5b704d01efc4537c5
Disposition: FIXED
Commit: 17802c24cac855f405e84ac5b704d01efc4537c5
Evidence: `_SECRET_ASSIGNMENT_RE` now redacts common secret/env assignment names before hashing, with regression coverage for `DATABASE_URL`, `SERVER_SALT`, and `SECRET_KEY` inputs.

## Premortem Findings

- Disposition: FIXED
  Evidence: provenance is optional internal metadata and tests assert admission
  fields plus disabled-runtime passthrough are unchanged.
- Disposition: FIXED
  Evidence: digest helpers redact before hashing; tests assert no raw
  prompt/context/answer/token/path/Slack-like identifiers leak through
  provenance serialization.
- Disposition: FIXED
  Evidence: `test_execute_insight_request_hands_internal_candidates_to_store_without_payload_drift`
  asserts public response output does not expose `verification_bundle`,
  `provenance`, or digest/count fields.
- Disposition: FIXED
  Evidence: semantic-cache gate check passes and docs keep semantic cache
  closed/out of scope.

## Post-Open Review Gates

- [x] `qa-engineer-agent` - completed; no findings. It reran scoped preflight, focused provenance/public-response pytest, semantic-cache gate, `git diff --check`, and `make validate-changed`.
- [x] `bug-hunter` - completed; found `github_pat_` token inputs were hashed before redaction. Fixed by `ee8b58d65` in `core/verification/registry.py`, with regression coverage in `tests/test_remaining_modules.py`.
- [x] `security-auditor` - completed; found a machine-local absolute path in committed review evidence. Fixed by replacing it with `$REPO_ROOT/.venv/bin/python`; the exact local-path guard passed after the artifact cleanup.
- [x] Codex Security diff scan / finding discovery - completed; no reportable findings after the bug-hunter and security-auditor remediations. Local report format validation and HTML rendering passed.
- [x] `pulseplate-pr-review` - completed in report mode. The large-diff planning note is dispositioned as NOT-A-BUG because this is one coherent internal provenance slice and changed-surface gates passed.

## Advisory / Bot Dispositions

- Disposition: FIXED
  Evidence: bug-hunter found `github_pat_` token inputs were hashed before redaction; `ee8b58d65` adds `github_pat_` to the redaction token pattern and asserts the provenance digest no longer equals the raw-token digest.
- Disposition: FIXED
  Evidence: security-auditor found a machine-local absolute path in review evidence; `docs/review/PR_1884_FIXED_MAPPING.md` now records `$REPO_ROOT/.venv/bin/python` instead of a user-specific `/Users/...` path.
- Disposition: NOT-A-BUG
  Evidence: `pulseplate-pr-review` reported a large-diff planning note because the branch exceeds the advisory line threshold. This PR intentionally keeps one narrow verification-bundle provenance slice across the contract, registry, RAG orchestration, philosophical runtime, deterministic tests, and backlog wording. Focused pytest, semantic-cache gate, OpenAPI drift check, `make validate-changed`, `pre-commit run --all-files`, and local diff-cover passed.
  Reason: Splitting the slice would separate the internal `VerificationBundle` contract from the runtime paths and tests that prove it does not leak into public responses.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-b5dc301d9990.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution kind: `oracle_review`
- `mutated_paths`: `[]`
- `shared_tree_untouched`: `true`
- `coauthor_required`: `true`
- Co-author trailer is present on `c3bd36235`, the commit materially shaped by
  the oracle-only Experiment Runner review.

## Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --path core/verification/contracts.py --path core/verification/registry.py --path core/verification/__init__.py --path core/rag/orchestration.py --path core/insight/philosophical_runtime.py --path app/services/insight_application_service.py --path tests/test_remaining_modules.py --path tests/test_rag_orchestration.py --path tests/test_philosophical_runtime.py --path tests/test_insight_application_service.py --path docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- PASS: `.venv/bin/python -m pytest -q tests/test_remaining_modules.py::TestVerificationRegistryCoverageTail tests/test_rag_orchestration.py tests/test_philosophical_runtime.py tests/test_insight_application_service.py tests/test_knowledge_promotion.py`
- PASS: `python3 scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- PASS: `PATH="$REPO_ROOT/.venv/bin:$PATH" make openapi-check`
- PASS: `git diff --exit-code origin/main...HEAD -- frontend ios providers alembic app/static/openapi.json frontend/src/api/openapi.json frontend/src/api/schema.ts`
- PASS: `$REPO_ROOT/.venv/bin/python -m pytest -q tests/test_remaining_modules.py::TestVerificationRegistryCoverageTail`
- PASS: `git log -1 --format=%B c3bd36235 | rg "Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>"`
- PASS: `git merge-base --is-ancestor ee8b58d65 HEAD && git merge-base --is-ancestor 3a738e078faaa4f8458d1fa034a809c6a3f93efc HEAD && git merge-base --is-ancestor 202eb70436653b2fc83f5bb107f9eb843839f481 HEAD`
- PASS: `$REPO_ROOT/.venv/bin/python -m pytest -q tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths` after artifact path redaction.
- PASS: `python3 $CODEX_SECURITY_PLUGIN_ROOT/scripts/validate_report_format.py --report-md artifacts/security_lab/codex-security/pr1884-verification-provenance/report.md`
- PASS: `python3 $CODEX_SECURITY_PLUGIN_ROOT/scripts/render_report_html.py --template $CODEX_SECURITY_PLUGIN_ROOT/assets/report_template_inlined.html --report-md artifacts/security_lab/codex-security/pr1884-verification-provenance/report.md --report-html artifacts/security_lab/codex-security/pr1884-verification-provenance/report.html --title "PulsePlate PR 1884 Codex Security Scan"`
- PASS: `$REPO_ROOT/.venv/bin/python -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q`
- PASS: focused local diff-cover check on provenance/runtime tests reached 98% diff coverage against `origin/main`.
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks during `git push`
- Not required for this operator-directed lane: full `make verify`. This PR
  uses the changed-surface gate plus focused runtime/provenance tests.

## Semantic Gate Recheck

- PASS: `python3 scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- Markers remain `closed / false / false / true`.
- This is a closed-gate assertion only, not semantic-cache activation.

## Merge Readiness

- Not claimed.
- Current-head CI, bot review state, final discussion-thread pass, strict
  disposition checks, strict merge-readiness checks, and wait-window remain
  pending.
