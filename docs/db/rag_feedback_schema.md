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
| `id` | `SERIAL` | PK | Auto-increment ID |
| `user_id` | `INTEGER` | FK(users.id), NOT NULL | User who provided feedback |
| `agent_id` | `VARCHAR(64)` | NULL | Optional agent identifier |
| `query` | `TEXT` | NOT NULL | User's original query |
| `retrieved_chunks` | `TEXT/JSONB` | NULL | Retrieved chunks: `[{chunk_id, file, preview, score}]` |
| `llm_response` | `TEXT` | NULL | LLM response (PII redacted) |
| `user_rating` | `SMALLINT` | CHECK(1-5) | User satisfaction rating |
| `user_correction` | `TEXT` | NULL | User's corrected response (PII redacted) |
| `confidence` | `FLOAT` | CHECK(0.0-1.0) | RAG confidence score |
| `hops` | `SMALLINT` | CHECK(>=0) | Number of retrieval hops |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Submission timestamp |

### Indexes

- `idx_rag_feedback_user_id` on `user_id` - Fast user lookup
- `idx_rag_feedback_user_created` on `(user_id, created_at)` - User history queries
- `idx_rag_feedback_agent` on `agent_id` - Agent analytics

### Security

- **Application-layer RLS**: All queries filtered by authenticated `user_id`
- **PII redaction**: `llm_response` and `user_correction` pass through `core.pii_redaction.redact_pii_from_text()` before storage

---

## user_knowledge

Stores user-specific content for personalized RAG retrieval. VIP-only feature.

### Schema

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `SERIAL` | PK | Auto-increment ID |
| `user_id` | `INTEGER` | FK(users.id), NOT NULL | Knowledge owner |
| `content` | `TEXT` | NOT NULL | Knowledge content |
| `embedding` | `TEXT` | NULL | Vector embedding (JSON on SQLite, VECTOR(768) on Postgres) |
| `source` | `VARCHAR(256)` | NULL | Content source identifier |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, DEFAULT NOW() | Creation timestamp |

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
| RLS | DB policies | Application-layer | No RLS anywhere in codebase |
| JSONB | Native | TEXT with JSONEncodedDict | SQLite test compatibility |

---

## API Endpoint

**POST /api/v1/feedback/rag**

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
