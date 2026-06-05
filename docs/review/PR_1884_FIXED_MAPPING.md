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
- No review threads have been resolved.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#pullrequestreview-4432302250 -> ee8b58d65
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1884#discussion_r3359533605 -> ee8b58d65
Disposition: FIXED
Commit: ee8b58d65
Evidence: cubic identified that the canonical fixed-mapping artifact used the PR-body mirror heading level. `docs/review/PR_1884_FIXED_MAPPING.md` now uses `## Fixed in Commit Mapping`, the canonical artifact heading.

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
- [ ] `security-auditor` - pending.
- [ ] Codex Security diff scan / finding discovery - pending.
- [ ] `pulseplate-pr-review` - pending.

## Advisory / Bot Dispositions

- Disposition: FIXED
  Evidence: bug-hunter found `github_pat_` token inputs were hashed before redaction; `ee8b58d65` adds `github_pat_` to the redaction token pattern and asserts the provenance digest no longer equals the raw-token digest.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-b5dc301d9990.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution kind: `oracle_review`
- `mutated_paths`: `[]`
- `shared_tree_untouched`: `true`
- `coauthor_required`: `true`
- Co-author trailer was applied to the commit materially shaped by the
  oracle-only Experiment Runner review.

## Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --path core/verification/contracts.py --path core/verification/registry.py --path core/verification/__init__.py --path core/rag/orchestration.py --path core/insight/philosophical_runtime.py --path app/services/insight_application_service.py --path tests/test_remaining_modules.py --path tests/test_rag_orchestration.py --path tests/test_philosophical_runtime.py --path tests/test_insight_application_service.py --path docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- PASS: `.venv/bin/python -m pytest -q tests/test_remaining_modules.py::TestVerificationRegistryCoverageTail tests/test_rag_orchestration.py tests/test_philosophical_runtime.py tests/test_insight_application_service.py tests/test_knowledge_promotion.py`
- PASS: `python3 scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- PASS: `PATH="$REPO_ROOT/.venv/bin:$PATH" make openapi-check`
- PASS: `git diff --exit-code origin/main...HEAD -- frontend ios providers alembic app/static/openapi.json frontend/src/api/openapi.json frontend/src/api/schema.ts`
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_remaining_modules.py::TestVerificationRegistryCoverageTail`
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
- Current-head CI, bot review state, final discussion-thread pass, post-open
  role review, Codex Security diff scan / finding discovery,
  `pulseplate-pr-review`, strict disposition checks, strict merge-readiness
  checks, and wait-window remain pending.
