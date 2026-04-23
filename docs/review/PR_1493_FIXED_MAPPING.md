# PR #1493 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is the source of truth for review dispositions on PR #1493.
Record every actionable human or bot review item here before resolving threads or
claiming merge readiness.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1493_FIXED_MAPPING.md`
Reason: The Sourcery review shell only aggregates the inline CLI/env-precedence suggestion that is fixed and mapped below; after that inline URL is dispositioned, the review shell adds no separate unresolved obligation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1493#pullrequestreview-4154419522

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1493_FIXED_MAPPING.md`
Reason: This CodeRabbit review shell summarizes the two inline runner findings mapped below for stable companion-path emission and canonical metric ordering; it does not add a separate unresolved action once those inline URLs are dispositioned.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1493#pullrequestreview-4154460774

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1493_FIXED_MAPPING.md`
Reason: This follow-up CodeRabbit review shell only contains the already-mapped fail-fast companion validation finding plus the already-mapped repo-relative path/ordering follow-up, so the shell itself is advisory once those inline comments are covered.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1493#pullrequestreview-4154990039

Disposition: FIXED
Commit: 2aca6ef76
Evidence: `tests/test_rag_release_gates_runner.py:493-579`
Reason: The runner contract now covers explicit CLI wiring for `--companion-metrics-json` and locks the precedence rule so an explicit CLI path wins over the env fallback.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1493#discussion_r3123728964 -> 2aca6ef76

Disposition: FIXED
Commit: 2aca6ef76
Evidence: `scripts/evals/run_rag_release_gates.py:2424-2442`; `tests/test_rag_release_gates_runner.py:1211-1244`
Reason: Companion artifact validation now happens before `run_evaluation(...)`, and the runner test proves malformed companion JSON aborts before the expensive evaluation loop starts.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1493#discussion_r3123731846 -> 2aca6ef76

Disposition: FIXED
Commit: 2aca6ef76
Evidence: `scripts/evals/run_rag_release_gates.py:381-446`; `tests/test_rag_release_gates_runner.py:1125-1137`
Reason: Emitted companion metadata now uses a stable repo-relative artifact path instead of leaking checkout-specific absolute filesystem paths.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1493#discussion_r3123763539 -> 2aca6ef76

Disposition: FIXED
Commit: 2aca6ef76
Evidence: `scripts/evals/run_rag_release_gates.py:434-450`; `tests/test_rag_release_gates_runner.py:1187-1208`
Reason: Companion metrics are normalized in canonical `faithfulness -> answer_relevancy -> context_precision` order, and the dedicated test now protects against noisy diffs from arbitrary JSON key order.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1493#discussion_r3123763553 -> 2aca6ef76

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green on latest pushed head
- [ ] `make verify` green on latest pushed head

## Notes

- This PR is a canonical release-gates follow-up, not a second eval rail.
- Companion RAGAS metrics remain informational only in this lane.
- Post-open reviewer lane completed on head `f9c9de14c`:
  `qa-engineer-agent` and `bug-hunter` reported no remaining delta findings.
- Continuity remains under
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane`.
