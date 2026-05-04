# PR 1659 Pre-mortem -- Canonical-Fail Invariance Fixtures

## Summary

This pre-mortem assumes the PR failed after merge and records the highest-risk
failure modes for canonical-fail negative-control fixture coverage.

## Failure Mode 1 -- Fake negative-control coverage

Risk: canonical-fail rows exist but no invariance row preserves the failing decision.

Mitigation: tests require fail-to-fail invariance for both judgment and RAG fixtures.

## Failure Mode 2 -- Judgment decision drift

Risk: fixture work accidentally changes promote/defer/discard mapping.

Mitigation: existing judgment tests must pass; fixture changes remain data/test/docs-only.

## Failure Mode 3 -- RAG threshold drift

Risk: fixture work accidentally changes release-gate thresholds or PASS/NO-GO logic.

Mitigation: existing RAG sidecar and release-gate tests must pass; threshold checks
remain unchanged.

## Failure Mode 4 -- Nondeterministic report output

Risk: unstable item ordering or slice breakdown differs across runs.

Mitigation: deterministic report tests remain active for both fixture sets.
Two-run diff confirmed identical output for both judgment and RAG reports.

## Failure Mode 5 -- Scope creep into advanced eval science

Risk: PR expands into hybrid adjudication, IRT, tool-use reliability,
semantic cache, or retriever rewrite.

Mitigation: allowed-files check confirms only data/evals, tests/evals, and docs
are touched. No runtime files modified.

## Required Evidence Before Merge

- `pytest -q tests/evals/` (137 passed)
- `pytest -q tests/test_judgment_eval.py` (passed)
- `pytest -q tests/evals/test_rag_release_gate_validity_sidecar.py` (passed)
- `pytest -q tests/test_rag_release_gates_runner.py` (passed)
- repeated validity reports are deterministic (diff clean)
- `make test-fast` (144 passed)
- `make lint` (clean)
- pre-push hooks all passed
