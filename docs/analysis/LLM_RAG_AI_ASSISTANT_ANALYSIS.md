# 🤖 Детальный анализ LLM провайдеров, RAG и AI ассистента

**Дата:** 2026-01-28
**Рецензент:** AI Assistant (Auto)
**Статус:** Комплексный анализ AI/LLM инфраструктуры и путей развития

---

## 📊 Executive Summary

**Общая оценка AI/LLM инфраструктуры:** 40% (Базовая реализация, требует развития)

**Разбивка:**
- **LLM Providers:** 70% (хорошо реализованы, но не интегрированы)
- **RAG System:** 30% (базовая реализация, нет vector embeddings)
- **AI Assistant:** 20% (только insight endpoint, нет полноценного ассистента)
- **Accuracy/Reliability:** 25% (нет техник повышения достоверности)

**Критические пробелы:**
- ❌ LLM провайдеры не интегрированы в production endpoints (только `/insight`)
- ❌ RAG использует простой keyword matching (нет vector embeddings)
- ❌ Нет техник повышения достоверности (fact-checking, validation, confidence scoring)
- ❌ Нет AI ассистента (только простой insight endpoint)

---

## 🔍 Детальный анализ LLM провайдеров

### Архитектура провайдеров

**Базовый интерфейс:** `ProviderBase` (Protocol)

```python
# providers/__init__.py
class ProviderBase(Protocol):
    name: str
    async def generate(self, text: str) -> str:
        raise NotImplementedError("Provider must implement .generate(text)")
```

**Дизайн:**
- ✅ Protocol-based (structural typing)
- ✅ Минимальный интерфейс: `name` + `generate(text)`
- ✅ Async-first (все провайдеры async)
- ✅ Легко добавлять новые провайдеры

---

### 1. GrokProvider (xAI) — Cloud LLM

**Файл:** `providers/grok.py`

**Реализация:**
- ✅ OpenAI-compatible SDK (`AsyncOpenAI`)
- ✅ Endpoint: `https://api.x.ai/v1` (default, configurable)
- ✅ Model: `grok-4-latest` (default, configurable)
- ✅ API key: из env (`GROK_API_KEY` или `XAI_API_KEY`)
- ✅ Retry logic: 3 попытки с exponential backoff
- ✅ Timeout: 30s (default, configurable)

**Особенности:**
- ✅ Network calls via `httpx` (async)
- ✅ Error handling: оборачивает исключения в `RuntimeError`
- ✅ Fallback: `GrokLiteProvider` (если API key отсутствует)

**Проблемы:**
- ❌ Нет rate limiting (риск abuse; грубая оценка: ~1M req/month × ~2k tokens × $0.03/1k ≈ $60k–72k/month при облачном провайдере; см. цену за 1k tokens у xAI/Grok)
- ❌ Нет cost tracking (невозможно отследить расходы)
- ❌ Нет токен-лимитов (может превысить budget)

**Оценка:** 70% (хорошо реализован, но нет production safeguards)

---

### 2. OllamaProvider (Local) — Self-hosted LLM

**Файл:** `providers/ollama.py`

**Реализация:**
- ✅ Local/self-hosted Ollama server
- ✅ Endpoint: `http://localhost:11434` (default, configurable)
- ✅ Model: `llama3.1:8b` (default, configurable)
- ✅ Timeout: 1.5s (короткий, для быстрых 503 ответов)
- ✅ Retry logic: 3 попытки с exponential backoff
- ✅ Два API метода: `/api/chat` (preferred) + `/api/generate` (fallback)

**Особенности:**
- ✅ Privacy: локальные модели, данные не покидают машину
- ✅ Cost: бесплатно (self-hosted)
- ✅ Fast failure: короткий timeout → быстрый 503 если Ollama недоступен
- ✅ Error handling: network errors → `RuntimeError("ollama_unavailable")`

**Проблемы:**
- ❌ Нет проверки доступности Ollama перед запросом
- ❌ Нет fallback на cloud provider (если Ollama недоступен)
- ❌ Нет мониторинга производительности (latency, throughput)

**Оценка:** 75% (хорошо реализован, но нет production monitoring)

---

### 3. PicoProvider (Ollama-Compatible) — Alternative Local LLM

**Файл:** `providers/pico.py`

**Реализация:**
- ✅ Ollama-compatible provider (альтернатива Ollama)
- ✅ Endpoint: same as Ollama (default: `http://localhost:11434`)
- ✅ Model: same as Ollama (default: `llama3.1:8b`)
- ✅ Timeout: 5.0s (длиннее, чем Ollama)
- ✅ Sync + async fallback (для test compatibility)

**Особенности:**
- ✅ Альтернатива Ollama (если пользователь предпочитает Pico)
- ✅ Тот же API contract как Ollama (легко заменить)
- ✅ Test compatibility (sync client для monkeypatch)

**Проблемы:**
- ❌ Дублирует функциональность OllamaProvider
- ❌ Нет уникальных преимуществ (почти идентичен Ollama)
- ❌ Не используется в production

**Оценка:** 60% (реализован, но дублирует Ollama)

---

### 4. StubProvider (Testing) — Deterministic Mock

**Файл:** `providers/stub.py`

**Реализация:**
- ✅ No network calls
- ✅ Deterministic output: `[stub @ {timestamp}] Insight: {text[:120]}`
- ✅ Synchronous (не async, но compatible)

**Особенности:**
- ✅ Fast tests (нет network)
- ✅ Deterministic (предсказуемый output)
- ✅ No external dependencies

**Оценка:** 100% (отлично для тестирования)

---

### 5. Lite Providers (Fallback) — Offline Fallback

**Файл:** `llm.py`

**Реализация:**
- ✅ `GrokLiteProvider` — lightweight fallback без сети
- ✅ `OllamaLiteProvider` — lightweight fallback без сети
- ✅ Возвращают форматированный текст вместо реальных LLM ответов

**Особенности:**
- ✅ Fail-soft design (graceful degradation)
- ✅ Нет network calls (быстро)
- ✅ Предотвращает network use если API key отсутствует

**Оценка:** 80% (хорошо для fallback, но не для production)

---

### Factory Function: `llm.py`

**Файл:** `llm.py` (root level)

**Реализация:**
- ✅ Lazy imports (fail-soft если provider unavailable)
- ✅ Env-based selection (`LLM_PROVIDER`)
- ✅ Fallback to lite providers (если real provider unavailable)
- ✅ Error handling (try/except для provider initialization)

**Проблемы:**
- ❌ Нет валидации provider configuration
- ❌ Нет health checks (проверка доступности provider)
- ❌ Нет caching (каждый вызов создает новый provider instance)

**Оценка:** 65% (базовая реализация, требует улучшений)

---

## 🔍 Детальный анализ RAG системы

### Текущая реализация: Simple RAG

**Файл:** `core/rag/simple_rag.py`

**Реализация:**
- ✅ Индексирует локальные `.md` файлы
- ✅ Keyword-based retrieval (Jaccard similarity)
- ✅ Chunking по параграфам (max 800 chars)
- ✅ Top-k retrieval (max 3 chunks)
- ✅ Без внешних зависимостей (no vector DB, no embeddings)

**Алгоритм:**
```python
def _score(query: str, text: str) -> float:
    # Simple Jaccard on word sets
    q = set(_tokenize(query))
    t = set(_tokenize(text))
    union = q | t
    base = len(q & t) / len(union) if union else 0.0
    if query.lower() in text.lower():
        base += 0.1  # Bonus for exact substring
    return base
```

**Проблемы:**
- ❌ **Нет vector embeddings** → низкое качество retrieval
- ❌ **Нет semantic search** → только keyword matching
- ❌ **Нет reranking** → топ-k может быть нерелевантным
- ❌ **Нет query expansion** → не находит синонимы
- ❌ **Нет metadata filtering** → не фильтрует по категориям
- ❌ **Нет citation tracking** → источники не отслеживаются

**Оценка:** 30% (базовая реализация, требует модернизации)

---

### Интеграция RAG в Insight Endpoint

**Файл:** `legacy_app.py:2282-2292`

**Реализация:**
```python
use_rag = str(os.getenv("FEATURE_RAG", "")).strip().lower() in {"1", "true", "on", "yes"}
if use_rag:
    with suppress(Exception):
        from core.rag.simple_rag import retrieve_context as _rag_retrieve
        if ctx := _rag_retrieve(prompt_input, max_chunks=3):
            prompt_text = _build_insight_prompt(
                prompt_input,
                _redact_rag_context_for_insight(ctx),
            )
```

**Особенности:**
- ✅ Feature flag (`FEATURE_RAG`)
- ✅ Graceful degradation (suppress exceptions)
- ✅ Context redaction (удаляет source headers)

**Проблемы:**
- ❌ RAG context может быть нерелевантным (keyword matching)
- ❌ Нет валидации качества retrieval (score threshold)
- ❌ Нет fallback если RAG не находит контекст

**Оценка:** 40% (базовая интеграция, требует улучшений)

---

## 🔍 Детальный анализ AI Insight Endpoint

### Endpoint: `/api/v1/insight`

**Файл:** `legacy_app.py:2256-2301`

**Реализация:**
- ✅ POST endpoint с API key dependency
- ✅ Feature flag (`FEATURE_INSIGHT`)
- ✅ RAG integration (optional, via `FEATURE_RAG`)
- ✅ Error handling (503 если provider unavailable)
- ✅ Privacy-safe error messages (не утечкает exception details)

**Проблемы:**
- ❌ **Нет rate limiting** → потенциальный $72k/month abuse
- ❌ **Нет cost tracking** → невозможно отследить расходы
- ❌ **Нет input validation** → может принять любой текст
- ❌ **Нет output validation** → может вернуть вредный контент
- ❌ **Нет fact-checking** → может галлюцинировать
- ❌ **Нет confidence scoring** → невозможно оценить достоверность

**Оценка:** 35% (базовая реализация, требует production safeguards)

---

### Prompt Engineering

**Файл:** `legacy_app.py:2219-2231`

**Текущий prompt:**
```python
def _build_insight_prompt(text: str, context: Optional[str]) -> str:
    if not context:
        return text
    prefix = "Context:\n"
    suffix = f"\n\nQuestion: {text}\nAnswer:"
    return f"{prefix}{context}{suffix}"
```

**Проблемы:**
- ❌ **Нет system prompt** → LLM не знает свою роль
- ❌ **Нет few-shot examples** → нет примеров хороших ответов
- ❌ **Нет role-based prompts** → не указывает "You are a nutrition expert"
- ❌ **Нет constraints** → не ограничивает домен (может давать медицинские советы)
- ❌ **Нет output format** → не требует структурированного ответа

**Оценка:** 25% (очень базовая, требует улучшений)

---

## 🎯 Пути реализации AI ассистента

### Текущее состояние

**Что есть:**
- ✅ LLM провайдеры (grok, ollama, pico, stub)
- ✅ RAG система (базовая, keyword-based)
- ✅ Insight endpoint (`/api/v1/insight`)

**Чего нет:**
- ❌ Полноценный AI ассистент
- ❌ Multi-turn conversation
- ❌ Context memory
- ❌ Tool use (function calling)
- ❌ Structured outputs
- ❌ Domain-specific knowledge

---

### Path 1: Улучшение Insight Endpoint (P0 — Immediate)

**Цель:** Сделать `/api/v1/insight` production-ready

**Задачи:**

1. **Rate Limiting (CRITICAL)**
   - Добавить `slowapi` rate limiting (10 req/hour для FREE, 50 req/hour для PRO, 100 req/hour для VIP)
   - Использовать fingerprinting для rate limiting (вместо IP)
   - Добавить cost tracking (token usage, API calls)

2. **Prompt Engineering**
   - Добавить system prompt: "You are a nutrition expert assistant for PulsePlate..."
   - Добавить few-shot examples (3-5 примеров хороших ответов)
   - Добавить role-based constraints: "Do not provide medical diagnosis..."
   - Добавить output format: "Provide structured response with: summary, recommendations, sources"

3. **Input/Output Validation**
   - Валидация input (max length, content filtering)
   - Валидация output (content filtering, toxicity detection)
   - Sanitization (удаление вредного контента)

4. **Error Handling**
   - Graceful degradation (fallback responses)
   - Retry logic (exponential backoff)
   - Health checks (provider availability)

**Время:** 1-2 недели
**Приоритет:** P0 (CRITICAL)

---

### Path 2: Модернизация RAG (P1 — High Priority)

**Цель:** Улучшить качество retrieval

**Задачи:**

1. **Vector Embeddings**
   - Интеграция sentence-transformers (например, `all-MiniLM-L6-v2`)
   - Генерация embeddings для всех документов
   - Хранение embeddings в vector DB (Chroma, Qdrant, или in-memory для начала)

2. **Hybrid Search**
   - Combine dense (vector) + sparse (BM25/keyword) retrieval
   - Weighted scoring (70% vector, 30% keyword)
   - Query expansion (синонимы, related terms)

3. **Reranking**
   - Cross-encoder reranking (например, `ms-marco-MiniLM`)
   - Rerank top-20 → top-3
   - Улучшает precision

4. **Metadata Filtering**
   - Фильтрация по категориям (nutrition, BMI, meal planning)
   - Фильтрация по языку (RU/EN/ES)
   - Фильтрация по tier (FREE/PRO/VIP)

5. **Citation Tracking**
   - Связь retrieved chunks с источниками
   - Отображение источников в ответе
   - Верификация источников

**Время:** 2-3 недели
**Приоритет:** P1 (HIGH)

---

### Path 3: Полноценный AI ассистент (P1 — High Priority)

**Цель:** Создать multi-turn conversation AI ассистента

**Задачи:**

1. **Conversation Management**
   - Context memory (хранить историю диалога)
   - Session management (уникальный session ID)
   - Context window optimization (summarize old messages)

2. **Tool Use (Function Calling)**
   - Интеграция с BMI calculator (`calculate_bmi`)
   - Интеграция с nutrition targets (`get_nutrition_targets`)
   - Интеграция с meal planning (`generate_weekly_plan`)
   - Structured outputs (JSON schema для tool calls)

3. **Domain-Specific Knowledge**
   - Knowledge base (nutrition facts, BMI guidelines, meal planning rules)
   - Integration с `core/bmi/`, `core/nutrition/`, `core/meal_planner/`
   - Fact-checking against canonical sources

4. **Multi-Agent System (Optional)**
   - Specialist agents (nutrition expert, meal planner, health analyzer)
   - Orchestration (supervisor pattern)
   - Tool routing (какой agent вызывает какой tool)

**Время:** 4-6 недель
**Приоритет:** P1 (HIGH)

---

### Path 4: Accuracy & Reliability Improvements (P0 — Critical)

**Цель:** Повысить достоверность и точность суждений AI

**Задачи:**

1. **Fact-Checking**
   - Cross-check against authoritative sources (USDA, WHO, NASM/ACSM)
   - Validation against canonical modules (`core/bmi/`, `core/nutrition/`)
   - Reject responses that contradict authoritative sources

2. **Confidence Scoring**
   - LLM confidence scores (если поддерживается)
   - RAG retrieval scores (relevance score)
   - Combined confidence (weighted average)
   - Filter low-confidence responses (< 0.7)

3. **Structured Outputs**
   - JSON schema для ответов
   - Validation against schema
   - Reject malformed responses

4. **Guardrails**
   - Domain filtering (reject queries outside nutrition/wellness)
   - Medical diagnosis blocking ("I cannot provide medical diagnosis...")
   - Toxicity detection (filter harmful content)
   - PII detection (redact personal information)

5. **Validation Pipeline**
   - Pre-generation validation (input checks)
   - Post-generation validation (output checks)
   - Fact verification (cross-check against sources)
   - Confidence threshold (reject if confidence < threshold)

**Время:** 2-3 недели
**Приоритет:** P0 (CRITICAL)

---

## 🔬 Технические решения для повышения достоверности (кроме RAG)

### 1. Fact-Checking System

**Проблема:** LLM может галлюцинировать факты

**Решение:**

```python
# core/insight/fact_checker.py
class FactChecker:
    """Проверяет факты в LLM ответах против authoritative sources."""

    def __init__(self):
        self.sources = {
            "bmi": BMICanonicalSource(),  # core/bmi/engine.py
            "nutrition": NutritionCanonicalSource(),  # core/nutrition/
            "sports": SportsNutritionSource(),  # core/sports_nutrition.py
        }

    def verify(self, claim: str, domain: str) -> FactCheckResult:
        """Проверяет утверждение против canonical source."""
        source = self.sources.get(domain)
        if not source:
            return FactCheckResult(verified=False, confidence=0.0)

        # Extract facts from claim (NLP parsing)
        facts = self._extract_facts(claim)

        # Check against source
        verified = []
        for fact in facts:
            is_valid = source.validate(fact)
            verified.append(is_valid)

        confidence = sum(verified) / len(verified) if verified else 0.0
        return FactCheckResult(
            verified=all(verified),
            confidence=confidence,
            source=domain
        )
```

**Интеграция:**
- Pre-generation: проверка input на противоречия
- Post-generation: проверка output на факты
- Reject если confidence < 0.7

**Оценка:** P0 (CRITICAL) — предотвращает галлюцинации

---

### 2. Confidence Scoring System

**Проблема:** Невозможно оценить достоверность ответа

**Решение:**

```python
# core/insight/confidence.py
class ConfidenceScorer:
    """Оценивает достоверность LLM ответов."""

    def score(self, response: str, context: Optional[str] = None) -> float:
        """Возвращает confidence score (0.0-1.0)."""
        scores = []

        # 1. RAG retrieval score (если использовался RAG)
        if context:
            rag_score = self._rag_relevance_score(context)
            scores.append(("rag", rag_score, 0.3))  # 30% weight

        # 2. Fact-checking score
        fact_score = self._fact_check_score(response)
        scores.append(("fact", fact_score, 0.4))  # 40% weight

        # 3. Source citation score
        citation_score = self._citation_score(response)
        scores.append(("citation", citation_score, 0.2))  # 20% weight

        # 4. Response quality score (length, structure, coherence)
        quality_score = self._quality_score(response)
        scores.append(("quality", quality_score, 0.1))  # 10% weight

        # Weighted average
        total = sum(score * weight for _, score, weight in scores)
        return min(1.0, max(0.0, total))
```

**Интеграция:**
- Добавить confidence score в response
- Filter responses с confidence < 0.7
- Показывать confidence пользователю (опционально)

**Оценка:** P0 (CRITICAL) — позволяет оценить достоверность

---

### 3. Structured Outputs with Validation

**Проблема:** LLM может вернуть неструктурированный или невалидный ответ

**Решение:**

```python
# core/insight/structured_output.py
from pydantic import BaseModel, Field

class InsightResponse(BaseModel):
    """Структурированный ответ AI ассистента."""
    summary: str = Field(..., min_length=10, max_length=500)
    recommendations: list[str] = Field(..., min_items=1, max_items=5)
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    domain: str = Field(..., pattern="^(bmi|nutrition|meal_planning|sports)$")

async def generate_structured_insight(
    provider: ProviderBase,
    prompt: str,
    response_schema: type[BaseModel]
) -> InsightResponse:
    """Генерирует структурированный ответ с валидацией."""
    # Add JSON schema to prompt
    schema_prompt = f"""
    {prompt}

    Respond in JSON format matching this schema:
    {response_schema.model_json_schema()}
    """

    response = await provider.generate(schema_prompt)

    # Parse and validate
    try:
        data = json.loads(response)
        return response_schema.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        # Fallback: try to extract structured data from text
        return _extract_structured_data(response, response_schema)
```

**Интеграция:**
- Использовать structured outputs для всех AI endpoints
- Validation против Pydantic schema
- Fallback на extraction если JSON parsing fails

**Оценка:** P1 (HIGH) — улучшает качество ответов

---

### 4. Guardrails System

**Проблема:** LLM может давать вредные или нерелевантные ответы

**Решение:**

```python
# core/insight/guardrails.py
class Guardrails:
    """Защитные механизмы для AI ответов."""

    FORBIDDEN_DOMAINS = {
        "medical_diagnosis",
        "prescription_drugs",
        "surgery",
        "mental_health_diagnosis",
    }

    def check_input(self, query: str) -> GuardrailResult:
        """Проверяет input на запрещенные домены."""
        # Detect domain
        domain = self._classify_domain(query)

        if domain in self.FORBIDDEN_DOMAINS:
            return GuardrailResult(
                allowed=False,
                reason=f"Query is about {domain}, which is outside our domain."
            )

        return GuardrailResult(allowed=True)

    def check_output(self, response: str) -> GuardrailResult:
        """Проверяет output на токсичность и вредный контент."""
        # Toxicity detection (можно использовать библиотеку типа `detoxify`)
        toxicity_score = self._detect_toxicity(response)
        if toxicity_score > 0.7:
            return GuardrailResult(
                allowed=False,
                reason="Response contains toxic content."
            )

        # PII detection
        pii_detected = self._detect_pii(response)
        if pii_detected:
            return GuardrailResult(
                allowed=False,
                reason="Response contains personal information."
            )

        return GuardrailResult(allowed=True)
```

**Интеграция:**
- Pre-generation: проверка input
- Post-generation: проверка output
- Reject если guardrails fail

**Оценка:** P0 (CRITICAL) — предотвращает вредный контент

---

### 5. Multi-Step Validation Pipeline

**Проблема:** Нужна комплексная валидация на всех этапах

**Решение:**

```python
# core/insight/validation_pipeline.py
class ValidationPipeline:
    """Многоэтапная валидация AI ответов."""

    def validate(self, query: str, response: str, context: Optional[str] = None) -> ValidationResult:
        """Выполняет полную валидацию."""
        results = []

        # Step 1: Input validation
        input_result = self._validate_input(query)
        results.append(("input", input_result))
        if not input_result.valid:
            return ValidationResult(valid=False, stage="input", reason=input_result.reason)

        # Step 2: Guardrails
        guardrail_result = self._guardrails.check_input(query)
        results.append(("guardrails_input", guardrail_result))
        if not guardrail_result.allowed:
            return ValidationResult(valid=False, stage="guardrails_input", reason=guardrail_result.reason)

        # Step 3: Generation (LLM call)
        # ... (happens here)

        # Step 4: Output validation
        output_result = self._validate_output(response)
        results.append(("output", output_result))
        if not output_result.valid:
            return ValidationResult(valid=False, stage="output", reason=output_result.reason)

        # Step 5: Guardrails (output)
        guardrail_output = self._guardrails.check_output(response)
        results.append(("guardrails_output", guardrail_output))
        if not guardrail_output.allowed:
            return ValidationResult(valid=False, stage="guardrails_output", reason=guardrail_output.reason)

        # Step 6: Fact-checking
        fact_result = self._fact_checker.verify(response, domain="nutrition")
        results.append(("fact_check", fact_result))
        if fact_result.confidence < 0.7:
            return ValidationResult(valid=False, stage="fact_check", reason="Low confidence")

        # Step 7: Confidence scoring
        confidence = self._confidence_scorer.score(response, context)
        results.append(("confidence", confidence))
        if confidence < 0.7:
            return ValidationResult(valid=False, stage="confidence", reason="Low confidence")

        return ValidationResult(valid=True, confidence=confidence, results=results)
```

**Интеграция:**
- Выполнять pipeline для каждого AI ответа
- Reject если любой этап fails
- Log результаты для мониторинга

**Оценка:** P0 (CRITICAL) — комплексная валидация

---

### 6. Knowledge Graph Integration

**Проблема:** LLM не имеет доступа к структурированным знаниям

**Решение:**

```python
# core/insight/knowledge_graph.py
class NutritionKnowledgeGraph:
    """Knowledge graph для nutrition domain."""

    def __init__(self):
        self.entities = {
            "foods": {},  # food_id -> FoodEntity
            "nutrients": {},  # nutrient_id -> NutrientEntity
            "health_conditions": {},  # condition_id -> ConditionEntity
        }
        self.relations = {
            "contains": [],  # (food_id, nutrient_id, amount)
            "beneficial_for": [],  # (nutrient_id, condition_id)
            "contraindicated_for": [],  # (food_id, condition_id)
        }

    def query(self, query: str) -> list[Fact]:
        """Query knowledge graph для релевантных фактов."""
        # Parse query (NLP)
        entities = self._extract_entities(query)
        relations = self._extract_relations(query)

        # Traverse graph
        facts = []
        for entity in entities:
            related = self._get_related_entities(entity, relations)
            facts.extend(related)

        return facts
```

**Интеграция:**
- Использовать knowledge graph для fact-checking
- Добавлять facts в RAG context
- Валидировать LLM ответы против knowledge graph

**Оценка:** P2 (MEDIUM) — долгосрочное улучшение

---

### 7. Chain-of-Thought (CoT) Prompting

**Проблема:** LLM может делать ошибки в reasoning

**Решение:**

```python
# core/insight/prompts.py
SYSTEM_PROMPT = """
You are a nutrition expert assistant for PulsePlate.

Your role:
- Provide accurate, evidence-based nutrition advice
- Use WHO, NASM/ACSM guidelines
- Do not provide medical diagnosis
- Cite sources when possible

Reasoning process:
1. Understand the question
2. Identify relevant nutrition facts
3. Apply appropriate guidelines
4. Provide structured answer with sources
"""

FEW_SHOT_EXAMPLES = """
Example 1:
Q: "How much protein do I need?"
A: "According to WHO guidelines, adults need 0.8-1.0g protein per kg body weight. For a 70kg person, that's 56-70g daily. For athletes, NASM recommends 1.2-2.2g/kg depending on sport type."

Example 2:
Q: "What foods are high in iron?"
A: "Iron-rich foods include: red meat (2.5mg/100g), spinach (2.7mg/100g), lentils (3.3mg/100g). Pair with vitamin C for better absorption."
"""
```

**Интеграция:**
- Добавить system prompt в `_build_insight_prompt`
- Добавить few-shot examples
- Требовать step-by-step reasoning

**Оценка:** P1 (HIGH) — улучшает reasoning

---

### 8. Response Post-Processing

**Проблема:** LLM ответы могут быть неструктурированными или содержать ошибки

**Решение:**

```python
# core/insight/post_process.py
class ResponsePostProcessor:
    """Пост-обработка LLM ответов."""

    def process(self, response: str) -> str:
        """Обрабатывает ответ для улучшения качества."""
        # 1. Remove hallucinations (проверка против sources)
        response = self._remove_hallucinations(response)

        # 2. Add citations (если использовался RAG)
        response = self._add_citations(response)

        # 3. Format structure (если требуется)
        response = self._format_structure(response)

        # 4. Validate facts (cross-check)
        response = self._validate_facts(response)

        return response

    def _remove_hallucinations(self, text: str) -> str:
        """Удаляет утверждения, которые не подтверждены sources."""
        sentences = text.split(". ")
        verified = []
        for sentence in sentences:
            if self._fact_checker.verify(sentence, domain="nutrition").verified:
                verified.append(sentence)
        return ". ".join(verified)
```

**Интеграция:**
- Применять post-processing ко всем AI ответам
- Улучшает качество без изменения LLM

**Оценка:** P1 (HIGH) — улучшает качество ответов

---

## 📊 Матрица соответствия документам анализа

### Соответствие `docs/analysis/FINAL_ASSESSMENT_REVIEW.md`

**Упоминается:**
- "LLM integration — Wire providers into VIP features (already implemented, not connected)" → ✅ **ПОДТВЕРЖДЕНО**
- "LLM cost control — No rate limiting on /api/v1/vip/insight (potential $72k/month abuse)" → ✅ **ПОДТВЕРЖДЕНО**

**Статус:**
- LLM провайдеры реализованы, но не интегрированы в production endpoints
- Insight endpoint существует, но нет rate limiting

---

### Соответствие `docs/analysis/CORE_MODULES_ANALYSIS_REVIEW.md`

**Упоминается:**
- "Bayesian Adherence Domain" → ⚠️ **НЕ УПОМИНАЕТСЯ** в контексте AI
- "BMI Engine" → ⚠️ **НЕ УПОМИНАЕТСЯ** в контексте AI integration

**Статус:**
- AI ассистент не интегрирован с Bayesian Adherence
- AI ассистент не интегрирован с BMI Engine

---

### Соответствие `docs/audit/AUDIT_GAPS_ANALYSIS.md`

**Упоминается:**
- "LLM cost control ($72k/month potential abuse)" → ✅ **ПОДТВЕРЖДЕНО**
- "LLM integration — Wire providers into VIP features" → ✅ **ПОДТВЕРЖДЕНО**

**Статус:**
- Критические gaps идентифицированы правильно
- Требуется rate limiting и cost tracking

---

## 🎯 Критические рекомендации

### P0 — Critical (Blocking Production)

1. **Rate Limiting для LLM endpoints**
   - Добавить `slowapi` rate limiting (10 req/hour для FREE, 50 req/hour для PRO, 100 req/hour для VIP)
   - Использовать fingerprinting для rate limiting
   - Добавить cost tracking (token usage, API calls)

2. **Fact-Checking System**
   - Cross-check против authoritative sources (USDA, WHO, NASM/ACSM)
   - Validation против canonical modules (`core/bmi/`, `core/nutrition/`)
   - Reject responses с confidence < 0.7

3. **Guardrails System**
   - Domain filtering (reject queries outside nutrition/wellness)
   - Medical diagnosis blocking
   - Toxicity detection
   - PII detection

4. **Confidence Scoring**
   - Оценка достоверности ответов
   - Filter low-confidence responses
   - Показывать confidence пользователю (опционально)

### P1 — High Priority

5. **Модернизация RAG**
   - Vector embeddings (sentence-transformers)
   - Hybrid search (dense + sparse)
   - Reranking (cross-encoder)
   - Citation tracking

6. **Structured Outputs**
   - JSON schema для ответов
   - Validation против schema
   - Fallback на extraction

7. **Prompt Engineering**
   - System prompt
   - Few-shot examples
   - Role-based constraints
   - Chain-of-Thought prompting

8. **Response Post-Processing**
   - Remove hallucinations
   - Add citations
   - Format structure
   - Validate facts

### P2 — Medium Priority

9. **Knowledge Graph**
   - Entities (foods, nutrients, health conditions)
   - Relations (contains, beneficial_for, contraindicated_for)
   - Query interface

10. **Multi-Agent System**
    - Specialist agents (nutrition expert, meal planner, health analyzer)
    - Orchestration (supervisor pattern)
    - Tool routing

---

## 📋 Сводная таблица пробелов

| Категория | Текущее состояние | Целевое состояние | Статус |
|-----------|-------------------|-------------------|--------|
| **LLM Providers** | ✅ Реализованы | ⚠️ Не интегрированы | 70% |
| **RAG System** | ⚠️ Keyword-based | ❌ Vector embeddings | 30% |
| **AI Assistant** | ⚠️ Только insight | ❌ Полноценный ассистент | 20% |
| **Rate Limiting** | ❌ Нет | ✅ Требуется | 0% |
| **Fact-Checking** | ❌ Нет | ✅ Требуется | 0% |
| **Confidence Scoring** | ❌ Нет | ✅ Требуется | 0% |
| **Guardrails** | ❌ Нет | ✅ Требуется | 0% |
| **Structured Outputs** | ❌ Нет | ✅ Требуется | 0% |

**Общая оценка:** 40% (Базовая реализация, требует развития)

---

## 🔗 Связь с документами анализа

### Соответствие `docs/analysis/FINAL_ASSESSMENT_REVIEW.md`

**Упоминается:**
- "LLM integration — Wire providers into VIP features" → ✅ **ПОДТВЕРЖДЕНО** (провайдеры не интегрированы)
- "LLM cost control — No rate limiting" → ✅ **ПОДТВЕРЖДЕНО** (нет rate limiting)

### Соответствие `docs/audit/AUDIT_GAPS_ANALYSIS.md`

**Упоминается:**
- "LLM cost control ($72k/month potential abuse)" → ✅ **ПОДТВЕРЖДЕНО** (критический gap)
- "LLM integration" → ✅ **ПОДТВЕРЖДЕНО** (не интегрировано)

---

## 📊 Соответствие BACKLOG_LEDGER.md

### ✅ Уже в BACKLOG:

1. **LLM rate limiting (CRITICAL — $72k/month potential abuse)** — ✅ Записано
2. **Wire LLM providers into VIP features** — ✅ Записано

### ❌ НЕ в BACKLOG (требует добавления):

1. **Модернизация RAG (vector embeddings, hybrid search)** — ❌ НЕ записано
2. **Fact-checking system** — ❌ НЕ записано
3. **Confidence scoring system** — ❌ НЕ записано
4. **Guardrails system** — ❌ НЕ записано
5. **Structured outputs** — ❌ НЕ записано
6. **Prompt engineering improvements** — ❌ НЕ записано
7. **Response post-processing** — ❌ НЕ записано
8. **Knowledge graph integration** — ❌ НЕ записано
9. **Multi-agent system** — ❌ НЕ записано

**Рекомендация:** Добавить все P0 и P1 задачи в BACKLOG_LEDGER.md немедленно.

---

## 🎯 Приоритетные действия

### Immediate Actions (This Week):

1. **P0 CRITICAL:**
   - Добавить rate limiting для LLM endpoints
   - Реализовать fact-checking system
   - Реализовать guardrails system
   - Реализовать confidence scoring

2. **P1 HIGH:**
   - Модернизировать RAG (vector embeddings)
   - Улучшить prompt engineering
   - Добавить structured outputs
   - Реализовать response post-processing

### Short-Term (Next Month):

3. **P1 MEDIUM:**
   - Интегрировать knowledge graph
   - Реализовать multi-agent system
   - Добавить tool use (function calling)
   - Реализовать conversation management

---

## 📚 Связанные документы

- `docs/architecture/providers_implementation.md` — providers implementation
- `docs/audit/AUDIT_GAPS_ANALYSIS.md` — audit gaps
- `docs/analysis/FINAL_ASSESSMENT_REVIEW.md` — final assessment
- `docs/roadmap/BACKLOG_LEDGER.md` — backlog
- `providers/AGENTS.md` — provider rules
- `.cursor/agents/ai-innovation-specialist.md` — AI innovation guide

---

**Последнее обновление:** 2026-01-28
**Версия:** 1.0
