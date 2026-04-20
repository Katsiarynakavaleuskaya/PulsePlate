# PR #1484 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is the source of truth for review dispositions on PR #1484.
Record every actionable human or bot review item here before resolving threads or
claiming merge readiness.

## Fixed in Commit Mapping

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane`
Reason: Sourcery's high-level request to split the runner into smaller modules
and fully deduplicate notebook/runner logic is valid follow-up architecture work,
but widening this PR beyond the bounded release-gates lane would violate the
approved packet scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139606616

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139611496`
Reason: The Codex connector review entry is only the review-shell notice for the
integration and does not introduce separate inline actionables beyond the items
already dispositioned elsewhere in this artifact.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139611496

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1484_FIXED_MAPPING.md`
Reason: This CodeRabbit review shell only aggregates inline findings. It does
not add a separate shell-only actionable beyond the individual review-thread
entries dispositioned below.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139607755

Disposition: FIXED
Commit: 463692ea9
Evidence: `.github/workflows/rag-release-gates.yml:84-96`;
`docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md:268-291`
Reason: The weekly/manual lane no longer hardcodes the missing
`data/evals/rag_weekly_500.jsonl` file. Instead it accepts an injected dataset
path via workflow input or repo variable, with deterministic sample-fixture
fallback and preserved strict flags.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110360496 -> 463692ea9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110363640 -> 463692ea9

Disposition: FIXED
Commit: d1fc36ed5
Evidence: `.github/workflows/rag-release-gates.yml:36-54`;
`docs/roadmap/BACKLOG_LEDGER.md:1639-1667`
Reason: Smoke-job dependency installation and `timeout-minutes` are now explicit,
and the ledger entry now documents the canonical contract note plus concrete
blockers / exit criteria for the persistence seam.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110360520 -> d1fc36ed5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110360521 -> d1fc36ed5

Disposition: FIXED
Commit: f9e730981
Evidence: `notebooks/pulseplate_rag_release_gates.ipynb`
Reason: The notebook chunking loop now advances with the same overlap semantics
as the runner (`max(0, end - overlap)`) instead of the broken
`max(end - overlap, end)` update.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110360523 -> f9e730981

Disposition: FIXED
Commit: f9e730981
Evidence: `notebooks/pulseplate_rag_release_gates.ipynb`
Reason: The notebook now uses `TOP_K` instead of the undefined lowercase
`top_k` in `recall_at_effective_k`, so the analyst artifact matches the runner's
contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110360527 -> f9e730981

Disposition: FIXED
Commit: f9e730981
Evidence: `scripts/evals/run_rag_release_gates.py:1788-1800`
Reason: The parquet-export fallback no longer binds an unused exception variable;
the CSV fallback behavior remains unchanged.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110456134 -> f9e730981

Disposition: FIXED
Commit: f9e730981
Evidence: `scripts/evals/run_rag_release_gates.py:1788-1800`
Reason: This CodeRabbit shell only summarized the single unused parquet-fallback
exception binding, which is already fixed in the runner.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139720492 -> f9e730981

Disposition: FIXED
Commit: e0d463d12
Evidence: `.github/workflows/rag-release-gates.yml:5-18,37-43,75-81`
Reason: The workflow now self-triggers on edits to its own file, sets
`SERVER_SALT` for both jobs, and uses the repo-level timeout variable through
`fromJSON(...)` across smoke and weekly/manual jobs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139765757 -> e0d463d12
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110489329 -> e0d463d12
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110489367 -> e0d463d12
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110489370 -> e0d463d12

Disposition: FIXED
Commit: b1320803a
Evidence: `.github/workflows/rag-release-gates.yml:37-43`;
`notebooks/pulseplate_rag_release_gates.ipynb`;
`scripts/evals/run_rag_release_gates.py:2049-2066`;
`tests/test_rag_release_gates_runner.py:332-377`
Reason: The cubic inline findings are now closed: manual dispatch no longer runs
the smoke lane, the notebook preserves guard-blocked routing decisions, and the
runner rejects non-positive `sample_size` / `top_k` instead of silently
degrading the evaluation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110469280 -> b1320803a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110469281 -> b1320803a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110469284 -> b1320803a

Disposition: FIXED
Commit: b1320803a
Evidence: `notebooks/pulseplate_rag_release_gates.ipynb`
Reason: The notebook now matches the runner defaults for
`support_precision=0.70`, and the dead `answer_norm` assignment is removed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139863623 -> b1320803a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110563101 -> b1320803a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110563123 -> b1320803a

Disposition: FIXED
Commit: b95ec5a04
Evidence: `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md:282-289`;
`scripts/evals/run_rag_release_gates.py:1458-1484`;
`tests/test_rag_release_gates_runner.py:210-219`
Reason: Final cleanup for the cubic shell: the notebook execution example now
writes into the experiment-scoped artifact directory, and the ECE implementation
keeps the terminal bucket bounded to `[0.9, 1.0]` with regression coverage.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110469263 -> b95ec5a04
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110469270 -> b95ec5a04

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1484_FIXED_MAPPING.md`
Reason: This cubic review shell summarizes inline findings that are already
dispositioned in the `b1320803a` and `b95ec5a04` FIXED blocks above. It does
not carry a separate shell-only actionable once those inline items are mapped.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4139739953

Disposition: FIXED
Commit: 27a6b05e5
Evidence: `.github/workflows/rag-release-gates.yml:66-118`;
`notebooks/pulseplate_rag_release_gates.ipynb:405-411`;
`tests/test_rag_release_gates_runner.py:650-729`
Reason: Current-head follow-up fixes now archive `traces.jsonl` for both smoke
and weekly artifact uploads, restore canonical `monkeypatch.setattr(...)`
patching in the strict validator-gap test, and add the missing terminal break in
the notebook chunking loop so the final overlapped slice cannot spin forever.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110692122 -> 27a6b05e5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110692167 -> 27a6b05e5

Disposition: NOT-A-BUG
Evidence: `core/rag/contracts.py:71-79`;
`notebooks/pulseplate_rag_release_gates.ipynb:501-530`
Reason: The live `RAGChunk` contract in this repo still exposes
`chunk_id/file/content/score/hop`. The notebook's PulsePlate retrieval adapter
already reads those public fields correctly, so the suggested `text/metadata`
rewrite would contradict the current source of truth.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110692134

Disposition: NOT-A-BUG
Evidence: `core/rag/contracts.py:71-79`;
`tests/test_rag_release_gates_runner.py:81-112`
Reason: The tests construct `RAGChunk` with the repository's real public
constructor (`chunk_id/file/content/score/hop`). Rewriting those fixtures to a
non-existent `text/metadata` signature would break parity with the actual
contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#discussion_r3110692163

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1484_FIXED_MAPPING.md`
Reason: This CodeRabbit review shell aggregates one real current-head fix
(`traces.jsonl` upload + monkeypatch cleanup + terminal loop break) and two
contract-mismatch comments about `RAGChunk` that are not valid against the live
repo contract. Each inline item is dispositioned separately above, so no
additional shell-only action remains.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1484#pullrequestreview-4140028748

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: live runs queued/pending on current head `fa9634d3e`
- [ ] Required checks complete (no pending jobs)
  Evidence: pending required jobs on current head `fa9634d3e`
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending final post-push review sweep after current-head bot reruns
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending current-head CodeRabbit / cubic rerun results
- [x] Pre-commit green on latest pushed head
  Evidence: local pre-push hooks passed on latest pushed head `fa9634d3e`
- [ ] `make verify` green on latest pushed head
  Evidence: not yet run for this lane

## Notes

- The lane packet remains the scope boundary for this PR; broader refactors and
  dashboard/persistence expansion stay out of scope until a separate governed
  follow-up exists.
  Evidence:
  `docs/orchestration/PULSEPLATE_RAG_RELEASE_GATES_TASK_PACKET_2026-04-20.md:24-58`
- Current-head merge truth must come from the latest status checks on the latest
  pushed head, not from older cancelled or superseded runs.
  Evidence: `RUNBOOK_AGENT.md:448-450`;
  `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-163`
- Mandatory role-order evidence is not yet complete for a merge-ready claim:
  `qa-engineer-agent` and `security-auditor` still need an explicit final pass or
  a canonical no-actionable record on the latest head.
  Evidence:
  `docs/orchestration/PULSEPLATE_RAG_RELEASE_GATES_TASK_PACKET_2026-04-20.md:26-37`
