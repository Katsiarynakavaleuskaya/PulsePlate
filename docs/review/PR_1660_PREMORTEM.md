# PR 1660 Pre-mortem — Evaluation Item Metadata Registry

## Frame

It is 6 months from now.  The item metadata registry PR failed after merge.
We are looking backward to understand why.

## Summary

**Plan:** Add a deterministic evaluation item metadata registry for
psychometric readiness, mapping 10 canonical_ids to stable metadata.

**Success:** Registry consumed by future IRT/item-weighting PRs; no
regressions in existing eval tests; no runtime scope creep.

## Failure Mode 1 — Fake psychometrics

**Risk:** Registry labels are mistaken for calibrated IRT/difficulty estimates.

**Underlying assumption:** Consumers will read the docs and notes fields.

**Early warning:** Someone writes `difficulty = registry["difficulty_band"]`
in a scoring function and treats it as a numeric parameter.

**Containment:** Every notes field states "Difficulty band is heuristic label,
not calibrated IRT estimate."  Guard test 15 blocks IRT patterns in the module.

## Failure Mode 2 — Missing item coverage

**Risk:** A future PR adds a fixture canonical_id without a registry row.

**Underlying assumption:** CI always runs the registry coverage tests.

**Early warning:** Coverage tests 5/6/7 fail, but author ignores or skips them.

**Containment:** Tests compare fixture canonical_ids to registry exactly.
Adding a fixture item without a registry row fails CI deterministically.

## Failure Mode 3 — Silent data corruption via malformed JSON

**Risk:** A hand-edit to the JSONL file introduces invalid JSON, non-dict rows,
extra keys, or type mismatches that are not caught by the validator.

**Underlying assumption:** The validator is strict and fail-closed.

**Early warning:** Loader returns wrong data or crashes with unhelpful errors.

**Containment (after premortem):** Validator now rejects non-dict input,
extra keys, empty variant_family_coverage, and non-string canonical_ids.
17 negative validation tests cover all error paths (commit 2143209dc).
Fixture extractor now wraps json.loads with try/except and line numbers.

## Failure Mode 4 — Decision contradiction

**Risk:** Registry expected_decision diverges from fixture canonical decision.

**Containment:** Test 8 enforces parity for all 10 items (8 pass + 2 fail).

## Failure Mode 5 — Runtime scope creep

**Risk:** PR touches runtime/API/RAG thresholds/judgment decisions.

**Containment:** Only `scripts/evals/`, `data/evals/`, `tests/evals/`, and
`docs/` paths are touched.  No `app/`, `core/`, `frontend/`, `ios/`, or
billing paths.

## Failure Mode 6 — Validator looks strict but passes garbage

**Risk:** Validator had str() coercion, accepted empty lists, and did not
reject extra keys or non-dict input.  A future consumer trusts the validator
but receives invalid data.

**Underlying assumption:** TypedDict + type hints = runtime safety.

**Containment (after premortem):** Code review + bug-hunter found and fixed
all 3 code bugs (non-dict guard, empty list guard, fixture JSON error handling)
and added 17 negative tests.  Commit 2143209dc.

## Synthesis

### Most likely failure
A future PR adds a fixture item without a registry row.  Mitigated by
deterministic coverage tests that fail CI immediately.

### Most dangerous failure
Registry labels mistaken for psychometric parameters in a scoring function.
Mitigated by docs, notes fields, and IRT pattern guard test.

### Hidden assumption
That consumers will always read the docs before using registry data.

### Decision
`proceed` — plan is sound after premortem-driven hardening.

### Pre-merge checklist
- [x] `pytest -q tests/evals/test_eval_item_metadata_registry.py` (32/32 pass)
- [x] `pytest -q tests/evals/` (169/169 pass)
- [x] No `app/`, `core/`, `frontend/`, `ios/` files touched
- [x] Pre-push hooks: black, ruff, mypy, pip-audit, pytest, bandit, docker
- [x] Negative validation tests cover all error paths
- [x] CodeRabbit comments dispositioned as FIXED with evidence

## PulsePlate-Specific Checklists

### PR governance
- [x] Preserves AGENTS.md authority
- [x] Preserves AGENT_ROUTING_GRAPH.md
- [x] Preserves Phase2 PR body gates
- [x] Review mapping artifact created (docs/review/PR_1660_FIXED_MAPPING.md)

### Security
- [x] No guards weakened
- [x] No suppressions added
- [x] No secrets or local paths leaked
- [x] No fail-closed gates made advisory

### RAG / LLM / eval
- [x] Offline fixtures only
- [x] No provider calls
- [x] No unverifiable claims
- [x] No private data in eval corpora
- [x] Clear promotion criteria (registry is readiness layer, not scoring)
