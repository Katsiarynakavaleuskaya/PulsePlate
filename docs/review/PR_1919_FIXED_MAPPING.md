# PR 1919 Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open review-thread pass completed.

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#pullrequestreview-4458554006
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-semantic-cache-cost-provenance-train
Evidence: docs/roadmap/BACKLOG_LEDGER.md
Reason: Sourcery review-level helper centralization feedback is valid but would widen PR-O1 beyond the metadata-only scaffold; individual actionable Sourcery comments are fixed below, while shared-helper extraction is deferred to the PR-O2 context-compression cleanup evaluation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#pullrequestreview-4458568992 -> 668ad1eda
Disposition: FIXED
Commit: 668ad1eda
Evidence: docs/orchestration/contracts/SEMANTIC_CACHE_COST_PROVENANCE_TELEMETRY.md; docs/orchestration/contracts/SEMANTIC_CACHE_COST_PROVENANCE_TELEMETRY.schema.json; tests/test_semantic_cache_cost_provenance_telemetry_contract.py
Reason: CodeRabbit review-level doc/schema feedback is addressed by adding explicit `blocked_policy_decisions` schema coverage and clarifying the payload/backend/policy-decision split in the contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#pullrequestreview-4460878053 -> 3f34a7f5f
Disposition: FIXED
Commit: 3f34a7f5f
Evidence: core/ai/prompt_modules.py; tests/core/ai/test_prompt_modules.py::test_prompt_module_registry_derives_id_for_public_constructor
Reason: Public `PromptModuleRegistry(...)` construction now derives `registry_id` from the normalized policy version and sorted prompt-module records instead of trusting caller-supplied identity.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#pullrequestreview-4460998465 -> bca7e9d1f
Disposition: FIXED
Commit: bca7e9d1f
Evidence: core/ai/prompt_modules.py; tests/core/ai/test_prompt_modules.py::test_prompt_module_metadata_rejects_unsafe_nested_values
Reason: Cubic found that colon-delimited `file://` path markers were missed; `_PATH_RE` now allows colon as a boundary only for `file://`, preserving `profile://safe-label` while rejecting `see:file:///tmp/raw.txt`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3382637044 -> bca7e9d1f
Disposition: FIXED
Commit: bca7e9d1f
Evidence: core/ai/prompt_modules.py; tests/core/ai/test_prompt_modules.py::test_prompt_module_metadata_rejects_unsafe_nested_values
Reason: Cubic found that colon-delimited `file://` path markers were missed; `_PATH_RE` now allows colon as a boundary only for `file://`, preserving `profile://safe-label` while rejecting `see:file:///tmp/raw.txt`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3380610588 -> 5cb59be3d
Disposition: FIXED
Commit: 5cb59be3d
Evidence: core/ai/prompt_modules.py; tests/core/ai/test_prompt_modules.py
Reason: Removed unsupported `float` from the prompt-module `JsonScalar` alias so the type contract matches runtime metadata validation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3380610597 -> 5cb59be3d
Disposition: FIXED
Commit: 5cb59be3d
Evidence: core/evidence/fingerprints.py; tests/core/evidence/test_fingerprints.py::test_provenance_envelope_fingerprint_dedupes_repeated_fingerprints
Reason: Provenance envelope source and prompt-module fingerprint sequences are canonicalized as sets before hashing.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3380623541 -> 5cb59be3d
Disposition: FIXED
Commit: 5cb59be3d
Evidence: core/ai/prompt_modules.py; tests/core/ai/test_prompt_modules.py
Reason: Prompt-module metadata intentionally excludes float values; the public `JsonScalar` alias now matches that runtime contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3380623548 -> 160b10d52
Disposition: FIXED
Commit: 160b10d52
Evidence: docs/orchestration/contracts/SEMANTIC_CACHE_COST_PROVENANCE_TELEMETRY.md
Reason: Contract prose now uses the same plural token field names as the JSON schema.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3380628001 -> 160b10d52
Disposition: FIXED
Commit: 160b10d52
Evidence: core/ai/prompt_modules.py; tests/core/ai/test_prompt_modules.py::test_prompt_module_record_allows_safe_prompt_label_ids
Reason: Token validation now permits safe prompt-module labels such as `system-prompt` while preserving raw-payload and secret/path guards.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3380628003 -> 160b10d52
Disposition: FIXED
Commit: 160b10d52
Evidence: core/ai/cache_observability.py; tests/core/ai/test_cache_observability.py::test_token_economy_estimate_hashes_normalized_reason_codes
Reason: Token-economy IDs are now hashed from normalized safe labels, integer estimate fields, and normalized reason codes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3380628010 -> 160b10d52
Disposition: FIXED
Commit: 160b10d52
Evidence: core/ai/prompt_modules.py; tests/core/ai/test_prompt_modules.py::test_prompt_module_registry_hashes_normalized_policy_version
Reason: Prompt-module registry IDs are now hashed from the normalized registry policy version.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3380628018 -> 160b10d52
Disposition: FIXED
Commit: 160b10d52
Evidence: core/ai/prompt_modules.py; tests/core/ai/test_prompt_modules.py::test_prompt_module_metadata_rejects_unsafe_nested_values
Reason: Prompt-module metadata path detection now catches punctuation-wrapped local paths such as `see(/Users/alice/raw.txt)`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3380730890 -> 074f4ce99
Disposition: FIXED
Commit: 074f4ce99
Evidence: core/ai/prompt_modules.py; tests/core/ai/test_prompt_modules.py::test_prompt_module_metadata_allows_non_path_url_like_labels
Reason: `file://` is now kept under the same boundary-prefix path check as other local path forms, avoiding false positives such as `profile://safe-label`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1919#discussion_r3380750594 -> 074f4ce99
Disposition: FIXED
Commit: 074f4ce99
Evidence: core/ai/prompt_modules.py; tests/core/ai/test_prompt_modules.py::test_prompt_module_metadata_is_deep_frozen_after_validation
Reason: Prompt-module metadata now recursively freezes nested mappings and lists after validation.

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/14f1a384b89b.json`
Starter: `scripts/orchestration/start_pr_lane.sh`

## Role Dispatch Evidence
- Task packet: `artifacts/orchestration/task_packets/14f1a384b89b.json`.
- Dispatch manifest: `python scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/14f1a384b89b.json --mode runtime --implementation-owner security-auditor --pretty`.
- Required pre-open role order executed: `agent-coordinator -> rag-systems-agent -> prompt-engineering-eval-agent -> architecture-specialist -> security-auditor -> qa-engineer-agent -> ai-innovation-specialist`.
- Mandatory post-open order executed: `qa-engineer-agent -> bug-hunter -> security-auditor`, then Codex Security diff/finding discovery and `pulseplate-pr-review`.

## Post-Open Role Finding Closure
- Bug-hunter P1 `TokenEconomyEstimate.metadata` shallow-freeze issue: FIXED in commit `5b279d9ad`.
Evidence: `core/ai/cache_observability.py`; `tests/core/ai/test_cache_observability.py::test_token_economy_estimate_metadata_is_deep_frozen_after_validation`.
Reason: Cache observability metadata now deep-freezes nested mappings and lists after validation, while `to_stable_mapping(...)` remains JSON-ready through safe copy conversion.
- Security-auditor P1 cache-observability path-boundary issue: FIXED in commit `79d891365`.
Evidence: `core/ai/cache_observability.py`; `core/ai/prompt_modules.py`; `tests/core/ai/test_cache_observability.py::test_token_economy_estimate_fails_closed_for_unsafe_inputs`; `tests/core/ai/test_prompt_modules.py::test_prompt_module_metadata_rejects_unsafe_nested_values`.
Reason: Cache observability and prompt-module metadata guards now share the same local-path boundary behavior, rejecting `see(/Users/...)`, `see:/Users/...`, and `see:file://...` while preserving safe URI-like labels such as `profile://safe-label`.
- Codex Security diff/finding discovery: NOT-A-BUG / no reportable findings on commit `4d8b083b4`.
Evidence: `/tmp/codex-security-scans/semantic-cache-cost-provenance-o1/4d8b083b4159_20260609T174700Z/report.md`; work ledger reviewed diff-scoped `core/ai/cache_observability.py`, `core/ai/prompt_modules.py`, and `core/evidence/fingerprints.py` with zero reportable findings.
Reason: Generated non-diff rows for semantic-cache admission harness files were closed as not applicable and are outside this branch diff.
- `pulseplate-pr-review` large-diff-risk advisory: NOT-A-BUG for PR #1919 scope.
Evidence: `/tmp/pulseplate_pr_review_context_1919.json`; `python scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr_review_context_1919.json --format markdown`; `make validate-changed` PASS.
Reason: The diff is intentionally one PR-O1 scaffold covering the deterministic provenance envelope, prompt-module fingerprint registry, token/cost telemetry contract, docs schema, ledger anchor, and focused tests; runtime serving and PR-O2 compression remain explicitly out of scope.
- Current-head CI `diff-coverage` failure on commit `739b4f912`: FIXED in commit `0e1e3de92`.
Evidence: `tests/core/ai/test_cache_observability.py`; `tests/core/ai/test_prompt_modules.py`; `tests/core/evidence/test_fingerprints.py`; local `diff-cover coverage.xml --compare-branch=origin/main --fail-under=97 ...` PASS with `core/ai/cache_observability.py (100%)`, `core/ai/prompt_modules.py (100%)`, `core/evidence/fingerprints.py (100%)`, total `100%`.
Reason: CI `test-pr` builds the coverage artifact from selected route-contract suites; the prompt-module contract tests were not visible to that selected suite, so a test-layer bridge now executes the existing prompt-module contract coverage from `tests/core/ai/test_cache_observability.py` without widening production or workflow scope.

## Premortem Finding Closure
- P1 token economy estimate IDs could collide for materially different estimates: FIXED in commit `81c2e5966d7a`.
Evidence: `core/ai/cache_observability.py`; `tests/core/ai/test_cache_observability.py::test_token_economy_estimate_identity_includes_material_estimate_fields`.
- P1 provenance envelope hashing accepted malformed fingerprints and raw-looking values: FIXED in commit `81c2e5966d7a`.
Evidence: `core/evidence/fingerprints.py`; `tests/core/evidence/test_fingerprints.py::test_provenance_envelope_fails_closed_for_raw_or_malformed_inputs`.

## Experiment Runner Evidence
- Artifact: `artifacts/orchestration/experiments/results/exp-064ad7a5805e.json`
- Mode: `oracle_only_governance_reviewer`.
- Status: `accepted`.
- Shared tree untouched: `true`.
- Mutated paths: `[]`.
- Co-author trailer used in commit `81c2e5966d7a`: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Validation Evidence
- `python -m pytest -q tests/core/evidence/test_fingerprints.py tests/core/ai/test_cache_observability.py tests/core/ai/test_prompt_modules.py tests/test_semantic_cache_cost_provenance_telemetry_contract.py tests/test_semantic_cache_observability_contract.py tests/test_semantic_cache_gate.py tests/test_docs_phase1_gates.py tests/test_ai_runtime_semantic_cache_handoff.py` PASS.
- `python -m mypy core/evidence/fingerprints.py core/ai/cache_observability.py core/ai/prompt_modules.py` PASS.
- `python scripts/ci/check_semantic_cache_gate.py` PASS.
- `python scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md docs/orchestration/contracts/SEMANTIC_CACHE_COST_PROVENANCE_TELEMETRY.md` PASS.
- `make validate-changed` PASS after commit `81c2e5966d7a`.
- `pre-commit run --all-files` PASS.
- `git diff --cached --check` PASS before commit.
- Pre-push hooks PASS: changed-file mypy, backend tests, full Bandit, Docker build test.
- `python -m pytest -q tests/core/evidence/test_fingerprints.py tests/core/ai/test_prompt_modules.py tests/core/ai/test_cache_observability.py tests/test_semantic_cache_cost_provenance_telemetry_contract.py` PASS after bot-fix commits.
- `python -m mypy core/evidence/fingerprints.py core/ai/cache_observability.py core/ai/prompt_modules.py` PASS after bot-fix commits.
- `python scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md docs/orchestration/contracts/SEMANTIC_CACHE_COST_PROVENANCE_TELEMETRY.md` PASS after bot-fix commits.
- `python -m pytest -q tests/core/evidence/test_fingerprints.py tests/core/ai/test_cache_observability.py tests/core/ai/test_prompt_modules.py tests/test_semantic_cache_cost_provenance_telemetry_contract.py tests/test_semantic_cache_observability_contract.py tests/test_semantic_cache_gate.py tests/test_docs_phase1_gates.py tests/test_ai_runtime_semantic_cache_handoff.py` PASS after commit `074f4ce99`.
- `python scripts/ci/check_docs_phase1_gates.py --files $(git diff --name-only origin/main...HEAD)` PASS after commit `074f4ce99`.
- Local diff coverage PASS after commit `074f4ce99`: `core/ai/cache_observability.py (100%)`, `core/ai/prompt_modules.py (99.2%)`, `core/evidence/fingerprints.py (100%)`, total `99%`.
- `make validate-changed` PASS after `pulseplate-pr-review` large-diff advisory.
- `python -m pytest -q tests/core/ai/test_cache_observability.py tests/core/ai/test_prompt_modules.py tests/core/evidence/test_fingerprints.py tests/test_semantic_cache_cost_provenance_telemetry_contract.py` PASS after commit `0e1e3de92`.
- `python -m coverage run -m pytest -q tests/core/ai/test_cache_observability.py tests/core/evidence && python -m coverage xml && diff-cover coverage.xml --compare-branch=origin/main --fail-under=97 ...` PASS after commit `0e1e3de92`: all PR-touched source files at `100%` diff coverage.
- `make validate-changed` PASS after commit `0e1e3de92`.
- `pre-commit run --all-files` PASS after commit `0e1e3de92`.

## Known Non-Ready Gate
- `make verify` FAILS at repo-wide `make typecheck` on files outside this PR diff.
Evidence: `core/ai/semantic_cache_offline_admission_runner.py:294`, `core/ai/semantic_cache_offline_admission_runner.py:480`, `core/ai/semantic_cache_offline_admission_runner.py:545-550`, `core/ai/semantic_cache_offline_admission_runner.py:676`, `core/ai/semantic_cache_offline_admission_runner.py:681`, `core/ai/semantic_cache_offline_admission_runner.py:683-684`, and `core/ai/semantic_cache_shadow_admission_harness.py:495`.
Disposition: NOT-A-BUG for PR #1919 scope; these files are not changed by this branch and this PR does not claim merge readiness until current-head CI/review governance is resolved.
