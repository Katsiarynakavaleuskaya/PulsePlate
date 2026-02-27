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
) -> RAGContext:
    ...
```

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
    user_id         UUID NOT NULL,
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
    user_id     UUID NOT NULL,
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

- `sources[].preview` проходит через `redact_rag_context_for_insight` перед отправкой клиенту.
- `user_knowledge.embedding` изолирован по `user_id` через RLS.
- `rag_feedback.llm_response` не хранится без редактирования (PII).
- Rate limit на RAG-эндпоинты сохраняется (см. `tests/test_insight_vip_guard_api.py`).

---

## 9. Next Steps

1. Реализовать `RAGChunk`, `RAGContext` в `core/rag/contracts.py`.
2. Добавить `sources[]` и `confidence` в response schema Insight (отдельный PR).
3. Создать миграцию для `rag_feedback` и `user_knowledge`.
4. Обновить `retrieve_context` signature с обратной совместимостью (default args).
5. Добавить `rag_constants.py` в `core/rag/`.

---

*Контракт согласован: rag-systems-agent, ai-app-architect, backend-engineer.*
*Ссылка на аудит: `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`*
