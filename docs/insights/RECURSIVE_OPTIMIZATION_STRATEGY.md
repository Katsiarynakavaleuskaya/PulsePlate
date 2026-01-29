# Recursive Methods Optimization Strategy

**Document Purpose:** Concrete optimization strategies to minimize latency impact of recursive LLM/RAG methods, leveraging our FastAPI architecture and open-source libraries.

**Status:** Implementation Guide
**Created:** 2026-01-28
**Related:**
- `docs/insights/RECURSIVE_METHODS_LLM_RAG.md`
- `docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md`
- `app/main.py`, `providers/ollama.py`, `providers/grok.py`

---

## Executive Summary

**Current Architecture:**
- FastAPI with async/await (✅ ready for parallelization)
- httpx for async HTTP (✅ ready for concurrent calls)
- Redis available in docker-compose (⏳ not actively used)
- In-memory caching exists (TTLCacheAnalyzerStore pattern)

**Optimization Strategy:**
1. **Parallelization** (asyncio.gather) → 50% latency reduction
2. **GPTCache integration** (semantic caching) → 30-50% latency reduction
3. **Redis caching** (query refinement, decomposition) → 40-60% latency reduction
4. **Batch processing** (verification queries) → 60-70% latency reduction
5. **Streaming responses** (progressive disclosure) → perceived latency reduction

**Expected Result:** Reduce recursive latency from 2-3x to **1.2-1.5x** (acceptable for VIP tier).

---

## 1. Architecture Analysis

### 1.1 Current Stack

**Async Infrastructure:**
- ✅ FastAPI (async endpoints)
- ✅ httpx (async HTTP client)
- ✅ asyncio (Python async runtime)
- ✅ SQLAlchemy async support (optional)

**Caching Infrastructure:**
- ✅ In-memory TTL cache (`core/analyzer/store_cache.py`)
- ✅ File-based cache (`core/food_apis/unified_db.py`)
- ⏳ Redis available (`docker-compose.yaml`) but not integrated
- ❌ No semantic caching for LLM queries

**LLM Providers:**
- ✅ GrokProvider (async, httpx-based)
- ✅ OllamaProvider (async, httpx-based)
- ✅ Retry logic (tenacity)
- ❌ No request batching
- ❌ No response caching

### 1.2 Bottlenecks Identified

1. **Sequential LLM calls** (no parallelization)
2. **No semantic caching** (redundant LLM calls for similar queries)
3. **No query refinement caching** (same refinement computed multiple times)
4. **No batch verification** (N calls instead of 1)
5. **No streaming** (users wait for complete response)

---

## 2. Optimization Strategies

### 2.1 Parallelization with asyncio.gather

**Current Problem:** Recursive methods call LLM sequentially.

**Solution:** Use `asyncio.gather` for independent operations.

**Implementation:**

```python
# core/insight/recursive_reasoning_optimized.py
import asyncio
from typing import List

class OptimizedRecursiveReasoner:
    """Recursive reasoner with parallel subproblem solving."""

    async def reason_recursive_parallel(
        self,
        query: str,
        context: Optional[str] = None
    ) -> RecursiveReasoningResult:
        """Solve subproblems in parallel."""

        # Step 1: Decompose (sequential, needed first)
        subproblems = await self._decompose_query(query, context)

        # Step 2: Solve subproblems in PARALLEL
        subproblem_tasks = [
            self._solve_subproblem(sp) for sp in subproblems
        ]
        subproblem_results = await asyncio.gather(*subproblem_tasks)

        # Step 3: Synthesize (sequential, depends on all results)
        synthesized_answer = await self._synthesize_answers(
            query,
            subproblem_results
        )

        return RecursiveReasoningResult(
            answer=synthesized_answer,
            reasoning_steps=self._flatten_reasoning_steps(subproblem_results),
            decomposition_used=True,
            subproblems=subproblems
        )

    async def _solve_subproblem(self, subproblem: Subproblem) -> RecursiveReasoningResult:
        """Solve single subproblem (can be parallelized)."""
        if subproblem.depth < self.max_depth:
            return await self.reason_recursive_parallel(
                subproblem.query,
                context=subproblem.context
            )
        else:
            answer = await self.llm.generate(f"Answer: {subproblem.query}")
            return RecursiveReasoningResult(
                answer=answer,
                reasoning_steps=[ReasoningStep(query=subproblem.query, answer=answer, depth=subproblem.depth)],
                decomposition_used=False
            )
```

**Impact:** 50% latency reduction for recursive reasoning (subproblems solved in parallel).

**Integration:** Drop-in replacement for `RecursiveReasoner.reason_recursive()`.

---

### 2.2 GPTCache Integration (Semantic Caching)

**Library:** [GPTCache](https://github.com/zilliztech/GPTCache) — semantic cache for LLM queries.

**Problem:** Similar queries trigger redundant LLM calls.

**Solution:** Cache LLM responses semantically (similar queries → cached response).

**Installation:**
```bash
pip install gptcache
```

**Implementation:**

```python
# core/insight/gptcache_integration.py
from gptcache import Cache
from gptcache.manager import get_data_manager, CacheBase, VectorBase
from gptcache.similarity_evaluation import SearchDistanceEvaluation
from gptcache.adapter import openai

class GPTCacheWrapper:
    """Wrapper for LLM providers with GPTCache semantic caching."""

    def __init__(self, provider: ProviderBase):
        self.provider = provider
        self.cache = self._init_cache()

    def _init_cache(self) -> Cache:
        """Initialize GPTCache with semantic similarity."""
        # Use in-memory cache for simplicity (can switch to Redis)
        cache_base = CacheBase(name="memory")
        vector_base = VectorBase(name="memory")
        data_manager = get_data_manager(cache_base, vector_base)

        # Semantic similarity threshold (0.8 = 80% similarity)
        evaluation = SearchDistanceEvaluation(threshold=0.8)

        cache = Cache()
        cache.init(
            pre_embedding_func=self._pre_embedding,
            data_manager=data_manager,
            similarity_evaluation=evaluation
        )
        return cache

    def _pre_embedding(self, data: dict, **kwargs) -> str:
        """Extract query text for embedding."""
        return data.get("messages", [{}])[0].get("content", "")

    async def generate_cached(self, prompt: str) -> str:
        """Generate with semantic caching."""
        # Check cache first
        cached_response = self.cache.get(prompt)
        if cached_response:
            return cached_response

        # Generate if not cached
        response = await self.provider.generate(prompt)

        # Cache response
        self.cache.put(prompt, response)

        return response
```

**Integration:**

```python
# providers/llm_cached.py
from core.insight.gptcache_integration import GPTCacheWrapper

def get_cached_provider():
    """Get LLM provider with semantic caching."""
    base_provider = get_provider()  # Existing function
    if base_provider:
        return GPTCacheWrapper(base_provider)
    return None
```

**Impact:** 30-50% latency reduction for similar queries (cache hit rate ~40-60%).

**Configuration:**
- Similarity threshold: 0.8 (80% similarity = cache hit)
- Cache backend: Memory (can switch to Redis for distributed caching)

---

### 2.3 Redis Caching for Query Refinement

**Current:** Redis available in docker-compose but not used.

**Problem:** Query refinement computed repeatedly for similar queries.

**Solution:** Cache refined queries in Redis.

**Installation:**
```bash
pip install redis aioredis
```

**Implementation:**

```python
# core/insight/redis_cache.py
import json
import hashlib
from typing import Optional
import aioredis

class RedisQueryCache:
    """Redis cache for query refinement and decomposition."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self.ttl = 3600  # 1 hour TTL

    async def _get_redis(self) -> aioredis.Redis:
        """Lazy Redis connection."""
        if self._redis is None:
            self._redis = await aioredis.from_url(self.redis_url)
        return self._redis

    def _cache_key(self, query: str, operation: str) -> str:
        """Generate cache key."""
        key_data = f"{operation}:{query}"
        return f"llm_cache:{hashlib.md5(key_data.encode()).hexdigest()}"

    async def get_refined_query(self, query: str, context: str) -> Optional[str]:
        """Get cached refined query."""
        redis = await self._get_redis()
        cache_key = self._cache_key(f"{query}:{context}", "refine")
        cached = await redis.get(cache_key)
        if cached:
            return cached.decode("utf-8")
        return None

    async def set_refined_query(self, query: str, context: str, refined: str):
        """Cache refined query."""
        redis = await self._get_redis()
        cache_key = self._cache_key(f"{query}:{context}", "refine")
        await redis.setex(cache_key, self.ttl, refined)

    async def get_decomposition(self, query: str) -> Optional[List[Subproblem]]:
        """Get cached query decomposition."""
        redis = await self._get_redis()
        cache_key = self._cache_key(query, "decompose")
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached.decode("utf-8"))
        return None

    async def set_decomposition(self, query: str, subproblems: List[Subproblem]):
        """Cache query decomposition."""
        redis = await self._get_redis()
        cache_key = self._cache_key(query, "decompose")
        await redis.setex(
            cache_key,
            self.ttl,
            json.dumps([sp.__dict__ for sp in subproblems])
        )
```

**Integration:**

```python
# core/insight/recursive_rag_optimized.py
class OptimizedRecursiveRAG:
    def __init__(self, base_retriever: SimpleRAG, llm_provider: ProviderBase):
        self.base_retriever = base_retriever
        self.llm = llm_provider
        self.redis_cache = RedisQueryCache()  # Add Redis cache

    async def retrieve_recursive(self, query: str, max_chunks: int = 5):
        # Check cache first
        cached_refinement = await self.redis_cache.get_refined_query(query, "")
        if cached_refinement:
            # Use cached refinement
            refined_query = cached_refinement
        else:
            # Compute refinement
            refined_query = await self._refine_query(query, [], [])
            # Cache it
            await self.redis_cache.set_refined_query(query, "", refined_query)

        # Continue with retrieval...
```

**Impact:** 40-60% latency reduction for query refinement (cache hit rate ~50-70%).

**Configuration:**
- TTL: 1 hour (configurable)
- Redis URL: `redis://localhost:6379` (from docker-compose)

---

### 2.4 Batch Verification Queries

**Problem:** Recursive verification makes N LLM calls (one per claim).

**Solution:** Batch all verification queries into single LLM call.

**Implementation:**

```python
# core/insight/recursive_verification_optimized.py
class OptimizedRecursiveVerifier:
    """Recursive verifier with batched verification queries."""

    async def verify_recursive_batched(
        self,
        answer: str,
        query: str,
        context: Optional[str] = None
    ) -> VerificationResult:
        """Verify with batched queries."""

        # Extract claims
        claims = await self._extract_claims(answer)

        # Generate verification queries for ALL claims in ONE call
        verification_queries = await self._generate_verification_queries_batched(
            claims,
            query
        )

        # Verify ALL claims in ONE call
        verification_answers = await self._verify_claims_batched(
            claims,
            verification_queries,
            query
        )

        # Parse results
        verification_results = []
        for claim, vq, va in zip(claims, verification_queries, verification_answers):
            fact_check_result = self.fact_checker.verify(claim, domain="nutrition")
            verification_results.append(ClaimVerification(
                claim=claim,
                verification_query=vq,
                verification_answer=va,
                fact_check_result=fact_check_result,
                verified=self._synthesize_verification(va, fact_check_result)
            ))

        verification_rate = sum(1 for r in verification_results if r.verified) / len(verification_results) if verification_results else 0.0

        return VerificationResult(
            answer=answer,
            claims=claims,
            verification_results=verification_results,
            all_verified=all(r.verified for r in verification_results),
            verification_rate=verification_rate
        )

    async def _generate_verification_queries_batched(
        self,
        claims: List[str],
        original_query: str
    ) -> List[str]:
        """Generate verification queries for all claims in one LLM call."""

        claims_text = "\n".join(f"{i+1}. {claim}" for i, claim in enumerate(claims))

        prompt = f"""
Generate verification queries for these claims (one query per claim):

Original query: {original_query}

Claims to verify:
{claims_text}

For each claim, generate a verification query that can be answered with yes/no or factual check.

Format:
QUERY 1: [Verification query for claim 1]
QUERY 2: [Verification query for claim 2]
...

Generate all queries:"""

        queries_text = await self.llm.generate(prompt)
        return self._parse_verification_queries(queries_text)

    async def _verify_claims_batched(
        self,
        claims: List[str],
        verification_queries: List[str],
        original_query: str
    ) -> List[str]:
        """Verify all claims in one LLM call."""

        claims_queries_text = "\n".join(
            f"Claim {i+1}: {claim}\nQuery {i+1}: {vq}\n"
            for i, (claim, vq) in enumerate(zip(claims, verification_queries))
        )

        prompt = f"""
Verify these claims by answering the verification queries:

Original query: {original_query}

Claims and verification queries:
{claims_queries_text}

For each claim, answer the verification query (yes/no/factual answer).

Format:
ANSWER 1: [Answer for claim 1]
ANSWER 2: [Answer for claim 2]
...

Answer all:"""

        answers_text = await self.llm.generate(prompt)
        return self._parse_verification_answers(answers_text)
```

**Impact:** 60-70% latency reduction (N calls → 1 call).

**Example:**
- Before: 5 claims × 1.5s = 7.5s
- After: 1 batched call = 2s (3.75x faster)

---

### 2.5 Streaming Responses (Progressive Disclosure)

**Problem:** Users wait for complete response (3-10s).

**Solution:** Stream partial answers as recursive layers complete.

**Implementation:**

```python
# core/insight/streaming_recursive_assistant.py
from fastapi.responses import StreamingResponse
import json

class StreamingRecursiveAssistant:
    """Recursive assistant with streaming responses."""

    async def answer_streaming(
        self,
        query: str,
        user_context: UserContext
    ) -> StreamingResponse:
        """Stream answers progressively."""

        async def generate_stream():
            # Layer 1: Fast answer (immediate)
            fast_answer = await self._fast_answer(query)
            yield json.dumps({
                "layer": 1,
                "answer": fast_answer,
                "complete": False
            }) + "\n"

            # Layer 2: Improved answer (if user wants more)
            improved_answer = await self._improved_answer(query, fast_answer)
            yield json.dumps({
                "layer": 2,
                "answer": improved_answer,
                "complete": False
            }) + "\n"

            # Layer 3: Verified answer (final)
            verified_answer = await self._verified_answer(query, improved_answer)
            yield json.dumps({
                "layer": 3,
                "answer": verified_answer,
                "complete": True
            }) + "\n"

        return StreamingResponse(
            generate_stream(),
            media_type="application/x-ndjson"
        )
```

**Integration:**

```python
# app/routers/vip.py
@router.post("/api/v1/vip/insight/stream")
async def vip_insight_stream(req: InsightRequest):
    """Streaming insight endpoint."""
    assistant = StreamingRecursiveAssistant(...)
    return await assistant.answer_streaming(req.text, user_context)
```

**Impact:** Perceived latency reduction (users see partial answers immediately).

**Frontend Integration:**
```typescript
// frontend/src/api/insight.ts
async function* streamInsight(query: string) {
  const response = await fetch('/api/v1/vip/insight/stream', {
    method: 'POST',
    body: JSON.stringify({ text: query }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader!.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n').filter(Boolean);

    for (const line of lines) {
      const data = JSON.parse(line);
      yield data; // Yield progressive answers
    }
  }
}
```

---

## 3. Open-Source Libraries Integration

### 3.1 GPTCache (Semantic Caching)

**GitHub:** <https://github.com/zilliztech/GPTCache>
**License:** Apache 2.0
**Status:** Active (2024-2025)

**Features:**
- Semantic similarity caching (not exact match)
- Multiple backends (memory, Redis, SQLite)
- LangChain integration
- Docker server mode

**Integration Steps:**

1. **Install:**
```bash
pip install gptcache
```

2. **Configure:**
```python
# core/insight/gptcache_config.py
from gptcache import Cache
from gptcache.manager import get_data_manager, CacheBase, VectorBase

def init_gptcache(use_redis: bool = False) -> Cache:
    """Initialize GPTCache with Redis or memory backend."""
    if use_redis:
        cache_base = CacheBase(name="redis", redis_host="localhost", redis_port=6379)
    else:
        cache_base = CacheBase(name="memory")

    vector_base = VectorBase(name="memory")  # For semantic similarity
    data_manager = get_data_manager(cache_base, vector_base)

    cache = Cache()
    cache.init(
        pre_embedding_func=lambda x: x.get("messages", [{}])[0].get("content", ""),
        data_manager=data_manager,
        similarity_evaluation=SearchDistanceEvaluation(threshold=0.8)
    )
    return cache
```

3. **Use:**
```python
# Wrap existing provider
cached_provider = GPTCacheWrapper(get_provider())
response = await cached_provider.generate_cached(prompt)
```

**Expected Impact:** 30-50% latency reduction (cache hit rate ~40-60%).

---

### 3.2 FastLLM (Batch Processing)

**GitHub:** <https://github.com/Rexhaif/fastllm>
**License:** MIT
**Status:** Active (2024)

**Features:**
- Parallel LLM API requests
- Request deduplication
- Response ordering
- Built-in caching

**Integration Steps:**

1. **Install:**
```bash
pip install fastllm
```

2. **Use for batch verification:**
```python
from fastllm import FastLLM

fast_llm = FastLLM(provider="grok")  # or "ollama"

# Batch multiple queries
queries = [f"Verify: {claim}" for claim in claims]
responses = await fast_llm.batch_generate(queries)  # Parallel execution
```

**Expected Impact:** 60-70% latency reduction for batch operations.

---

### 3.3 LMCache (KV Cache Optimization)

**GitHub:** <https://github.com/lm-sys/LMCache>
**License:** Apache 2.0
**Status:** Active (2024-2025)

**Features:**
- KV cache for LLM (stores intermediate computations)
- 3-10x delay savings
- Works with vLLM
- Multi-round QA optimization

**Note:** More suitable for local models (Ollama) than cloud APIs (Grok).

**Integration Steps:**

1. **Install:**
```bash
pip install lmcache
```

2. **Use with Ollama:**
```python
from lmcache import LMCache

lmcache = LMCache(model="llama3.1:8b")

# Cache intermediate KV states
cached_response = await lmcache.generate_cached(prompt, cache_key=query_hash)
```

**Expected Impact:** 3-10x latency reduction for local Ollama (if using vLLM).

---

### 3.4 LangChain Caching

**GitHub:** <https://github.com/langchain-ai/langchain>
**License:** MIT
**Status:** Active (2024-2025)

**Features:**
- Native LLM caching
- GPTCache integration
- Multiple cache backends

**Integration Steps:**

1. **Install:**
```bash
pip install langchain langchain-openai
```

2. **Use:**
```python
from langchain.cache import GPTCache, InMemoryCache
from langchain_openai import ChatOpenAI

# Enable caching
import langchain
langchain.llm_cache = GPTCache()

llm = ChatOpenAI(model="grok-beta", base_url="https://api.x.ai/v1")
response = await llm.ainvoke(prompt)  # Cached automatically
```

**Expected Impact:** 30-50% latency reduction (similar to GPTCache).

---

## 4. Implementation Roadmap

### Phase 1: Quick Wins (Week 1)

**Priority: P0 (Immediate impact)**

1. **Parallelize subproblem solving** (asyncio.gather)
   - Effort: 2-3 days
   - Impact: 50% latency reduction
   - Risk: Low (async/await already in place)

2. **Batch verification queries** (single LLM call)
   - Effort: 2-3 days
   - Impact: 60-70% latency reduction
   - Risk: Medium (requires prompt engineering)

**Total Impact:** 50-60% latency reduction for recursive methods.

---

### Phase 2: Caching Integration (Week 2-3)

**Priority: P1 (High impact)**

1. **GPTCache integration** (semantic caching)
   - Effort: 3-4 days
   - Impact: 30-50% latency reduction (cache hits)
   - Risk: Low (drop-in wrapper)

2. **Redis caching** (query refinement, decomposition)
   - Effort: 2-3 days
   - Impact: 40-60% latency reduction (cache hits)
   - Risk: Low (Redis already in docker-compose)

**Total Impact:** Additional 30-50% latency reduction (on top of Phase 1).

---

### Phase 3: Advanced Optimizations (Week 4+)

**Priority: P2 (Nice to have)**

1. **Streaming responses** (progressive disclosure)
   - Effort: 5-7 days
   - Impact: Perceived latency reduction
   - Risk: Medium (requires WebSocket/SSE)

2. **FastLLM integration** (batch processing)
   - Effort: 3-4 days
   - Impact: 60-70% latency reduction for batches
   - Risk: Low (optional library)

**Total Impact:** Additional 20-30% perceived improvement.

---

## 5. Expected Performance After Optimizations

### 5.1 Latency Breakdown (Optimized)

**Simple Query (depth=1, cached):**
```text
RAG (50ms) → LLM cached (10ms) → Response
Total: ~60ms (0.06s) ✅ 10x faster than baseline
```

**Medium Query (depth=2, parallelized + cached):**
```text
RAG (100ms) → Decomposition cached (10ms) → Subproblems parallel (500ms) → Synthesis (500ms) → Response
Total: ~1110ms (1.1s) ✅ 2x faster than unoptimized
```

**Complex Query (depth=3, fully optimized):**
```text
RAG (150ms) → Decomposition cached (10ms) → Subproblems parallel (1000ms) → Synthesis (500ms) → Refinement early stop (500ms) → Verification batched (500ms) → Response
Total: ~2660ms (2.7s) ✅ 2x faster than unoptimized
```

### 5.2 Cache Hit Rates (Estimated)

- **GPTCache (semantic):** 40-60% hit rate (similar queries)
- **Redis (refinement):** 50-70% hit rate (common query patterns)
- **Redis (decomposition):** 30-50% hit rate (domain-specific queries)

**Combined Effect:** 60-80% of queries benefit from caching.

---

## 6. Configuration

### 6.1 Environment Variables

```bash
# Enable optimizations
FEATURE_RECURSIVE_OPTIMIZATION=true
FEATURE_GPT_CACHE=true
FEATURE_REDIS_CACHE=true
FEATURE_STREAMING_RESPONSES=true

# Redis configuration
REDIS_URL=redis://localhost:6379
REDIS_CACHE_TTL=3600  # 1 hour

# GPTCache configuration
GPT_CACHE_SIMILARITY_THRESHOLD=0.8  # 80% similarity = cache hit
GPT_CACHE_BACKEND=memory  # or "redis"

# Parallelization
MAX_PARALLEL_SUBPROBLEMS=5  # Max concurrent subproblem solving
MAX_PARALLEL_VERIFICATION=10  # Max concurrent verification queries
```

### 6.2 Docker Compose Update

```yaml
# docker-compose.yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    # Remove "profiles: cache" to enable by default
    networks:
      - pulseplate-network
```

---

## 7. Monitoring & Metrics

### 7.1 Metrics to Track

1. **Latency:**
   - P50, P95, P99 for recursive endpoints
   - Cache hit rate (GPTCache, Redis)
   - Parallelization efficiency (tasks completed in parallel vs sequential)

2. **Quality:**
   - Answer accuracy (should remain ≥85%)
   - Verification rate (should remain ≥95%)
   - User satisfaction (should improve with faster responses)

3. **Cost:**
   - LLM calls per query (should decrease with caching)
   - Cache storage size (Redis memory usage)

### 7.2 Prometheus Metrics

```python
# app/middleware/recursive_metrics.py
from prometheus_client import Counter, Histogram, Gauge

recursive_queries_total = Counter(
    "recursive_queries_total",
    "Total recursive queries",
    ["method", "depth"]
)

recursive_latency_seconds = Histogram(
    "recursive_latency_seconds",
    "Recursive query latency",
    ["method", "depth"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

cache_hits_total = Counter(
    "cache_hits_total",
    "Cache hits",
    ["cache_type"]
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Cache misses",
    ["cache_type"]
)
```

---

## 8. Conclusion

**Key Takeaways:**

1. **Parallelization** (asyncio.gather) is the biggest win → 50% latency reduction, low effort.

2. **GPTCache** provides semantic caching → 30-50% latency reduction for similar queries.

3. **Redis caching** leverages existing infrastructure → 40-60% latency reduction for query refinement.

4. **Batch processing** reduces N calls to 1 → 60-70% latency reduction for verification.

5. **Combined optimizations** reduce recursive latency from 2-3x to **1.2-1.5x** (acceptable for VIP tier).

**Recommendation:** Implement Phase 1 (parallelization + batching) immediately, then Phase 2 (caching) for maximum impact.

---

**Last Updated:** 2026-01-28
**Status:** Implementation Guide — Ready for Development
