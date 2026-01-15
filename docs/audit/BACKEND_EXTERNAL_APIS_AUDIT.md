# Backend External APIs & Product Base Audit

**Date:** 2026-01-15
**Scope:** External API integrations, providers, error handling, and product database
**Purpose:** Assess external API integration quality and product base implementation

---

## 📊 Summary

**External API Providers:** 5
**Food Database APIs:** 2 (USDA, OpenFoodFacts)
**LLM Providers:** 3 (Ollama, Grok, Pico)
**Product Base Status:** Stub implementations (by design)

---

## 🌐 External API Providers

### 1. Food Database APIs

#### USDA FoodData Central (`core/food_apis/usda_client.py`)

**Status:** ✅ **Fully Implemented**

**Features:**
- Search foods by name
- Get detailed nutrition information
- Nutrient mapping (USDA IDs → standard names)
- Async HTTP client (httpx)
- Error handling with logging

**API Details:**
- Base URL: `https://api.nal.usda.gov/fdc/v1`
- API Key: Required (uses DEMO_KEY as fallback)
- Rate limits: Not explicitly documented, but reasonable delays implemented

**Error Handling:**
- Network errors logged
- Test runtime detection (blocks external HTTP in tests)
- Graceful degradation

**File:** `core/food_apis/usda_client.py:96-442`

---

#### Open Food Facts (`core/food_apis/openfoodfacts_client.py`)

**Status:** ✅ **Fully Implemented**

**Features:**
- Search products by name/barcode
- Get product information (nutrition, ingredients, packaging)
- Nutrient mapping (OFF names → standard names)
- Async HTTP client (httpx)
- Error handling with logging

**API Details:**
- Base URL: `https://world.openfoodfacts.org/api/v2`
- Rate limits: 100 requests/minute (anonymous), higher for API accounts
- Data License: Open Database License (ODbL)

**Error Handling:**
- Network errors logged
- Test runtime detection (blocks external HTTP in tests)
- Availability flag (`OFF_AVAILABLE`) for testing

**File:** `core/food_apis/openfoodfacts_client.py:102-380`

---

#### Unified Food Database (`core/food_apis/unified_db.py`)

**Status:** ✅ **Fully Implemented**

**Features:**
- Unified interface for multiple food databases
- Caching (memory + file cache)
- Source preference (USDA vs OpenFoodFacts)
- Fallback strategy (USDA → OFF)

**Implementation:**
- `UnifiedFoodItem` dataclass
- `UnifiedFoodDatabase` class
- Cache management (save/load)
- Error handling with fallbacks

**File:** `core/food_apis/unified_db.py:138-266`

---

### 2. LLM Providers

#### Ollama Provider (`providers/ollama.py`)

**Status:** ✅ **Fully Implemented**

**Features:**
- Local Ollama integration
- Short timeouts (1.5s default, configurable)
- Retry logic (3 attempts, exponential backoff)
- Error conversion (network errors → RuntimeError)
- Fallback strategies (chat → generate)

**API Details:**
- Base URL: `http://localhost:11434` (default)
- Model: `llama3.1:8b` (default)
- Timeout: 1.5s (configurable via `OLLAMA_TIMEOUT` env var)

**Error Handling:**
- Converts network errors to `RuntimeError("ollama_unavailable")`
- Allows `/insight` endpoint to return 503 quickly
- Retry with exponential backoff

**File:** `providers/ollama.py:11-98`

---

#### Grok Provider (`providers/grok.py`)

**Status:** ✅ **Fully Implemented**

**Features:**
- x.ai Grok integration via OpenAI-compatible SDK
- Async client (AsyncOpenAI)
- Retry logic (3 attempts, exponential backoff)
- Error conversion (network errors → RuntimeError)

**API Details:**
- Endpoint: Configurable (x.ai endpoint)
- Model: Configurable
- Timeout: 30s (default, configurable)

**Error Handling:**
- Retry with exponential backoff
- Converts errors to `RuntimeError("Grok error: ...")`

**File:** `providers/grok.py:7-41`

---

#### Pico Provider (`providers/pico.py`)

**Status:** ✅ **Fully Implemented**

**Features:**
- Pico LLM integration (Ollama REST compatible)
- Sync and async client support
- Fallback strategies (sync → async)
- Error conversion (network errors → RuntimeError)

**API Details:**
- Base URL: Configurable (defaults to Ollama port)
- Model: Configurable
- Timeout: Configurable

**Error Handling:**
- Tries sync client first, falls back to async
- Converts errors to `RuntimeError("Pico error: ...")`

**File:** `providers/pico.py:11-68`

---

### 3. Product Base (Catalog System)

**Status:** ⚠️ **Stub Implementations Only**

**Modules:**
- `core/catalog/sources/off_stub.py` — Open Food Facts stub
- `core/catalog/sources/carrefour_stub.py` — Carrefour stub
- `core/catalog/sources/walmart_stub.py` — Walmart stub

**Current State:**
- All sources are offline stubs
- Deterministic test data only
- No real network calls

**Comment:**
```python
"""
This package intentionally contains only deterministic, offline stubs for now.
No real provider integrations or network calls should live here yet.
"""
```

**Impact:** Low (by design)
- Catalog system is intentionally stubbed
- Real integrations planned for future

**Files:**
- `core/catalog/__init__.py:3-5`
- `core/catalog/sources/*.py`

---

## 🔧 Error Handling Patterns

### 1. Network Error Handling

**Pattern:** Convert network errors to `RuntimeError` for fast 503 responses

**Example:**
```python
except (httpx.RequestError, httpx.HTTPStatusError, httpx.TimeoutException) as e:
    raise RuntimeError("ollama_unavailable") from e
```

**Files:**
- `providers/ollama.py:93-95`
- `providers/grok.py:39-41`
- `providers/pico.py:67-68`

---

### 2. Test Runtime Detection

**Pattern:** Block external HTTP calls in tests

**Implementation:**
```python
from ._testing import is_test_runtime

if is_test_runtime():
    logger.info("External HTTP blocked in tests: %s", context)
    return
```

**Files:**
- `core/food_apis/usda_client.py:28-32`
- `core/food_apis/openfoodfacts_client.py` (similar pattern)

---

### 3. Retry Logic

**Pattern:** Exponential backoff with retry

**Example:**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(RuntimeError),
    reraise=True,
)
async def generate(self, text: str) -> str:
    # ...
```

**Files:**
- `providers/ollama.py:76-81`
- `providers/grok.py:24-29`

---

## 📋 Provider Interface

### ProviderBase Protocol

**File:** `providers/__init__.py:6-14`

**Interface:**
```python
class ProviderBase(Protocol):
    name: str
    async def generate(self, text: str) -> str: ...
```

**Implemented by:**
- `OllamaProvider`
- `GrokProvider`
- `PicoProvider`
- `StubProvider` (for testing)

---

## 🎯 Recommendations

### P0 (Critical)

**None** — All external APIs are properly implemented with error handling.

### P1 (High Priority)

1. **Document catalog stub strategy**
   - When will real integrations be added?
   - Keep stubs for testing

2. **Improve error messages**
   - More specific error types
   - Better logging context

### P2 (Low Priority)

3. **Add rate limiting**
   - Per-API-key rate limiting
   - Respect API rate limits

4. **Add monitoring**
   - Track API call success/failure rates
   - Monitor response times

---

## 📊 API Integration Status

| Provider | Status | Error Handling | Retry Logic | Test Support |
|----------|--------|----------------|-------------|--------------|
| **USDA** | ✅ Complete | ✅ Yes | ⚠️ No | ✅ Yes |
| **OpenFoodFacts** | ✅ Complete | ✅ Yes | ⚠️ No | ✅ Yes |
| **Unified DB** | ✅ Complete | ✅ Yes | ✅ Fallback | ✅ Yes |
| **Ollama** | ✅ Complete | ✅ Yes | ✅ Yes | ✅ Yes |
| **Grok** | ✅ Complete | ✅ Yes | ✅ Yes | ✅ Yes |
| **Pico** | ✅ Complete | ✅ Yes | ⚠️ No | ✅ Yes |
| **Catalog (stubs)** | ⚠️ Stub | N/A | N/A | ✅ Yes |

---

## 🔍 Verification

**Test external API blocking:**
```bash
# Verify tests block external HTTP
pytest tests/test_openfoodfacts_client.py -v
```

**Check provider availability:**
```python
# Check if providers are importable
from providers import OllamaProvider, GrokProvider, PicoProvider
```

---

**Last updated:** 2026-01-15
