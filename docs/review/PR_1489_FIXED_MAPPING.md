# PR #1489 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is the source of truth for review dispositions on PR #1489.
Record every actionable human or bot review item here before resolving threads or
claiming merge readiness.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1489_FIXED_MAPPING.md`
Reason: The Sourcery review shell summarizes two inline actionable findings that are fixed below plus high-level deduplication suggestions that are advisory only for this narrow companion bootstrap lane.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#pullrequestreview-4150576866

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#pullrequestreview-4150583465`
Reason: The Codex connector review is only the integration shell notice and does not add separate inline actionables on top of the findings dispositioned elsewhere in this artifact.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#pullrequestreview-4150583465

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1489_FIXED_MAPPING.md`
Reason: This CodeRabbit review shell aggregates inline findings that are dispositioned individually below; once those comment URLs are mapped, the shell entry adds no separate unresolved obligation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#pullrequestreview-4150602793

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1489_FIXED_MAPPING.md`
Reason: This follow-up CodeRabbit review shell contains a single minor inline finding that is fixed immediately below; the shell entry itself adds no separate unresolved obligation after the inline comment is dispositioned.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#pullrequestreview-4150726499

Disposition: FIXED
Commit: ab540cd91
Evidence: `tests/test_remaining_modules.py:152-169`; `tests/test_remaining_modules.py:301-334`; `tests/test_remaining_modules.py:726-729`
Reason: The follow-up CodeRabbit review shell is fully addressed: the dataset-path assertion now uses a normalized POSIX path, the fake dataset capture uses closure-local state instead of a mutable class attribute, and the helper variable name is now `id_val` to match PEP 8.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#pullrequestreview-4150781157 -> ab540cd91

Disposition: FIXED
Commit: 29b1a61d0
Evidence: `tests/evals/test_ragas_runner_contract.py:245-258`
Reason: The runner-contract test name now matches the function under test, so the suite no longer advertises `_extract_metric_scores` while actually exercising `_validate_metric_scores`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#pullrequestreview-4150797713 -> 29b1a61d0

Disposition: FIXED
Commit: b2e5d5c0a
Evidence: `evals/ragas/run_ragas_eval.py:115-159`; `tests/evals/test_ragas_runner_contract.py:160-180`; `docs/evals/RAGAS_SETUP.md:51-60`
Reason: Dataset-row normalization now rejects conflicting `reference` / `ground_truth` values instead of silently preferring one field, and the companion setup doc now makes the same contract explicit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#discussion_r3120117336 -> b2e5d5c0a

Disposition: FIXED
Commit: b2e5d5c0a
Evidence: `tests/evals/test_ragas_runner_contract.py:130-157`; `tests/test_remaining_modules.py:429-438`
Reason: The runner contract now explicitly covers repo-relative dataset-path rendering for the in-repo bootstrap fixture, and the smoke suite keeps `_display_path(...)` on the default dataset under coverage.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#discussion_r3120117339 -> b2e5d5c0a

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane`
Reason: Explicit local judge wiring for RAGAS-native metrics is valid follow-up hardening, but adding a governed local judge stack or new dependency/config surface would widen this companion bootstrap lane beyond the approved scope. The setup doc now records that this hardening remains under the existing release-gates follow-up umbrella.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#discussion_r3120123611

Disposition: NOT-A-BUG
Evidence: `requirements-evals.txt:1-2`; `docs/evals/RAGAS_SETUP.md:65-80`
Reason: This bootstrap lane intentionally keeps `requirements-evals.txt` as a minimal manual-install surface (`ragas`, `datasets`) and does not introduce a compiled or lockfile-backed eval dependency lane in this PR. Pinning/compiling eval extras would widen scope beyond the approved companion bootstrap contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#discussion_r3120123614

Disposition: FIXED
Commit: b2e5d5c0a
Evidence: `evals/AGENTS.md:1-20`; `tests/evals/AGENTS.md:1-11`
Reason: Scoped AGENTS authority is now correct: `evals/AGENTS.md` only governs the `evals/` subtree, and eval-test-specific rules moved into a dedicated descendant file under `tests/evals/`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#discussion_r3120142369 -> b2e5d5c0a

Disposition: FIXED
Commit: b2e5d5c0a
Evidence: `evals/ragas/run_ragas_eval.py:232-293`; `tests/evals/test_ragas_runner_contract.py:245-259`; `tests/test_remaining_modules.py:372-383`
Reason: Metric-score coercion now re-raises malformed values as controlled `RuntimeError` with metric/source context instead of leaking raw `TypeError` from `float(...)`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#discussion_r3120142373 -> b2e5d5c0a

Disposition: FIXED
Commit: b2e5d5c0a
Evidence: `evals/ragas/run_ragas_eval.py:322-329`; `tests/test_remaining_modules.py:321-371`
Reason: `evaluate_records(...)` now uses an `inspect.signature(...)` capability check for `show_progress` instead of retrying on every `TypeError`, so real evaluator failures are no longer masked by a blanket fallback.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#discussion_r3120142378 -> b2e5d5c0a

Disposition: NOT-A-BUG
Evidence: `requirements-evals.txt:1-2`; `docs/evals/RAGAS_SETUP.md:65-80`
Reason: This bootstrap lane intentionally keeps `requirements-evals.txt` as a minimal manual-install surface (`ragas`, `datasets`) and does not introduce a compiled or lockfile-backed eval dependency lane in this PR. Pinning/compiling eval extras would widen scope beyond the approved companion bootstrap contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#discussion_r3120142386

Disposition: FIXED
Commit: b2e5d5c0a
Evidence: `tests/evals/test_ragas_runner_contract.py:42-55`
Reason: The import-laziness test now forces `ragas` / `datasets` unavailable in `sys.modules` before a cold import, so the contract no longer depends on whether optional eval extras happen to be installed in CI.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#discussion_r3120142392 -> b2e5d5c0a

Disposition: FIXED
Commit: 39025418f
Evidence: `tests/evals/test_ragas_runner_contract.py:42-50`
Reason: The cold-import test now removes the cached runner module via `monkeypatch.delitem(...)`, so teardown is consistent with the rest of the forced optional-dependency stubs and no direct `sys.modules.pop(...)` mutation remains.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1489#discussion_r3120262364 -> 39025418f

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green on latest pushed head
  Evidence: local `pre-commit run --all-files` passed on the current remediation head, and the `git commit` hook passed for `b2e5d5c0a`
- [ ] `make verify` green on latest pushed head
  Evidence: `verify-env`, `lint`, `typecheck`, and `test-fast` passed in the final local run; fresh `coverage.xml` plus manual `diff-cover` confirmed the diff gate after the long `diff-cov` coverage pass ended with external `Terminated: 15`, so a clean uninterrupted `make verify` rerun remains outstanding before any merge-ready claim

## Notes

- This PR is a companion bootstrap lane, not a second canonical evaluation rail.
  The canonical internal evaluation lane remains
  `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`.
- Existing evaluation continuity stays under
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane`.
