# PR 1658 Pre-mortem — RAG Invariance and Mutation Fixtures

## Summary

This pre-mortem assumes the PR failed after merge and records the highest-risk
failure modes for the RAG variant fixture lane.

## Failure Mode 1 — Fake robustness coverage

**Risk:** Curated 4-group fixture set could make the validity report appear more
robust than production RAG actually is. Someone cites `invariance_score=1.0`
as evidence of production robustness.

**Mitigation:** Docs explicitly state that fixtures are deterministic curated
measurement inputs and are not proof of full production robustness. Tests assert
`> 0.0` (not `== 1.0`) so future lower-scoring fixtures won't break.

## Failure Mode 2 — RAG release-gate threshold drift

**Risk:** A future PR modifies `_ITEM_NLI_ENTAILMENT_THRESHOLD` or
`_ITEM_SUPPORT_PRECISION_THRESHOLD` in `rag_release_gate_validity.py` and
the variant test doesn't catch it.

**Mitigation:** `test_rag_variant_fixtures_do_not_modify_release_gate_thresholds`
imports the actual constants from the sidecar adapter and asserts their canonical
values (0.85, 0.80). Evidence: `tests/evals/test_rag_release_gate_validity_variant_families.py:215`.

## Failure Mode 3 — Nondeterministic report output

**Risk:** Dict ordering or list ordering changes across runs causing
`unstable_items` or `slice_breakdown` to differ.

**Mitigation:** `_find_unstable_items` returns `sorted()` list.
`_compute_slice_breakdown` sorts by tag. Test runs `build_validity_report`
twice and compares full JSON serialization. Evidence:
`tests/evals/test_rag_release_gate_validity_variant_families.py:175`.

## Failure Mode 4 — LLM-generated fixture contamination

**Risk:** Fixture rows could contain provider/model/network metadata or
LLM-generated paraphrases.

**Mitigation:** Two tests scan the fixture file for forbidden patterns
(`_LLM_METADATA_PATTERNS` and `_NETWORK_PROVIDER_PATTERNS`). Evidence:
`tests/evals/test_rag_release_gate_validity_variant_families.py:193`.

## Failure Mode 5 — Scope creep into runtime

**Risk:** PR could accidentally mutate runtime/API/frontend/iOS/RAG retriever.

**Mitigation:** Only 5 files changed: 1 JSONL fixture, 1 test file, 3 doc files.
No code changes to `scripts/evals/` or `app/` or `core/`.

## Required Evidence Before Merge

- `pytest -q tests/evals/test_rag_release_gate_validity_variant_families.py`
- `pytest -q tests/evals/test_rag_release_gate_validity_sidecar.py`
- `pytest -q tests/test_rag_release_gates_runner.py`
- `pytest -q tests/evals/`
- Repeated validity report diff is clean
- `make verify` or raw failure output documented
- `pre-commit run --all-files` green
