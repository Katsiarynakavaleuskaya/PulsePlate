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

**Текущее состояние:** `InsightResponse` в `legacy_app.py:1174-1183` содержит только `provider` и `insight`. Поля `sources[]`, `confidence`, `rag_used`, `hops`, `latency_ms` — целевые (требуют отдельного PR).

### 1.1 Normative vs example; single source of truth

- **Normative (обязательные к реализации):** секции 2 (Response Schema), 3 (RAGContext/RAGChunk), 4 (константы бюджета), 5 (Tier-политика), 6 (AGENT_CORPUS_MAP), 7 (Feedback Schema DDL). Эти элементы — контракт для рантайм-реализации; при расхождении с аудитом или бэклогом приоритет у данного документа.
- **Example / reference:** конкретные значения в таблицах (SLA, Tier), примеры JSON и Python — иллюстративные; канонические значения при реализации брать из `core/rag/` (после появления модулей) или из миграций для DDL.
- **AGENT_CORPUS_MAP и синхронизация с другими мапами:** в этом документе `AGENT_CORPUS_MAP` задаёт маршрутизацию корпусов по агенту. Концептуально он пересекается с `AGENT_CONTEXT_MAP` (`docs/orchestration/AGENT_CONTEXT_MAP.md`) и планируемым `AGENT_KNOWLEDGE_MAP` (`docs/orchestration/AGENT_KNOWLEDGE_MAP.md` — см. аудит §8.1). **Временный шов (две мапы в разных документах):** exit criteria — единый источник в `core/rag/` (или конфиг) после реализации RAG contract; отслеживание — BACKLOG_LEDGER item «RAG contract implementation» (sources[], confidence, budget) с DoD «консолидировать agent→corpus в один модуль и обновить контракт»; ADR — планируется при реализации (см. `docs/roadmap/BACKLOG_LEDGER.md` entry «RAG contract implementation»). До реализации этот файл — норма; при реализации — ADR на консолидацию и обновление контракта.

---

## 2. Публичный API Response Schema

### 2.1 Insight endpoint (`POST /api/v1/insight`) — целевой

```jsonc
{
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

- `sources[].preview` проходит через `redact_rag_context_for_insight` перед отправкой клиенту. **Evidence:** `core/insight/safety.py:10` (реализация); при добавлении `sources[]` в response — вызывать перед сериализацией (target-state).
- `user_knowledge` разрешён только при authenticated `subject_id`; если subject context отсутствует, vector retrieval обязан fail-closed и перейти на non-personal fallback. **Evidence:** `core/rag/vector_rag.py:201` (fail-closed on missing `subject_id`), `core/rag/vector_rag.py:317` (fallback to Jaccard on empty/error vector path), `core/rag/orchestration.py:137` and `core/rag/orchestration.py:147` (subject propagation into recursive/vector retrieval), `legacy_app.py:2202` and `legacy_app.py:2332` (authenticated `/api/v1/insight` derives and forwards `subject_id`), `legacy_app.py:2274` (legacy `/insight` passes `subject_id=None`), `app/routers/cbt_insight.py:176` (PRO CBT endpoint derives and forwards `subject_id`).
- `user_knowledge` и `rag_feedback` изолированы по bigint `user_id` subject principal через PostgreSQL RLS с transaction-local session context `app.current_user_id`. Этот principal представляет authenticated subject, derived from API key today, и не обязан совпадать с `users.id`; app-layer `user_id` filtering остаётся как defense in depth. **Evidence:** `core/db_rls.py:12` (`app.current_user_id` setting contract), `core/db_rls.py:24` (session-local `set_config` helper), `core/rag/vector_rag.py:219` (RLS context before retrieval), `app/routers/feedback.py:157` (RLS context before insert/commit), `core/compliance/dsar_service.py:36`, `core/compliance/dsar_service.py:108`, `core/compliance/dsar_service.py:143` (RLS context before export/delete helpers), `alembic/versions/202603100001_enable_rag_user_rls.py:29`, `alembic/versions/202603100001_enable_rag_user_rls.py:41` (initial ENABLE/FORCE RLS), `alembic/versions/202603110001_harden_rag_subject_principal_bigint.py:1` (bigint subject hardening).
- `rag_feedback.llm_response` не хранится без редактирования (PII). **Target-state:** при реализации записи в `rag_feedback` применять redaction (тот же `core/insight/safety.py` или отдельный redactor) перед сохранением.
- Rate limit на RAG-эндпоинты (insight) сохраняется. **Evidence:** детерминированные 429-тесты — `tests/test_rate_limit_llm_and_exports_api.py:95-108` (`/api/v1/insight`), `:117-130` (`/insight`); tier-guard — `tests/test_insight_vip_guard_api.py:50-78`.

---

## 9. Next Steps

1. Реализовать `RAGChunk`, `RAGContext` в `core/rag/contracts.py`.
2. Добавить `sources[]` и `confidence` в response schema Insight (отдельный PR).
3. Добавить integration coverage для live Postgres RLS deny-by-default path.
4. Обновить `retrieve_context` signature с обратной совместимостью (default args).
5. Добавить `rag_constants.py` в `core/rag/`.

---

*Контракт согласован: rag-systems-agent, ai-app-architect, backend-engineer.*
*Ссылка на аудит: `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`*
