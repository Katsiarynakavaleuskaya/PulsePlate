# Universal Agent Orchestration Layer — Audit

**Status:** Canonical orchestration rationale artifact aligned to the current workflow and experimentation SoTs
**Topic PR:** tracked by branch `docs/universal-orchestration-audit-canonicalization`
**Branch:** `docs/universal-orchestration-audit-canonicalization`
**Scope:** orchestration rationale only (docs / dev-process), **no runtime impact**
**Date:** 12 March 2026

---

## Executive summary (RU)

Цель этого аудита — зафиксировать **канонический, воспроизводимый, evidence-driven** audit-слой для universal orchestration
контекста PulsePlate, совместимый с уже принятым каркасом: **Coordinator → routing → handoff → review → synthesis → DoD**.

Ключевые решения:

- **SoT (Source of Truth)** живёт только в репозитории (docs + код + тесты), а не в “памяти” агентов.
- **Coordinator** — единственный агент, который финализирует решения и формирует итоговые артефакты.
- **Evidence contract**: любой значимый claim в audit/decision должен иметь ссылку на evidence: `file:line` (внутри репо) и/или
  конкретный воспроизводимый command + raw output + exit code (если помечаем как Verified).
- **Safety-first**: wellness-only формулировки (не медицина, не терапия), обязательные disclaimers и “high uncertainty → degrade” политика.

Этот PR — **docs-only**: мы фиксируем границы, контракты ролей и вопросы аудита; реализация (runtime) — отдельной серией PR.

---

## Executive summary (EN)

This audit defines a **reproducible, evidence-driven** rationale layer for PulsePlate's universal orchestration context,
compatible with the canonical workflow: **Coordinator → routing → handoff → review → synthesis → DoD**.

Key decisions:

- Canonical knowledge lives in the repo (docs/code/tests), never in agent “memory”.
- The Coordinator is the single finalizer for decisions and artifacts.
- Evidence contract: claims must be backed by `file:line` and/or reproducible commands with raw output + exit code when “Verified”.
- Safety-first: wellness-only language, required disclaimers, and “high uncertainty → degrade” behavior.

This audit is a rationale artifact only. Runtime behavior remains governed by the workflow, experimentation, and repo hard gates.

---

## Canonical references (single source of truth)

**Evidence anchors:**
- `docs/orchestration/workflow.md:61-72`
- `docs/orchestration/AGENT_CONTEXT_MAP.md:22-45`

### Orchestration canon

- `docs/orchestration/workflow.md` (canonical workflow + **Pre-flight Checklist (SoT)**)
- `docs/orchestration/AGENT_CONTEXT_MAP.md` (context loading requirements)
- `docs/orchestration/AGENT_CAPABILITY_MATRIX.md` (routing guide; advisory, not permissions)
- `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md` (formal handoffs)
- `docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md` (dialogue hard limit + coordinator intervention rule)
- `docs/orchestration/PARALLEL_WORK_PROTOCOL.md` (parallel tracks + sync points)
- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md` (governed experimentation umbrella)

### Governance alignment

- This audit is a rationale layer, not a second orchestration constitution.
- Canonical workflow authority remains `docs/orchestration/workflow.md`.
- Experiment-loop authority remains `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`.
- Hidden memory, autonomous merge, and runtime autonomy remain prohibited by repo-level policy.

### Repo-wide hard rules

- `AGENTS.md` (hard gates, coordinator-first rule, docs-only PR rule, audit evidence requirements)
- `RUNBOOK_AGENT.md` (operational checks)
- `docs/agents/index.md` (Cursor agents registry; must stay in sync with `.cursor/agents/*.md`)

### Discovery / research-to-PR (dev-only)

- `docs/audit/SCIENTIFIC_DISCOVERY_LAYER_AUDIT.md` (Scientific Discovery Layer; dev-only discovery loop + new agents)

### Insight / scientific R&D corpus (non-canonical inputs)

These documents are **inputs** for planning and audits. They must **not** be treated as runtime truth unless backed by code/tests.

- `docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md` (baseline analysis of current LLM/RAG infra)
- `docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md` (scientific review; roadmap framing)
- `docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md` (philosophy+logic reliability frameworks)
- `docs/insights/PHILOSOPHICAL_SPEED_OPTIMIZATION.md` (adaptive depth / early stopping)
- `docs/insights/RECURSIVE_METHODS_LLM_RAG.md` (multi-hop retrieval, refinement, verification)
- `docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md` (latency/cost trade-offs + mitigation strategies)

---

## Evidence log (observed)

### Orchestration workflow exists and is explicitly dev-only

```1:7:docs/orchestration/workflow.md
# Dev Orchestrator Workflow (Canonical)
...
**Status:** dev-only, no runtime impact
```

### Pre-flight Checklist is centralized as SoT

```51:57:docs/orchestration/workflow.md
## Canonical Pre-flight Checklist (SoT)
...
(EN: This checklist is the single source of truth; other docs must link here.)
```

### Coordinator-first rule is a hard gate

```111:119:AGENTS.md
## Agent Coordination (Coordinator-First Rule)
**Hard rule:** Any new task MUST start with `agent-coordinator` for task analysis and agent routing.
...
```

### Insight is a high-risk surface with explicit hard guardrails (VIP gating + rate limit + quota)

```204:218:docs/roadmap/BACKLOG_LEDGER.md
- [x] PR-611 AI Insight Safety & Error Hygiene (merged 2026-01-28)
...
  - DoD: ✅ Completed
    - ✅ Import-failure returns 503 with safe detail (no "boom" leak)
    - ✅ Provider.generate exceptions return 503 with safe detail (no raw exception leak)
    - ✅ All insight endpoints use `response_model=InsightResponse`
...
```

```307:370:docs/roadmap/BACKLOG_LEDGER.md
- [x] P0 CRITICAL: Rate-limiting for LLM endpoints (prevent $72k/month cost attack)
...
    - ✅ `@limit_if_available(RATE_LIMIT_INSIGHT)` on `/api/v1/insight` + `/insight`
...
### P0 Move LLM insight to VIP tier
...
- [x] P0 CRITICAL: Move LLM insight to VIP tier (prevent FREE tier abuse)
...
    - ✅ `/api/v1/insight` uses `require_vip_tier()` (VIP-only)
...
- [x] P0 CRITICAL SECURITY: VIP LLM hard monthly quota (deterministic enforcement)
...
    - Tests:
      - VIP under quota → 200
      - VIP over quota → 429
      - FREE/PRO remain → 403
```

### Insight baseline explicitly calls out missing reliability features (analysis)

```19:24:docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md
**Критические пробелы:**
- ❌ Нет техник повышения достоверности (fact-checking, validation, confidence scoring)
- ❌ Нет AI ассистента (только простой insight endpoint)
```

### Current RAG baseline is a simple keyword/Jaccard retriever (analysis)

```182:216:docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md
## 🔍 Детальный анализ RAG системы
...
### Текущая реализация: Simple RAG
...
**Файл:** `core/rag/simple_rag.py`
...
**Алгоритм:**
def _score(query: str, text: str) -> float:
    # Simple Jaccard on word sets
    q = set(_tokenize(query))
    t = set(_tokenize(text))
    union = q | t
    base = len(q & t) / len(union) if union else 0.0
    if query.lower() in text.lower():
        base += 0.1  # Bonus for exact substring
    return base
...
```

### Insight research corpus is explicitly “illustrative code only” (not runtime)

```14:15:docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md
> **Note:** Code examples in this document are illustrative and represent proposed design patterns, not current implementation.
```

### Scientific review explicitly frames “philosophy + logic + bayes + CBT” as the innovation foundation

```11:19:docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md
Представленные документы раскрывают **высокоинтеллектуальную экосистему** с уникальным сочетанием:
- **Философско-математического фундамента**
- **Рекурсивных методов оптимизации**
- **Передовых AI/LLM практик**
...
**Ключевой инсайт:** ... **научно-инженерный гибрид** ...
```

---

## Audit goals and non-goals

### Goals

- Define **system boundaries** (SoT, memory/state rules, canonical vs non-canonical layers).
- Define **agent taxonomy** and **role contracts** for new “scientific + applied + domain” agents.
- Define **evidence contract**, **uncertainty contract**, and **safety/ethics contract** for wellness domain.
- Define **multi-agent interaction patterns** (sequential, parallel, dialogue/debate) and conflict resolution.
- Define **extensibility rules** for adding new agents without drift.

### Non-goals (explicit)

- No runtime endpoints, no provider calls, no new quotas/rate limits in this PR.
- No changes to `app/`, `core/`, `providers/`, `tests/` (implementation PRs follow).
- No changes to medical/therapy positioning beyond language/safety disclaimers in docs.

---

## I. System boundaries audit (SoT + layer boundaries)

### 1) Source of Truth (SoT)

**Decision (canonical):**

> Agents never store canonical knowledge. All canonical knowledge lives in repo docs/code/tests.

**Audit questions:**

1. Какие знания считаются каноническими (SoT) для orchestration?
2. Где запрещено хранить “истину”: agent memory, prompt history, external tools?
3. Как знание “promote” из reasoning в docs без дрейфа (см. Backlog Ledger policy)?

**Acceptance criteria:**

- Любой новый инвариант → фиксируется в 1 SoT-документе (не дублируем).
- Любое “отложили” → запись в `docs/roadmap/BACKLOG_LEDGER.md`.

### 2) Canonical vs non-canonical layers

**Canonical (may affect decisions):**

- `AGENTS.md`, `RUNBOOK_AGENT.md`, `docs/orchestration/*`, scoped `*/AGENTS.md`, contract docs.

**Non-canonical (must not change product behavior):**

- Scratch reasoning, temporary notes, session-only artifacts, external retrieved content.

**Stop condition:**

Если агент “сделал вывод” и он не попал в репо-док/код/тесты → это не SoT и не считается решением.

---

## II. Agent taxonomy audit (кто есть в системе)

### Existing Cursor agents (already registered)

See `docs/agents/index.md` + `.cursor/agents/*.md`.

### New agent roles (proposed)

**Core / Scientific**

- `philosophy-agent`
- `logic-agent`
- `bayesian-uq-agent`
- `rag-systems-agent`

**Applied AI**

- `cv-agent`
- `ai-app-architect`
- `data-scientist-agent`
- `ml-engineer-agent`

**Domain experts**

- `nutritionist-agent`
- `cbt-psychologist-agent`

**Control**

- `agent-coordinator` (single final authority)

**Audit questions:**

1. Есть ли агент без чёткой области и deliverable?
2. Есть ли пересечения полномочий (role drift risk)?
3. Кто имеет право veto? (в этой модели: veto = Coordinator decision after bounded dialogue)

---

## III. Role responsibility audit (контракты ролей)

### Universal Role Contract (required for each new agent)

Each agent doc (in `.cursor/agents/*.md`) must declare:

- **SoT loaded** (what files it must read)
- **Can / Cannot** (scope boundaries)
- **Deliverable** (what it returns to coordinator)
- **Evidence requirements** (what counts as evidence)

### Role-specific audit questions (per agent)

#### `philosophy-agent`

- Какие типы claim считаются “осмысленными/проверяемыми/фальсифицируемыми” для insight/coach?
- Какие speech-acts запрещены (wellness safety)?
- DoD метрики: contradiction rate, unverifiable claims rate.

#### `logic-agent`

- Какие claims извлекаем и в каком минимальном schema?
- Где хранится набор правил (SoT) и как обновляется без дрейфа?
- 10 must-catch contradictions для PulsePlate (как тестовые фикстуры — future PR).

#### `bayesian-uq-agent`

- Где uncertainty обязателен (insight/coaching/meal planning)?
- Формат uncertainty (одно решение на MVP: score + bucket + optional CI).
- Science метрики: calibration (Brier), coverage.

#### `rag-systems-agent`

- Baseline SoT: single-pass retrieval vs recursive; feature flag strategy.
- Budget/stop conditions: max hops, early-stop thresholds.
- Security/cost: tier gating + rate limit + quota pre-check (future PR).

#### `cv-agent`

- MVP scope: dish-level vs ingredients vs portions (choose one).
- Contract shape: items + confidence + mapping to FoodDB.
- Privacy/logging boundaries.

#### `ai-app-architect`

- Unified pipeline contract: RAG → logic → UQ → safety → coordinator.
- Feature flags (names + ownership).
- Determinism constraints (OpenAPI + tests).

#### `data-scientist-agent`

- Hybrid metrics: product + science (retention, trust, calibration).
- Data sources + anonymization + retention policy.

#### `ml-engineer-agent`

- Latency budget + call amplification controls (recursive).
- Caching / parallelization plan + stop conditions.

#### `nutritionist-agent`

- Safe nutrition language and “no medical claims” boundaries.
- Domain constraints that must be formalized as rules (logic/bayes).

#### `cbt-psychologist-agent`

- CBT-inspired coaching (non-therapy) boundaries + forbidden phrasing list.
- Interaction contract with UQ (high uncertainty → “ask questions / suggest professional help”).

---

## IV. Reasoning, Uncertainty, RAG, CV — contracts (MVP policy)

This audit stays ADR-style. The contract text is centralized here:

- `docs/orchestration/contracts/AI_OUTPUT_CONTRACTS.md`
- `docs/orchestration/contracts/SAFETY_LANGUAGE_POLICY.md`

### Insight track alignment (design inputs → contracts)

This audit explicitly aligns with the repo’s “insight” research corpus:

- **Philosophical reliability**: Aristotelian/analytical/linguistic frameworks → map to **claim semantics**, **verifiability**, **non-contradiction** checks.
  - Inputs: `docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md`
- **Recursive methods**: multi-hop retrieval + refinement + verification → map to **bounded budgets** and **explicit citations**.
  - Inputs: `docs/insights/RECURSIVE_METHODS_LLM_RAG.md`
- **Performance reality**: recursive pipelines amplify latency/cost → contracts must include budgets + caching + early stopping (VIP only).
  - Inputs: `docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md`, `docs/insights/PHILOSOPHICAL_SPEED_OPTIMIZATION.md`
- **Baseline gap**: current analysis calls out missing reliability primitives → contracts close these gaps in future runtime PRs.
  - Inputs: `docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md`

> Detailed paste-ready contract text lives in:
>
> - `docs/orchestration/contracts/AI_OUTPUT_CONTRACTS.md`
> - `docs/orchestration/contracts/SAFETY_LANGUAGE_POLICY.md`

---

## V. Multi-agent interaction audit (patterns + conflict resolution)

### Allowed interaction patterns

- **Sequential**: strict handoffs via `AGENT_HANDOFF_PROTOCOL.md`
- **Parallel**: tracks + sync points via `PARALLEL_WORK_PROTOCOL.md`
- **Dialogue/debate**: bounded by **hard limit ≤3** (see `AGENT_DIALOGUE_TEMPLATE.md`)

### Conflict resolution

**Rule:**

> Coordinator resolves conflicts or forces a decision in ≤3 dialogue iterations. All trade-offs are recorded.

**Audit questions:**

- Что если `logic-agent` ≠ `nutritionist-agent`?
- Где фиксируем конфликт: audit doc / decision log?
- Что считаем “blocking” vs “non-blocking advisory”?

---

## VI. Memory & state audit (session vs promoted knowledge)

### Session memory (non-canonical)

- Temporary reasoning is session-local; it must not become SoT implicitly.

### Knowledge promotion (canonical)

**Rule:**

> Any new durable rule/contract must be promoted into the repo as a doc/code/test change, or recorded as deferred work in the ledger.

---

## VII. Safety, ethics, wellness boundaries (CBT + nutrition)

### Psychological safety (CBT-inspired, not therapy)

**Forbidden (examples):**

- direct diagnosis language
- treatment-or-cure claims
- Crisis/clinical instructions without escalation policy (future PR).

**Required:**

- Wellness-only language + disclaimers
- High uncertainty → “ask questions / suggest professional support”

### Medical/nutrition boundaries

**Required disclaimer (SoT):**

Use the canonical disclaimer: `docs/safety/WELLNESS_DISCLAIMER_CANONICAL.md`.

---

## VIII. Orchestration process audit (task lifecycle)

We anchor lifecycle to canonical workflow:

- Task Analysis template: `docs/orchestration/task_analysis.template.md`
- Work Review template: `docs/orchestration/work_review.template.md`
- Synthesis template: `docs/orchestration/synthesis.template.md`
- DoD template: `docs/orchestration/dod.template.md`

**Stop condition is explicit in workflow SoT** (do not execute if pre-flight incomplete).

---

## IX. Extensibility audit (adding new agents without drift)

### Adding a new agent requires updating exactly these surfaces

- `.cursor/agents/<agent>.md` (agent contract)
- `docs/agents/index.md` (registry)
- `docs/orchestration/AGENT_CONTEXT_MAP.md` (required context)
- `docs/orchestration/AGENT_CAPABILITY_MATRIX.md` (routing guide)

### Drift prevention

- No duplicated rules across multiple docs; link to SoT.
- Any deferred work → ledger entry.

---

## X. Final decision block (required)

## Decision

- **Orchestration model:** REVISE (docs-only baseline; implementation PR(s) required)
- **Open risks:** See “Security Notes” and “Next Actions”
- **Mitigations:** Budgeting, rate limiting, monthly quota, determinism, tier gating (implementation PRs)
- **Required follow-ups:** See “Next Actions”

---

## Security Notes (pre-runtime)

This PR is docs-only. The notes below are **requirements for future runtime PRs**, derived from repo hard rules.

- **Cost-abuse amplification (recursive / multi-agent)**:
  - Risk: recursion multiplies provider calls (budget blow-ups).
  - Requirement: explicit budgets (max hops/calls/time) + early-stop policy.
- **Rate limiting is mandatory for expensive endpoints**:
  - Requirement (canonical policy): LLM endpoints must be rate-limited and must have deterministic 429 tests.
- **Monthly quota is mandatory for LLM endpoints**:
  - Requirement: server-side monthly hard quota enforced **before** any provider call.
- **Prompt injection / untrusted retrieval**:
  - Requirement: retrieved content is untrusted; it must not drive actions or bypass policy.
- **Determinism and OpenAPI safety**:
  - Requirement: OpenAPI generation must remain side-effect free; avoid module-level ORM imports on OpenAPI import path.
- **Thin-client policy**:
  - Requirement: iOS/Web clients remain thin adapters; no domain logic duplication on clients.

---

## External references (web, non-canonical)

These are **external** sources used only for alignment and terminology. They are **not** Source of Truth for runtime behavior.

### RAG / prompt injection / untrusted retrieval

- AWS Prescriptive Guidance: “Best practices to avoid prompt injection attacks” — `https://docs.aws.amazon.com/prescriptive-guidance/latest/llm-prompt-engineering-best-practices/best-practices.html`

### Self-verification / solver-verifier patterns (LLM reliability)

- OpenReview: “Beyond Solving: A Closer Look at LLMs as Solution Verifiers” — `https://openreview.net/forum?id=I0yfD1zLZI`

### Uncertainty quantification / calibration (LLMs)

- OpenReview: “Textual Bayes: Quantifying Uncertainty in LLM-Based Systems” — `https://openreview.net/forum?id=VPmsAr1OTl`
- OpenReview: “Cross-Model Disagreement for Uncertainty Quantification” — `https://openreview.net/forum?id=lOoRJo8xWy`

### Digital coaching / safety boundaries (non-therapy)

- ICF: “Artificial Intelligence Coaching Framework” (v0.16) — `https://coachingfederation.org/app/uploads/2024/06/The-ICF-Artificial-Intelligence-Coaching-Framework-and-Standard-v0.16.pdf`

---

## Marketing & GTM (moved)

This audit is kept ADR-style. Dev-only positioning notes live here:

- `docs/marketing/GTM_NOTES_DEV_ONLY.md`

---

## Next Actions (staged PR plan)

### Docs / contracts (already in this PR)

- Add new agent files in `.cursor/agents/*` + keep `docs/agents/index.md` in sync.
- Extend orchestration routing/context docs to include new roles.

### Runtime implementation (follow-up PRs; tracked in ledger)

- **Ledger item:** “Orchestration: implement AI multi-agent contracts (RAG/UQ/CV + safety) — runtime follow-up”
  - See `docs/roadmap/BACKLOG_LEDGER.md` (P1).

Suggested PR sequence (non-binding):

1. Implement **RAG grounding contract** (response schema includes `sources[]`) + deterministic tests.
2. Implement **UQ/confidence contract** (confidence fields + degrade behavior) + calibration tests (where applicable).
3. Implement **recursive budgets** (max hops/calls/timeouts) + anti-abuse tests (429 + quota).
4. Implement **CV MVP** (contract-only endpoint or offline pipeline) with confidence + graceful degradation.

---

## Appendix A — Draft contracts (moved)

To keep this audit ADR-style, the draft contract text was moved to:

- `docs/orchestration/contracts/AI_OUTPUT_CONTRACTS.md`
- `docs/orchestration/contracts/SAFETY_LANGUAGE_POLICY.md`
