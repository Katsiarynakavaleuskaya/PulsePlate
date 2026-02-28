# RAG Feedback Storage Implementation Spec

## Summary

Implement persistent storage for RAG feedback (`rag_feedback`) and user knowledge (`user_knowledge`) per `docs/contracts/RAG_CONTRACT.md` §7, with adaptations for existing codebase patterns.

## Design Decisions

| Aspect | Contract | Implementation | Rationale |
|--------|----------|----------------|-----------|
| Primary Keys | UUID | **Integer** | All 20+ tables use Integer PKs |
| User FK | UUID | **Integer** | `users.id` is Integer |
| RLS | Required | **Application-layer** | No RLS anywhere in codebase |
| pgvector | Required | **Postgres-only conditional** | SQLite tests need compatibility |

## Files to Create/Modify

### New Files

1. **`alembic/versions/202602280001_add_rag_feedback_tables.py`** - Migration
2. **`app/models/rag_feedback.py`** - RAGFeedback + UserKnowledge models
3. **`core/pii_redaction.py`** - PII redaction helper
4. **`app/routers/feedback.py`** - Feedback submission endpoint
5. **`tests/test_feedback_api.py`** - Endpoint tests
6. **`tests/test_pii_redaction.py`** - Redaction tests
7. **`docs/db/rag_feedback_schema.md`** - Schema documentation

### Modified Files

1. **`app/models/__init__.py`** - Export new models
2. **`app/main.py`** - Register feedback router
3. **`docs/roadmap/BACKLOG_LEDGER.md`** - Update P1 status

## Schema

### rag_feedback

```sql
CREATE TABLE rag_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_id VARCHAR(64),
    query TEXT NOT NULL,
    retrieved_chunks JSONB,  -- [{chunk_id, file, preview, score}]
    llm_response TEXT,       -- PII redacted
    user_rating SMALLINT CHECK (user_rating BETWEEN 1 AND 5),
    user_correction TEXT,    -- PII redacted
    confidence FLOAT CHECK (confidence BETWEEN 0.0 AND 1.0),
    hops SMALLINT CHECK (hops >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_rag_feedback_user_created ON rag_feedback(user_id, created_at DESC);
CREATE INDEX idx_rag_feedback_agent ON rag_feedback(agent_id) WHERE agent_id IS NOT NULL;
```

### user_knowledge (VIP-only)

```sql
CREATE TABLE user_knowledge (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(768),   -- pgvector, NULL on SQLite
    source VARCHAR(256),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_user_knowledge_user ON user_knowledge(user_id);
-- Vector index deferred until embedding pipeline ready
```

## API Endpoint

### POST /api/v1/feedback/rag

**Request:**
```json
{
  "agent_id": "insight-default",
  "query": "What is BMI?",
  "retrieved_chunks": [...],
  "llm_response": "BMI is...",
  "user_rating": 5,
  "user_correction": null,
  "confidence": 0.95,
  "hops": 1
}
```

**Response (201):**
```json
{"id": 123, "message": "Feedback submitted successfully"}
```

**Security:**
- Requires authentication (session or API key)
- PII auto-redacted from `llm_response` and `user_correction`
- Tier: FREE (feedback collection benefits all users)

## PII Redaction

```python
# core/pii_redaction.py
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')

def redact_pii_from_text(text: str | None) -> str | None:
    """Replace common PII with [*_REDACTED] tokens."""
```

## pgvector Handling

**Postgres:**
- Create extension if not exists: `CREATE EXTENSION IF NOT EXISTS vector`
- Use `VECTOR(768)` for embeddings

**SQLite (tests):**
- Column type: `TEXT` (nullable, stores JSON or ignored)
- Embedding tests skipped with `@pytest.mark.skipif(is_sqlite)`

**Migration pattern:**
```python
from sqlalchemy.dialects import postgresql

# Conditional column
if dialect == "postgresql":
    embedding = Column(postgresql.VECTOR(768), nullable=True)
else:
    embedding = Column(Text, nullable=True)  # Stub for SQLite
```

## Implementation Order

1. **core/pii_redaction.py** + tests
2. **app/models/rag_feedback.py** (both models)
3. **alembic migration** (with pgvector conditional)
4. **app/routers/feedback.py** + tests
5. **docs/db/rag_feedback_schema.md**
6. **Update BACKLOG_LEDGER**
7. **make verify**

## Verification

```bash
# 1. Migration
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# 2. Model import
python -c "from app.models.rag_feedback import RAGFeedback, UserKnowledge"

# 3. Run tests
pytest tests/test_pii_redaction.py -v
pytest tests/test_feedback_api.py -v

# 4. Full verification
make verify

# 5. Smoke test
curl -X POST http://localhost:8000/api/v1/feedback/rag \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "user_rating": 5}'
```

## Follow-up Items (track in BACKLOG_LEDGER)

- [ ] P1: Database RLS policies (project-wide, not just RAG)
- [ ] P1: Vector similarity search API for user_knowledge
- [ ] P2: Advanced PII redaction (NER-based via Presidio)
- [ ] P2: Feedback analytics dashboard

## Critical Files

| File | Purpose |
|------|---------|
| `alembic/versions/202602280001_add_rag_feedback_tables.py` | Migration DDL |
| `app/models/rag_feedback.py` | SQLAlchemy models |
| `core/pii_redaction.py` | PII redaction helper |
| `app/routers/feedback.py` | POST endpoint |
| `tests/test_feedback_api.py` | Endpoint tests |
