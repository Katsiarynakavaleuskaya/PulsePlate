# PR #1585 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1585>
Branch: `codex/investigate-rag-release-gates-vulnerability`
Date: 2026-04-29

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Sourcery raised actionable review feedback about canonical path reuse and
public-interface coverage for the spoofed small-fixture advisory path.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1585#pullrequestreview-4200326196 -> a2f8ca5f9d934af32cc53722a8c846921110d6a4

Disposition: FIXED
Commit: a2f8ca5f9d934af32cc53722a8c846921110d6a4
Evidence: `scripts/evals/run_rag_release_gates.py` uses module-level `CANONICAL_RAG_EVAL_SAMPLE_PATH`; `tests/test_rag_release_gates_runner.py` includes public `main(... --require-pass)` coverage for a spoofed canonical basename.
