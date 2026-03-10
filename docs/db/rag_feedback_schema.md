# RAG Feedback Schema Documentation

**Migration**: `alembic/versions/202602280001_add_rag_feedback_tables.py`
**Contract**: `docs/contracts/RAG_CONTRACT.md` §7

---

## Overview

Two tables for RAG quality improvement and VIP personalization:

1. **`rag_feedback`** - User feedback on RAG responses
2. **`user_knowledge`** - User-contributed knowledge corpus (VIP)

---

## rag_feedback

Stores user ratings, corrections, and metadata about RAG interactions to enable recursive learning.

### Schema

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `Integer` | PK, autoincrement | Auto-increment ID |
| `user_id` | `Integer` | FK(users.id), NOT NULL | User who provided feedback |
| `agent_id` | `String(64)` | NULL | Optional agent identifier |
| `query` | `Text` | NOT NULL | User's original query |
| `retrieved_chunks` | `Text` | NULL | Retrieved chunks: `[{chunk_id, file, preview, score}]` |
| `llm_response` | `Text` | NULL | LLM response (PII redacted) |
| `user_rating` | `SmallInteger` | CHECK(1-5) | User satisfaction rating |
| `user_correction` | `Text` | NULL | User's corrected response (PII redacted) |
| `confidence` | `Float` | CHECK(0.0-1.0) | RAG confidence score |
| `hops` | `SmallInteger` | CHECK(>=0) | Number of retrieval hops |
| `created_at` | `DateTime(tz)` | NOT NULL, server_default | Submission timestamp |

### Indexes

- `idx_rag_feedback_user_id` on `user_id` - Fast user lookup
- `idx_rag_feedback_user_created` on `(user_id, created_at)` - User history queries
- `idx_rag_feedback_agent` on `agent_id` - Agent analytics

### Security

- **PostgreSQL RLS**: `rag_feedback` and `user_knowledge` enforce `user_id` isolation with transaction-local setting `app.current_user_id`
- **Application-layer filtering**: Existing authenticated `user_id` scoping remains in runtime code as defense in depth
- **PII redaction**: `llm_response` and `user_correction` pass through `core.pii_redaction.redact_pii_from_text()` before storage

---

## user_knowledge

Stores user-specific content for personalized RAG retrieval. VIP-only feature.

### Schema

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `Integer` | PK, autoincrement | Auto-increment ID |
| `user_id` | `Integer` | FK(users.id), NOT NULL | Knowledge owner |
| `content` | `Text` | NOT NULL | Knowledge content |
| `embedding` | `Text` | NULL | Vector embedding (JSON on SQLite, VECTOR(768) on Postgres) |
| `source` | `String(256)` | NULL | Content source identifier |
| `created_at` | `DateTime(tz)` | NOT NULL, server_default | Creation timestamp |

### Indexes

- `idx_user_knowledge_user` on `user_id` - User lookup
- `idx_user_knowledge_source` on `source` - Source filtering

### Notes

- **pgvector**: For production Postgres, consider `ALTER COLUMN embedding TYPE VECTOR(768)` after enabling pgvector extension
- **SQLite**: Embeddings stored as JSON text (not searchable)
- **Vector index**: IVFFlat/HNSW index should be added when embedding pipeline is implemented

---

## Migration Notes

**Contract divergence** (documented in migration header):

| Aspect | Contract | Implementation | Rationale |
|--------|----------|----------------|-----------|
| Primary Keys | UUID | Integer | All existing tables use Integer PKs |
| User FK | UUID | Integer | `users.id` is Integer |
| RLS | DB policies | PostgreSQL RLS + app-layer filters | SQLite tests stay app-layer only |
| JSONB | Native | TEXT with JSONEncodedDict | SQLite test compatibility |

---

## API Endpoint

### POST /api/v1/feedback/rag

```json
{
  "agent_id": "insight-default",
  "query": "What is BMI?",
  "retrieved_chunks": [{"chunk_id": "c1", "file": "docs/bmi.md", "score": 0.95}],
  "llm_response": "BMI is...",
  "user_rating": 5,
  "confidence": 0.92,
  "hops": 1
}
```

Response: `{"id": 123, "message": "Feedback submitted successfully"}`

---

## Future Enhancements

Tracked in `docs/roadmap/BACKLOG_LEDGER.md`:

- [ ] Database RLS policies (project-wide)
- [ ] Vector similarity search API for `user_knowledge`
- [ ] Advanced PII redaction (NER-based via Presidio)
- [ ] Feedback analytics dashboard
