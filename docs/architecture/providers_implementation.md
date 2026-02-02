# Providers Implementation — Detailed Analysis

**Originally drafted:** 2026-01-12
**Purpose:** Document how `providers/` is implemented and how it is wired into runtime (via `llm.py` + `legacy_app.py` insight endpoints).

---

## 📋 Current State (Facts)

### Directory Structure

```text
providers/
├── __init__.py      # ProviderBase Protocol
├── grok.py          # xAI Grok provider
├── ollama.py        # Local Ollama provider
├── pico.py          # Pico provider (Ollama-compatible)
├── stub.py          # Stub provider (for tests)
└── AGENTS.md        # Provider-specific rules
```

### What Providers Are

**LLM Providers** (Language Model Providers):
- Abstract interface: `ProviderBase` (Protocol)
- Implementations: `GrokProvider`, `OllamaProvider`, `PicoProvider`, `StubProvider`
- Purpose: Provide LLM (Large Language Model) capabilities for AI features

**Not to be confused with:**
- Catalog providers (`app/services/catalog_adapter.py`) — different domain (food catalog)
- Shoplist providers (`core/catalog/provider.py`) — different domain (shopping list)

---

## 🔍 Implementation Details

### 1. ProviderBase Protocol

**File:** `providers/__init__.py`

```python
class ProviderBase(Protocol):
    """Базовый интерфейс для всех LLM-провайдеров."""
    name: str
    async def generate(self, text: str) -> str:
        raise NotImplementedError("Provider must implement .generate(text)")
```

**Design:**
- Protocol-based (structural typing)
- Minimal interface: `name` + `generate(text)` method
- Async-first (all providers are async)

**Rationale:**
- Allows multiple implementations (grok, ollama, pico, stub)
- Easy to swap providers via env var (`LLM_PROVIDER`)
- Testable via stub provider

---

### 2. GrokProvider (xAI)

**File:** `providers/grok.py`

**Implementation:**
- Uses OpenAI-compatible SDK (`AsyncOpenAI`)
- Endpoint: `https://api.x.ai/v1` (default)
- Model: `grok-4-latest` (default)
- API key: from env (`GROK_API_KEY` or `XAI_API_KEY`)
- Retry logic: 3 attempts with exponential backoff

**Key features:**
- Network calls via `httpx` (async)
- Error handling: wraps exceptions in `RuntimeError`
- Timeout: 30s (default, configurable)

**Rationale:**
- xAI provides OpenAI-compatible API
- Reuse existing OpenAI SDK (less code)
- Production-ready provider for cloud LLM

---

### 3. OllamaProvider (Local)

**File:** `providers/ollama.py`

**Implementation:**
- Local/self-hosted Ollama server
- Endpoint: `http://localhost:11434` (default)
- Model: `llama3.1:8b` (default)
- Timeout: 1.5s (short, for fast 503 responses)
- Retry logic: 3 attempts with exponential backoff

**Key features:**
- Two API methods: `/api/chat` (preferred) + `/api/generate` (fallback)
- Handles multiple response formats (compatible implementations)
- Fast timeout → quick 503 if Ollama unavailable
- Network errors → `RuntimeError("ollama_unavailable")`

**Rationale:**
- Privacy: local models, no data leaves machine
- Cost: free (self-hosted)
- Flexibility: can use any Ollama-compatible model
- Fast failure: short timeout prevents hanging requests

---

### 4. PicoProvider (Ollama-Compatible)

**File:** `providers/pico.py`

**Implementation:**
- Ollama-compatible provider (alternative to Ollama)
- Endpoint: same as Ollama (default: `http://localhost:11434`)
- Model: same as Ollama (default: `llama3.1:8b`)
- Timeout: 5.0s (longer than Ollama)

**Key features:**
- Sync + async fallback (for test compatibility)
- Handles multiple response formats
- Error handling: wraps in `RuntimeError`

**Rationale:**
- Alternative to Ollama (if user prefers Pico)
- Same API contract as Ollama (easy swap)
- Test compatibility (sync client for monkeypatch)

---

### 5. StubProvider (Testing)

**File:** `providers/stub.py`

**Implementation:**
- No network calls
- Deterministic output: `[stub @ {timestamp}] Insight: {text[:120]}`
- Synchronous (not async, but compatible)

**Rationale:**
- Fast tests (no network)
- Deterministic (predictable output)
- No external dependencies

---

## 🔗 Integration Point: `llm.py`

**File:** `llm.py` (root level)

**Purpose:** Factory function to get LLM provider based on env var.

**Implementation:**
```python
# Lazy imports (fail-soft if provider unavailable)
try:
    from providers.grok import GrokProvider as _GrokProvider
except ImportError:
    GrokProvider = None

try:
    from providers.ollama import OllamaProvider as _OllamaProvider
except ImportError:
    OllamaProvider = None

# Factory function
def get_provider():
    val = os.getenv("LLM_PROVIDER", "").strip().lower()
    if val == "grok":
        return GrokProvider(...) or GrokLiteProvider()
    if val == "ollama":
        return OllamaProvider(...) or OllamaLiteProvider()
    if val == "stub":
        return StubProvider()
    return None
```

**Rationale:**
- Fail-soft: if provider unavailable → fallback to "lite" provider
- Lite providers: offline fallback (no network, returns formatted text)
- Env-based selection: easy to switch providers

---

## ✅ Current Runtime Usage: WIRED (via `legacy_app.py` insight endpoints)

### Evidence: Providers are used via `legacy_app.py → llm.py → providers/*`

**1. Insight endpoints live in `legacy_app.py` (not in `app/routers/`)**

- Evidence:
  - `legacy_app.py:2168-2187` defines HTTP routes:
    - `POST /api/v1/insight` (API key gated)
    - `POST /insight` (legacy path)

**2. `legacy_app.py` loads `llm.get_provider` lazily and calls `provider.generate()`**

- Evidence:
  - `legacy_app.py:2066-2076` — `_load_llm_get_provider()` imports `llm.get_provider`
  - `legacy_app.py:2098-2117` — `provider = get_provider()` and `await provider.generate(prompt_text)`

**3. `llm.py` imports `providers/*` and selects provider by env var**

- Evidence:
  - `llm.py:57-79` — optional imports of `providers.grok`, `providers.ollama`, `providers.pico`
  - `llm.py:91-153` — `get_provider()` selects provider based on `LLM_PROVIDER`

**Conclusion:** `providers/` is wired into runtime through the insight endpoints in `legacy_app.py`, with `llm.get_provider()` acting as the factory/adapter layer.

---

## 🎯 Why Providers Exist (Design Rationale)

### Original Intent (Inferred)

**Purpose:** Provide LLM capabilities for AI features (e.g., nutrition insights, recipe synthesis).

**Design decisions:**
1. **Multiple providers** → flexibility (cloud vs local)
2. **Protocol-based** → easy to swap implementations
3. **Fail-soft** → graceful degradation (lite providers)
4. **Env-based selection** → no code changes to switch providers

### Current Status

**Implemented:**
- ✅ Provider interfaces (Protocol)
- ✅ Multiple implementations (grok, ollama, pico, stub)
- ✅ Factory function (`llm.py`)
- ✅ Tests (unit tests for each provider)

**Runtime wiring (current):**
- ✅ Insight endpoints in `legacy_app.py` call `llm.get_provider()` and then `provider.generate()`

**Historical note (superseded):**
- Earlier versions of this doc claimed providers were “not wired into runtime” because `app/routers/` did not import them.
  That was incomplete: the wiring lives in `legacy_app.py` (root module), not in `app/routers/`.

---

## 📊 Provider Usage Analysis

### Where Providers Are Used

**1. `llm.py` (root):**
- Imports all providers
- Factory function `get_provider()`
- Lite providers (fallback)

**2. Tests:**
- `tests/test_providers_unit.py` — unit tests
- `tests/test_llm*.py` — integration tests
- `tests/test_llm_import_coverage.py` — import coverage

**3. Scripts:**
- `ollama_diagnostic.sh` — diagnostic script
- `ollama_monitor.sh` — monitoring script

**4. Documentation:**
- `docs/finetune/README.md` — mentions providers
- `docs/archive/2025-09-16/` — historical docs

### Where Providers Are NOT Used (directly)

**Verified via (reproducible check):**
- Run: `rg -n --type=py 'providers\.' app/routers app/services`
- Expected outcome: **no matches** (no direct `providers.*` imports in those directories).

**1. `app/routers/` (directly):**
- No direct imports of `providers/*` (LLM wiring for insight currently lives in `legacy_app.py`)

**2. `app/services/` (directly):**
- No direct `providers/*` usage (LLM integration is routed through `llm.py` and called from `legacy_app.py`)

**3. Core domain:**
- No LLM calls in `core/` modules

---

## 🔮 Future Integration (Not Current)

### Potential Use Cases

**1. Nutrition Insights:**
- `/api/v1/vip/insight` endpoint
- Uses LLM to generate nutrition insights
- Requires VIP tier

**2. Recipe Synthesis:**
- AI-generated recipes
- Uses LLM to create custom recipes
- Requires VIP tier

**3. Meal Planning:**
- AI-assisted meal planning
- Uses LLM for suggestions
- Requires PRO/VIP tier

### Why Not Connected Yet

**Possible reasons:**
1. Feature not ready (still in development)
2. Waiting for LLM infrastructure (Ollama setup, API keys)
3. Prioritizing other features first
4. Design decision: keep LLM optional/experimental

---

## ✅ Verification: Providers wired into runtime

Evidence pointers (runtime truth):

- `legacy_app.py:2168-2187` — insight HTTP endpoints exist (`/api/v1/insight`, `/insight`)
- `legacy_app.py:2066-2076` — lazy loader imports `llm.get_provider`
- `legacy_app.py:2098-2117` — calls `provider.generate(...)`
- `llm.py:57-79` + `91-153` — imports/selects `providers/*` via `LLM_PROVIDER`

---

## 📝 Implications for OpenAPI stability

### OpenAPI Stability

**Fact:** `providers/` is wired into runtime via insight endpoints (legacy_app → llm → providers).

**Implication for OpenAPI:**
- Providers are not OpenAPI consumers themselves, but they are part of runtime behavior via insight endpoints.
- OpenAPI stability policy still primarily serves thin clients (web types from OpenAPI) and unknown external consumers.
- See ADR: `docs/architecture/ADR-002-openapi-schema-only-mode.md` (schema-only contract + exit criteria).

**OpenAPI Stability Rationale (separate from providers):**
- Web frontend generates types from OpenAPI (`openapi.json` → `schema.ts`)
- External OpenAPI consumers are unknown
- iOS is manual today (does not depend on OpenAPI)

**Conclusion:** OpenAPI stability policy is driven by web type generation and unknown external consumers, **not by providers** (providers are not OpenAPI consumers).

---

## 🎯 Summary

**What providers are:**
- LLM provider implementations (grok, ollama, pico, stub)
- Abstracted via `ProviderBase` Protocol
- Selected via env var (`LLM_PROVIDER`)
- Factory function in `llm.py`

**Current status:**
- ✅ Implemented (code exists)
- ✅ Wired into runtime via `legacy_app.py` insight endpoints and `llm.get_provider()`
- ✅ Tested (unit tests exist)

**Why they exist:**
- Future AI features (insights, recipe synthesis)
- Flexibility (cloud vs local LLM)
- Fail-soft design (graceful degradation)

**For PR-521:**
- Providers are potential future OpenAPI consumers
- Cannot assume they won't use OpenAPI in future
- Therefore: keep deprecated aliases in schema (vendor extensions only)

---

**Last updated:** 2026-02-02
**Status:** Providers exist and are wired into runtime via insight endpoints
