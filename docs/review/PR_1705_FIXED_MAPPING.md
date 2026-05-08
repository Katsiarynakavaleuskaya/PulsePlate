# PR 1705 Fixed Mapping

## Summary

SC-G4 bounded `/insight` semantic-cache experiment. The PR adds a deterministic, metadata-only, off-by-default decision layer and machine-checkable contract while keeping the global semantic-cache gate closed.

## Local Evidence

- Commit: `250a1f856` `feat(ai-runtime): add bounded insight semantic-cache experiment`
- `python scripts/orchestration/check_preflight.py` PASS
- `python scripts/orchestration/check_agent_consistency.py` PASS
- `python scripts/ci/check_semantic_cache_gate.py` PASS
- `python scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/contracts/SEMANTIC_CACHE_BOUNDED_INSIGHT_EXPERIMENT.md docs/orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.md docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md` PASS
- Focused semantic-cache pytest bundle PASS
- Narrow mypy PASS
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` PASS
- `PATH=.venv/bin:$PATH pre-commit run --all-files` PASS

## Discussion Thread Pass

- [ ] Awaiting CodeRabbit/Sourcery/Cubic/human review.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` lane pending.
- [ ] Codex Security threat-model/security-scan/validation pending.
- [ ] No unresolved actionable review threads before merge readiness.

## Fixed in Commit Mapping

- No actionable review comments yet.

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
