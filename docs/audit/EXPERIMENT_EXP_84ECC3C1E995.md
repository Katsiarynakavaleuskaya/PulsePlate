# Experiment Audit Artifact: exp-84ecc3c1e995

- Decision question: Harden RAG orchestration confidence handling so malformed retriever metadata degrades gracefully instead of dropping the full result
- Promotion target: `audit_artifact`
- Disposition: `promoted`
- Result status: `accepted`
- Failure class: `none`

## Mutable Surface

- `core/rag/orchestration.py`

## Immutable Oracles

- `pytest -q tests/test_rag_orchestration.py` (must pass)
- `pytest -q tests/test_insight_rag_response_fields.py` (must pass)
- `pytest -q tests/test_rag_vector_feature_flag_guard.py` (must pass)

## Evidence

- Implementation anchor: `core/rag/orchestration.py:72`
- Confidence fallback helper path: `core/rag/orchestration.py:97`
- Regression coverage for malformed retriever confidence: `tests/test_rag_orchestration.py:164`
- Regression coverage for malformed filtered chunk scores: `tests/test_rag_orchestration.py:429`
- Regression coverage for all-invalid-score degrade path: `tests/test_rag_orchestration.py:469`
- `pytest -q tests/test_rag_orchestration.py` -> rc=0, timed_out=false, truncated=false
- `pytest -q tests/test_insight_rag_response_fields.py` -> rc=0, timed_out=false, truncated=false
- `pytest -q tests/test_rag_vector_feature_flag_guard.py` -> rc=0, timed_out=false, truncated=false

## Deferred Follow-up Block

- Owner: `@katsiaryna_kavaleuskaya`
- Priority: `P1`
- Target PR: `PR_TBD_EXP_84ECC3C1E995`
- Reason: `failure_class=none`
