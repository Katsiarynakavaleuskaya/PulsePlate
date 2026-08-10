# RAG Contract — Response Schema, Sources, Confidence & Budget

> **Файл:** `docs/contracts/RAG_CONTRACT.md`
> **Версия:** v0.1 (Draft)
> **Дата:** 27 февраля 2026 года (America/New_York)
> **Ссылка:** `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`

---

## 1. Назначение

Этот документ определяет **публичный контракт RAG** для всех агентов и эндпоинтов проекта:

- Response schema (что возвращается клиенту).
- Внутренний контракт (что передаётся между агентами).
- Бюджет рекурсии и латентности.
- Tier-политика доступа.

**Текущее состояние:** канонический `InsightResponse` в
`app/schemas/insight.py:25` уже реализует `provider`, `insight`, `sources[]`,
`confidence`, `rag_used`, `hops`, `latency_ms` и расширенные runtime metadata.
Два скрытых Insight route handler принадлежат `app/routers/legacy_insight.py` и
используют `app/services/insight_compat.py` напрямую; `legacy_app.py` сохраняет
точный alias модели и поддерживаемых callables. Response assembly остаётся в
`app/services/insight_application_service.py`.

### 1.1 Normative vs example; single source of truth

- **Normative (обязательные к реализации):** секции 2 (Response Schema), 3 (RAGContext/RAGChunk), 4 (константы бюджета), 5 (Tier-политика), 6 (AGENT_CORPUS_MAP), 7 (Feedback Schema DDL). Эти элементы — контракт для рантайм-реализации; при расхождении с аудитом или бэклогом приоритет у данного документа.
- **Example / reference:** конкретные значения в таблицах (SLA, Tier), примеры JSON и Python — иллюстративные; канонические значения при реализации брать из `core/rag/` (после появления модулей) или из миграций для DDL.
- **AGENT_CORPUS_MAP и синхронизация с другими мапами:** реализованный source of truth для текущей agent→corpus маршрутизации находится в `core/rag/contracts.py`; реализованная запись `cbt-agent` и target-state остальных agent mappings явно разделены в §6. `AGENT_CONTEXT_MAP` (`docs/orchestration/AGENT_CONTEXT_MAP.md`) остаётся отдельным orchestration-контрактом, а будущая консолидация требует отдельного ADR и обновления этого документа — текущий Insight ownership cutover её не открывает.

---

## 2. Публичный API Response Schema

### 2.1 Insight endpoint (`POST /api/v1/insight`) — реализованный

```jsonc
{
  "provider": "string",
  "insight": "string",
  "sources": [
    {
      "chunk_id": "string",
      "file": "string",
      "preview": "string",
      "score": 0.0
    }
  ],
  "confidence": 0.0,
  "rag_used": true,
  "hops": 1,
  "latency_ms": 0
}
```

**Правила:**

- `sources` возвращается только если `rag_used = true`.
- `confidence` = среднее `score` по топ-N чанкам (при векторном retrieval — cosine similarity).
- `sources[].preview` не должен содержать PII (применяется `redact_rag_context_for_insight`).
- Максимальное число элементов в `sources[]`: `MAX_SOURCES_IN_RESPONSE = 5`.

### 2.2 Ответ при отключённом RAG

```jsonc
{
  "provider": "string",
  "insight": "string",
  "sources": [],
  "confidence": null,
  "rag_used": false,
  "hops": 0,
  "latency_ms": 0
}
```

---

## 3. Внутренний контракт агента

### 3.1 RAGContext (передаётся между агентами)

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RAGChunk:
    chunk_id: str
    file: str
    content: str
    score: float
    hop: int = 1


@dataclass
class RAGContext:
    query: str
    refined_queries: list[str]
    chunks: list[RAGChunk]
    confidence: float
    hops: int
    latency_ms: int
    agent_id: Optional[str] = None
    user_tier: Optional[str] = None
```

### 3.2 Сигнатура retrieve_context (целевая)

Текущая реализация: `core/rag/simple_rag.py:109` — `retrieve_context(query: str, max_chunks: int = 3) -> str`.

Целевая (обратная совместимость через default args):

```python
def retrieve_context(
    query: str,
    max_chunks: int = 3,
    max_hops: int = 1,
    agent_id: str | None = None,
    user_tier: str | None = None,
    subject_id: int | None = None,
) -> RAGContext:
    ...
```

`subject_id` обязателен для любого retrieval из `user_knowledge`. Если `subject_id` отсутствует,
vector path должен fail-closed и перейти на non-personal fallback, не читая персональный corpus.

### 3.3 Mandatory Stage-1 validation boundary

Stage 1 in `core/rag/validation.py` is mandatory for every final request-local
vector result and every final merged recursive result before a chunk can affect
the prompt, sources, confidence, provenance, a verification bundle, or a
knowledge candidate. `FEATURE_PHILOSOPHY_VALIDATION` controls only advisory
Stages 2-4. Those stages receive separate chunk copies and cannot change the
canonical Stage-1 survivor set.

| Stage-1 baseline | Optional Stages 2-4 | User RAG response | Knowledge admission |
|---|---|---|---|
| Exception or no survivors | Not run | `rag_used=false`, `sources=[]`, `confidence=null`; the original non-RAG prompt remains available | Closed |
| Survivors; feature flag off | Not run | Baseline survivors only | Closed |
| Survivors; enrichment completes | Completed | The same baseline survivors plus advisory metadata or warnings | Possible only through all existing canonical policy and verification-bundle gates |
| Survivors; enrichment raises | Rolled back | Untouched baseline survivors | Closed |
| Formatting or redaction produces no usable context | Irrelevant | Existing fail-closed non-RAG result | Closed |

Normative terms are deliberately bounded:

- **valid** means accepted by the current Stage-1 validator version; it does
  not mean proven true or comprehensively safe.
- **all** means every chunk on the finite final request-local vector and merged
  recursive carriers named above; it is not an open-world text-recognition claim.
- **authorized** means Stage-1 survival, observed completion of configured
  enrichment, and every existing verification and policy gate passed for the
  same survivor snapshot.
- **complete** describes only the finite decision table above, not recognition
  of every possible harmful, misleading, or unsupported statement.

Formatting and redaction must finish before the final verification bundle and
knowledge candidates are built. Disabled or failed enrichment may preserve an
available wellness response from baseline survivors, but it cannot authorize
knowledge promotion. After Stage 1, one final request-local hygiene boundary
rejects chunks whose `chunk_id` or `file` is not an exact built-in string, is
blank, exceeds 256 code points, or contains control, format, surrogate,
unassigned/noncharacter, line-separator, or paragraph-separator characters.
Metadata must contain at least one letter, number, punctuation character,
symbol, or assigned private-use character; combining marks and variation
selectors remain allowed when attached to such accepted content. This is a
post-Stage-1 carrier boundary, not a new Stage 0. The resulting sanitized and
redacted snapshot is the only source for the prompt, response chunks and
sources, confidence, evidence references, provenance, verification bundle, and
knowledge candidates.

Runtime warnings use stable codes only. Internal stage metadata may contain
bounded aggregate counts, but neither surface may include raw query or chunk
content, chunk identifiers, file paths, scores, exception messages, or other
request-specific diagnostics. The roadmap
[PDF](https://drive.google.com/file/d/1e7Ij5pV897BTUImocsES26fP0gE0IcxK/view?usp=drivesdk)
is product-intent input only; runtime authority remains with this contract, the
canonical ledger entry, code, and deterministic tests.

### 3.4 Pilot 3B exact-carrier context compaction

`FEATURE_RAG_CONTEXT_COMPACTION` is an optional, default-off request-time
optimization after the mandatory Stage-1 boundary and final metadata,
sanitization, and redaction hygiene. When enabled, it removes only later
carriers whose five primitive fields (`chunk_id`, `file`, `content`, `score`,
`hop`) have the same runtime types and equal values as an earlier carrier. The
first occurrence and request-local order are preserved. Same-content carriers
with any different provenance, score, or hop remain distinct; this is not
content-only, normalized, fuzzy, semantic, or boilerplate deduplication.

The compacted snapshot is the single source for prompt context, response
sources, confidence, evidence references, provenance, verification bundle, and
knowledge candidates. Compaction does not validate truth, corroborate evidence,
or grant admission authority. Existing Stage-1, enrichment-completion,
degraded-path, recursive-path, policy, confidence, and verification-bundle
gates remain mandatory.

If compaction fails, the user response falls back to an untouched copy of the
final validated/hygienic snapshot, `chunks_compacted` remains zero, and the
stable internal warning is `rag_context_compaction_error: internal failure`.
The verification bundle and knowledge admission fail closed through the
existing post-retrieval degraded state. Logs contain fixed text only. The
fallback does not change provider-call count, quota/rate-limit ordering, route
schemas, DTOs, or OpenAPI.

Offline release-gate evidence treats enabled but unattempted compaction as N/A
only for the explicit `RETRIEVAL_EMPTY` and `ALL_CHUNKS_FILTERED` outcomes.
Missing, exception, or fallback reasons are malformed evidence, and an observed
compaction result must have no degraded reason. This classifier reports runtime
evidence; it does not create runtime, verification, or knowledge authority.

This pilot is request-local and is not a semantic cache, persistent memory,
Evidence Graph serving, Stage 0, or a new authority/approval boundary.

---

## 4. Бюджет рекурсии и латентности

### 4.1 Константы (именованные)

```python
MAX_RAG_HOPS: int = 3
MAX_CHUNKS_PER_HOP: int = 5
MAX_SOURCES_IN_RESPONSE: int = 5
RAG_PIPELINE_TIMEOUT_SEC: int = 10
MIN_CHUNK_SCORE: float = 0.1
MAX_CHUNK_SIZE_CHARS: int = 800
```

### 4.2 SLA по латентности

| Режим | Целевая латентность | Максимум |
|-------|---------------------|----------|
| Single-hop (текущий) | ≤ 200 мс | 500 мс |
| Multi-hop (3 hops) | ≤ 1000 мс | 3000 мс |
| Vector + rerank | ≤ 500 мс | 1500 мс |
| Полный пайплайн (RAG + LLM) | ≤ 5000 мс | 10000 мс |

---

## 5. Tier-политика доступа

| Tier | RAG доступен | Max hops | Sources в ответе | Персональный корпус |
|------|---------------|----------|------------------|---------------------|
| FREE | Нет | — | — | Нет |
| PRO | Да (базовый) | 1 | Да (≤3) | Нет |
| VIP | Да (полный) | 3 | Да (≤5) | Да |

---

## 6. Corpus Routing (для доменных агентов)

**Implementation status:** `cbt-agent` corpus filtering is implemented in `core/rag/contracts.py:AGENT_CORPUS_MAP`. Other agent mappings are target-state.

**Evidence:**
- `core/rag/contracts.py:19` — `AGENT_CORPUS_MAP` constant with `cbt-agent` → `["docs/cbt/", "docs/psychology/"]`
- `core/rag/vector_rag.py:86` — `_retrieve_vector_postgres()` corpus filtering via parameterized LIKE
- `core/rag/vector_rag.py:124` — `_retrieve_vector_sqlite()` corpus filtering via parameterized LIKE
- `core/rag/vector_rag.py:181` — `_retrieve_vector_from_db()` resolves `agent_id` → `corpus_prefixes`
- `core/rag/vector_rag.py:201` — vector retrieval fails closed when `subject_id` is missing
- `core/rag/vector_rag.py:317` — public vector path falls back to non-personal Jaccard retrieval when vector path returns no chunks or errors
- `core/rag/simple_rag.py:157` — Jaccard fallback with `startswith` corpus filtering
- `app/routers/cbt_insight.py:134` — PRO-gated endpoint using `agent_id="cbt-agent"`

```python
AGENT_CORPUS_MAP: dict[str, list[str]] = {
    "cbt-agent": ["docs/cbt/", "docs/psychology/"],
    "nutritionist-agent": ["docs/nutrition/", "docs/health/"],
    "philosophy-agent": ["docs/philosophy/", "docs/logic/"],
    "logic-agent": ["docs/logic/", "docs/math/"],
    "bayesian-uq-agent": ["docs/statistics/", "docs/uncertainty/"],
    "rag-systems-agent": ["docs/", "ROOT"],
    "insight-default": ["ROOT", "docs/"],
}
```

---

## 7. Feedback Schema (prerequisite для recursive learning)

```sql
CREATE TABLE rag_feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         BIGINT NOT NULL,
    agent_id        VARCHAR(64),
    query           TEXT NOT NULL,
    retrieved_chunks JSONB,
    llm_response    TEXT,
    user_rating     SMALLINT CHECK (user_rating BETWEEN 1 AND 5),
    user_correction TEXT,
    confidence      FLOAT,
    hops            SMALLINT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_knowledge (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     BIGINT NOT NULL,
    content     TEXT NOT NULL,
    embedding   VECTOR(768),
    source      VARCHAR(256),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE rag_feedback   ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_knowledge ENABLE ROW LEVEL SECURITY;
```

---

## 8. Security Notes

Evidence anchors (audit policy: architecture docs must cite `file:line` or mark target-state):

- `sources[].preview` проходит через `redact_rag_context_for_insight` перед отправкой клиенту. **Evidence:** `core/insight/safety.py:10` (реализация), `app/services/insight_application_service.py:197` and `app/services/insight_application_service.py:205` (response source assembly).
- `user_knowledge` разрешён только при authenticated `subject_id`; если subject context отсутствует, vector retrieval обязан fail-closed и перейти на non-personal fallback. **Evidence:** `core/rag/vector_rag.py:201` (fail-closed on missing `subject_id`), `core/rag/vector_rag.py:317` (fallback to Jaccard on empty/error vector path), `core/rag/orchestration.py:137` and `core/rag/orchestration.py:147` (subject propagation into recursive/vector retrieval), `app/routers/legacy_insight.py:49` and `app/services/insight_compat.py:81-95` (authenticated `/api/v1/insight` derives and forwards `subject_id`), `app/services/insight_compat.py:104-114` (legacy `/insight` omits subject context), `app/routers/cbt_insight.py:176` (PRO CBT endpoint derives and forwards `subject_id`).
- `user_knowledge.embedding` остаётся `VECTOR(768)`, но смена embedding model family требует runtime fence: `RAG_VECTOR_EMBEDDING_MODEL_ACK` должен совпадать с активной моделью после rebuild/reset rows, иначе vector retrieval обязан fail-closed и перейти на Jaccard. **Evidence:** `core/rag/rag_constants.py` (active model and ack env), `core/rag/vector_rag.py` (ack check before provider/DB work).
- `FastEmbedTextEmbeddings._load_model()` intentionally remains lazy and is first reached from `EmbeddingProvider.encode()` inside `retrieve_context_structured(...)`; production vector deployments should pre-populate the FastEmbed/ONNX cache or expect the first acknowledged vector request to pay model download/initialization cost. Provider failures still degrade through the documented Jaccard fallback.
- `user_knowledge` и `rag_feedback` изолированы по bigint `user_id` subject principal через PostgreSQL RLS с transaction-local session context `app.current_user_id`. Этот principal представляет authenticated subject, derived from API key today, и не обязан совпадать с `users.id`; app-layer `user_id` filtering остаётся как defense in depth. **Evidence:** `core/db_rls.py:12` (`app.current_user_id` setting contract), `core/db_rls.py:24` (session-local `set_config` helper), `core/rag/vector_rag.py:219` (RLS context before retrieval), `app/routers/feedback.py:157` (RLS context before insert/commit), `core/compliance/dsar_service.py:36`, `core/compliance/dsar_service.py:108`, `core/compliance/dsar_service.py:143` (RLS context before export/delete helpers), `alembic/versions/202603100101_enable_rag_user_rls.py:29`, `alembic/versions/202603100101_enable_rag_user_rls.py:41` (initial ENABLE/FORCE RLS), `alembic/versions/202603110001_harden_rag_subject_principal_bigint.py:1` (bigint subject hardening).
- `rag_feedback.llm_response` не хранится без редактирования (PII). **Target-state:** при реализации записи в `rag_feedback` применять redaction (тот же `core/insight/safety.py` или отдельный redactor) перед сохранением.
- Rate limit на RAG-эндпоинты (insight) сохраняется. **Evidence:** детерминированные 429-тесты — `tests/test_rate_limit_llm_and_exports_api.py:95-108` (`/api/v1/insight`), `:117-130` (`/insight`); tier-guard — `tests/test_insight_vip_guard_api.py:50-78`.

---

## 9. Next Steps

1. Реализовать `RAGChunk`, `RAGContext` в `core/rag/contracts.py`.
2. Сохранять реализованные `sources[]` и `confidence` синхронными с
   `app/schemas/insight.py` и детерминированными response tests.
3. Добавить integration coverage для live Postgres RLS deny-by-default path.
4. Обновить `retrieve_context` signature с обратной совместимостью (default args).
5. Добавить `rag_constants.py` в `core/rag/`.

---

*Контракт согласован: rag-systems-agent, ai-app-architect, backend-engineer.*
*Ссылка на аудит: `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`*
