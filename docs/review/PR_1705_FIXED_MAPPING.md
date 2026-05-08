# PR 1705 Fixed Mapping

## Summary

SC-G4 bounded `/insight` semantic-cache experiment. The PR adds a deterministic, metadata-only, off-by-default decision layer and machine-checkable contract while keeping the global semantic-cache gate closed.

## Local Evidence

- Commit: `250a1f856` `feat(ai-runtime): add bounded insight semantic-cache experiment`
- Follow-up commit: `e388863c4` `fix(ai-runtime): close bounded insight review gaps`
- Follow-up commit: `83c372b1f` `fix(ai-runtime): harden bounded insight linkage guards`
- Follow-up commit: `18a333152` `fix(ai-runtime): keep linkage mismatch typing explicit`
- Follow-up commit: `878b316a6` `fix(ai-runtime): bind bounded insight audit fingerprints`
- Follow-up commit: `3e5f9ca6f` `fix(ai-runtime): close bounded insight bot findings`
- Follow-up commit: `153c65302` `fix(ai-runtime): keep bounded insight helper typing strict`
- Follow-up commit: `b25a370b2` `fix(ai-runtime): omit rejected bounded insight candidate payloads`
- Follow-up commit: `014017e6a` `fix(ai-runtime): harden bounded insight metadata contracts`
- Follow-up commit: `2f0692a67` `fix(ai-runtime): return json-ready bounded insight mappings`
- Follow-up commit: `c1fc167cd` `fix(ci): include bounded insight tests in coverage lane`
- Follow-up commit: `d8af82a6e` `docs(review): map bounded insight bot findings`
- Follow-up commit: `11311d937` `fix(ai-runtime): close bounded insight diff coverage gaps`
- Follow-up commit: `aa0204417` `docs(review): map bounded insight coverage fix`
- Follow-up commit: `844e1416b` `docs(review): record bounded insight coverage mapping`
- Follow-up commit: `613abbb68` `docs(review): fix bounded insight GitHub wording`
- `python scripts/orchestration/check_preflight.py` PASS
- `python scripts/orchestration/check_agent_consistency.py` PASS
- `python scripts/ci/check_semantic_cache_gate.py` PASS
- `python scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/contracts/SEMANTIC_CACHE_BOUNDED_INSIGHT_EXPERIMENT.md docs/orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.md docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md` PASS
- Focused semantic-cache pytest bundle PASS
- Narrow mypy PASS
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` PASS
- `PATH=.venv/bin:$PATH pre-commit run --from-ref origin/main --to-ref HEAD` PASS

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 3e5f9ca6f, 014017e6a, 2f0692a67
Evidence: `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py`, `docs/review/PR_1705_FIXED_MAPPING.md`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#pullrequestreview-4250807388 -> 3e5f9ca6f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#discussion_r3207440778 -> 3e5f9ca6f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#discussion_r3207440785 -> 3e5f9ca6f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#discussion_r3207399328 -> 3e5f9ca6f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#discussion_r3207399336 -> e388863c4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#discussion_r3207480050 -> 3e5f9ca6f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#pullrequestreview-4250851460 -> 3e5f9ca6f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#pullrequestreview-4251227882 -> 014017e6a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#discussion_r3207798992 -> 014017e6a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#discussion_r3207799842 -> 014017e6a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#discussion_r3207799846 -> 2f0692a67
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#pullrequestreview-4251228938 -> 2f0692a67
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#discussion_r3208706618 -> 613abbb68
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1705#pullrequestreview-4252289237 -> 613abbb68

## Post-Open Agent Finding Mapping

| Finding | Disposition | Evidence |
| --- | --- | --- |
| Require promotion/replay linkage before eligibility | FIXED | Commit `e388863c4`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py` |
| Validate audit event partition fields | FIXED | Commit `e388863c4`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py` |
| Fix Phase 2 mapping artifact format | FIXED | Commit `e388863c4`; `docs/review/PR_1705_FIXED_MAPPING.md`, PR body mirror |
| Require Evidence Graph ID equality across request, record, and audit event | FIXED | Commit `83c372b1f`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py` |
| Harden SC-G4 checker against unsafe bare backend/raw-payload wording | FIXED | Commit `83c372b1f`; `scripts/ci/check_semantic_cache_gate.py`, `tests/test_semantic_cache_bounded_insight_experiment_contract.py` |
| Keep pre-push mypy strict on linkage mismatch helper | FIXED | Commit `18a333152`; `core/ai/bounded_insight_semantic_cache.py`; `python -m mypy ...` PASS |
| Bind SC-G4 decisions to audited request fingerprint | FIXED | Commit `878b316a6`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py` |
| Require safety flag parity before eligibility | FIXED | Commit `3e5f9ca6f`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py` |
| Do not attach candidate record/response metadata on lookup miss | FIXED | Commit `3e5f9ca6f`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py` |
| Replace `Phase2` spelling with `Phase 2` | FIXED | Commit `3e5f9ca6f`; `docs/review/PR_1705_FIXED_MAPPING.md` |
| Keep strict mypy compatibility for eligible candidate helper returns | FIXED | Commit `153c65302`; `core/ai/bounded_insight_semantic_cache.py`; `python -m mypy ...` PASS |
| Omit candidate identifiers and response fingerprints on all rejected fallback decisions | FIXED | Commit `b25a370b2`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py`; focused pytest + mypy PASS |
| Require candidate response fingerprint parity before bound-hit metadata eligibility | FIXED | Commit `014017e6a`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py`; focused pytest + mypy PASS |
| Deep-freeze nested metadata without breaking JSON-ready stable mappings | FIXED | Commit `014017e6a`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py`; focused pytest + mypy PASS |
| Reject non-string token inputs with `ValueError` instead of `AttributeError` | FIXED | Commit `014017e6a`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py`; focused pytest + mypy PASS |
| Return plain JSON-ready stable mappings from `to_stable_mapping()` | FIXED | Commit `2f0692a67`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py`; focused pytest + mypy PASS |
| Include SC-G4 tests in CI coverage selection | FIXED | Commit `c1fc167cd`; GitHub Actions workflow coverage lane; focused pytest, mypy, changed-files pre-commit, and `make validate-changed` PASS |
| Close remaining SC-G4 diff coverage gaps | FIXED | Commit `11311d937`; `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py`; local diff-cover 100% PASS |

## Premortem Finding Mapping

| Finding | Disposition | Evidence |
| --- | --- | --- |
| SC-G4 could imply gate-open or serving | FIXED | `scripts/ci/check_semantic_cache_gate.py`, `tests/test_semantic_cache_bounded_insight_experiment_contract.py` |
| Default-on experiment | FIXED | `core/ai/bounded_insight_semantic_cache.py`, `tests/core/ai/test_bounded_insight_semantic_cache.py` |
| Hidden runtime import path | FIXED | `tests/test_semantic_cache_bounded_insight_experiment_contract.py` side-door guard |
| Negative controls becoming safe hits | FIXED | `core/ai/cache_observability.py`, `tests/core/ai/test_cache_observability.py` |
| Miss audit event with hit-like mode | FIXED | `core/ai/cache_observability.py`, `tests/core/ai/test_cache_observability.py` |
| Raw auth/header metadata leakage | FIXED | `core/ai/cache_observability.py`, `core/ai/bounded_insight_semantic_cache.py`, focused tests |

## Merge Readiness

Not merge-ready yet. Await current-head CI, bot/human review disposition, Codex Security pass, strict merge-readiness wrapper, unresolved-thread check, and mandatory wait-window.
