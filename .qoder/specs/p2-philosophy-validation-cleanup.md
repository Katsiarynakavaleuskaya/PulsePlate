# P2 Philosophy Validation Cleanup

## Problem
`legacy_app.py` has ~37 lines of identical validation logic duplicated between `insight_v1()` (lines 2201-2237) and `insight()` (lines 2287-2323). This violates AGENTS.md policy: "legacy_app.py is a thin compatibility proxy only. Forbidden: runtime behavior changes."

## Solution
Extract duplicated RAG+validation orchestration logic into `core/rag/orchestration.py`.

## Architecture Decision
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| `core/rag/orchestration.py` | Domain-aligned, reusable | New file | **Selected** |
| `app/routers/_helpers.py` | Follows paywall pattern | Mixes domain with presentation | Rejected |
| `app/services/rag_service.py` | Service layer abstraction | Over-abstraction for thin logic | Rejected |

## Implementation

### Step 1: Create `core/rag/orchestration.py`

```python
@dataclass
class RAGOrchestrationResult:
    rag_sources: list[RAGSourceItem]
    formatted_prompt: str
    rag_actually_used: bool
    confidence: Optional[float]
    hops: int
    latency_ms: int
    warnings: list[str]

async def retrieve_and_validate_rag(
    prompt_input: str,
    max_chunks: int = 3,
) -> RAGOrchestrationResult:
    """Orchestrate RAG retrieval + philosophy validation.

    Returns empty result on any failure (fail-safe).
    Feature flag checked inside (lazy import preserved).
    """
```

**Logic:**
1. Retrieve chunks via `retrieve_context_structured()`
2. If `FEATURE_PHILOSOPHY_VALIDATION=true`: call `validate_rag_chunks()`
3. Recalculate confidence from filtered chunks
4. Format prompt with RAG context
5. Return structured result

### Step 2: Create `tests/test_rag_orchestration.py`

**Test cases (8 tests, 100% coverage):**
1. Happy path: chunks retrieved + validation filters some
2. No chunks retrieved -> empty result
3. Validation disabled (flag off) -> all chunks used
4. All chunks filtered -> `rag_actually_used=False`
5. Import failure -> graceful fallback (empty result)
6. Confidence recalculation correctness
7. Prompt formatting includes RAG context
8. Warnings propagated from validation

### Step 3: Refactor `legacy_app.py`

**Before** (~37 lines per endpoint):
```python
if use_rag:
    with suppress(Exception):
        from core.rag.vector_rag import retrieve_context_structured
        rag_ctx = await run_in_threadpool(...)
        # ... 30+ lines of logic
```

**After** (~5 lines per endpoint):
```python
if use_rag:
    from core.rag.orchestration import retrieve_and_validate_rag
    rag_result = await retrieve_and_validate_rag(prompt_input)
    rag_sources = rag_result.rag_sources
    prompt_text = rag_result.formatted_prompt
    rag_actually_used = rag_result.rag_actually_used
    # ... use remaining fields
```

### Step 4: Verify

```bash
make test-fast              # smoke tests
make diff-cov               # >= 97%
pytest tests/test_repo_policy_guards.py  # import hygiene
make lint                   # ruff/mypy
```

## Files to Modify

| File | Action |
|------|--------|
| `core/rag/orchestration.py` | **Create** - orchestration logic |
| `tests/test_rag_orchestration.py` | **Create** - test coverage |
| `legacy_app.py` (lines 2201-2237) | **Refactor** - delegate to orchestration |
| `legacy_app.py` (lines 2287-2323) | **Refactor** - delegate to orchestration |
| `core/rag/__init__.py` | **Update** - export orchestration |

## Success Criteria

- [ ] `legacy_app.py` lines reduced by ~60 (30 per endpoint)
- [ ] Zero duplicated validation logic between endpoints
- [ ] RAG+validation behavior unchanged (no regressions)
- [ ] `make verify` passes (lint, typecheck, test-fast, diff-cov >= 97%)
- [ ] All bot comments addressed (Sourcery, CodeRabbit)
- [ ] Green CI with zero unresolved comments

## Commit Plan

1. `feat(rag): add orchestration module for RAG+validation pipeline`
2. `refactor(legacy): delegate insight validation to orchestration helper`
3. `test(rag): add orchestration unit tests for 100% coverage`
