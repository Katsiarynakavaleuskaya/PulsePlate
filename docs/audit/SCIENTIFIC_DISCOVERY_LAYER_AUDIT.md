# Scientific Discovery Layer (SDL) — Audit

**Status:** Canonical SDL rationale artifact for the governed `creative_research` sub-lane
**Topic PR:** PR #1131 (Docs-only canonicalization)
**Branch:** `docs/sdl-audit-canonicalization-cleanup`
**Scope:** rationale / audit only (docs / dev-process), **no runtime impact**
**Date:** 12 March 2026

---

## Executive summary (RU)

Этот аудит фиксирует **Scientific Discovery Layer (SDL)** для PulsePlate: dev-only процесс и контракт, который
системно превращает “идеи” в **фальсифицируемые гипотезы**, отбрасывает мусор через
логико-философские/безопасностные/доменные фильтры и продвигает только то, что имеет
**воспроизводимую проверку** (протокол + критерии успеха + отрицательные контроли).

SDL **не** заменяет RAG/Logic/Bayes/CBT/CV. Он **оркестрирует** их в научном цикле:
Observation → Hypothesis → Protocol → Evidence → Promotion/Reject.

Ключевой принцип:

> “Новое знание существует только если есть воспроизводимая проверка”.

---

## Executive summary (EN)

This audit defines a **Scientific Discovery Layer (SDL)** for PulsePlate as a dev-only rationale and contract for the
governed `creative_research` sub-lane. It turns ideas into **falsifiable hypotheses**, filters low-quality proposals using
philosophy/logic/safety/domain constraints, and promotes only what has **reproducible validation**
(protocol + success criteria + negative controls).

SDL is a conceptual framing layer. It supports `creative_research` but does not replace the existing experimentation umbrella.

---

## Canonical references (single source of truth)

**Evidence anchors:**
- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:5-9`
- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md:34-54`
- `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md:13-32`

### Orchestration canon

- `docs/orchestration/workflow.md` (canonical workflow + Pre-flight Checklist SoT)
- `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md` (handoff format)
- `docs/orchestration/PARALLEL_WORK_PROTOCOL.md` (parallel tracks + sync points)
- `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md` (authoritative experimentation umbrella)
- `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md` (canonical `creative_research` task-class contract)

### Existing insight / scientific corpus (inputs; non-canonical)

- `docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md` (baseline analysis; gaps)
- `docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md` (scientific framing)
- `docs/insights/*` (philosophy/logic reliability, recursive methods, speed/perf analysis)
- `docs/roadmap/BACKLOG_LEDGER.md` (plans, already-shipped P0 guardrails around `/insight`)

### Related audit (orchestration baseline)

- `docs/audit/UNIVERSAL_AGENT_ORCHESTRATION_LAYER_AUDIT.md` (universal orchestration layer audit)

---

## System boundaries (SoT + safety)

### What SDL is

- A **dev-only rationale layer** for producing scientific artifacts: hypotheses, protocols, eval plans, and PR-ready acceptance criteria.
- A way to ensure multi-agent “research” does not become product behavior without tests.
- A supporting design lens for `creative_research`, not a second orchestration constitution.

### What SDL is not

- Not a runtime feature.
- Not an excuse to add speculative claims to product copy.
- Not a replacement for existing hard guardrails (VIP gating, rate limiting, monthly quota).
- Not a public creativity endpoint.
- Not a path to hidden memory, runtime autonomy, or autonomous merge behavior.

---

## 1) Goal of the layer

SDL must:

1. Generate hypotheses (divergent thinking allowed).
2. Filter via constraints (safety/domain/logic/evidence).
3. Rank by expected value (Bayesian/EV thinking; cost-aware).
4. Produce a reproducible artifact: protocol + metrics + acceptance criteria (and negative controls).

**DoD for a “discovery”:**

- Hypothesis (falsifiable)
- Protocol (reproducible)
- Success criteria (quantified)
- Negative controls (≥2)
- Decision (promote / reject / inconclusive) + rationale

---

## 2) Taxonomy of knowledge (operational)

1. **Observation** — anomaly / metric / failure pattern.
2. **Hypothesis** — explanation that can be falsified.
3. **Model/Theory** — compact structure making predictions.
4. **Protocol** — how to test: data → method → metric → acceptance criteria.

**Promotion rule:** Observation alone is never promoted to canon.

---

## 3) Canonical discovery loop (process)

### 3.1 Pipeline (mandatory order)

1. **Problem framing** (which metric: quality / cost / latency / safety).
2. **Anomaly harvesting** (collect failures: logs, test failures, user feedback).
3. **Hypothesis generation** (divergent).
4. **Constraint filtering** (philosophy/logic/safety/domain boundaries).
5. **Bayesian ranking** (expected value, probability of success, cost of test).
6. **Experiment design** (offline eval, synthetic tests, ablation, shadow-mode — as allowed).
7. **Execution** (minimal artifact; docs/tests in follow-up PR).
8. **Peer review** (agents as critics; bounded dialogue).
9. **Promotion / Rejection** (artifact to ledger/PR or rejection with reason).

Operational shorthand used by the merged creative-research lane:

```text
diverge
 -> cluster
 -> synthesize
 -> critique
 -> verify
 -> score
 -> promote/defer/discard
```

Evidence: `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md:62-72`

### 3.2 Stop conditions

- Anything that violates wellness-only boundaries or introduces medical/therapy positioning.
- Anything that would require runtime changes in a docs-only PR.
- Anything that increases provider-call amplification without explicit budget controls (future runtime PRs only).

---

## 4) New agents (dev-only roles)

SDL introduces two **new Cursor agents** (docs-only in this PR):

### 4.1 `epistemology-discovery-agent`

**Role:** engineer of scientific knowledge.

**Does:**
- Turn ideas into falsifiable hypotheses.
- Enforce negative controls.
- Enforce maturity model (“research readiness”).
- Orchestrate peer review (Logic/Philosophy/Bayes/DS/ML/Security).

**Does not:**
- Make product decisions.
- Promote anything to canon without evidence.
- Implement runtime behavior without coordinator.

### 4.2 `physics-sensor-agent`

**Role:** sensor/measurement invariants for multimodal inputs (camera/mic).

**Does:**
- Defines sensor priors (noise, lighting, perspective, SNR).
- Proposes physics-grounded robustness tests (augmentations, calibration, bounds).
- Defines what we measure (dish vs ingredients vs portion; ASR-only vs voice commands).

**Does not:**
- Use “quantum” framing as an explanation for improvements.
- Claim physical effects without a relevant hardware model.

---

## 5) How “postmodern divergence” fits without breaking science

- **Divergent framing** is allowed to generate alternative hypotheses.
- **Promotion to canon** requires falsifiability + protocol + evidence.

Rule:

> Postmodern frames are allowed as generators. Science is the filter.

---

## 6) Physics layer (practical, not mystical)

We explicitly restrict “physics” to **classical sensor modeling + Bayesian measurement uncertainty**:

- Camera: exposure/white balance, compression artifacts, blur, perspective distortion.
- Mic: SNR, noise suppression, echo / room impulse response (as models, not mysticism).

**Explicit rejection:**

> “Quantum magic” is rejected as an explanation layer. Metaphors are allowed, physics claims are not.

---

## 7) Audit questions (checklist)

### A) Scientific Discovery Layer

1. What is the single #1 pain metric? (hallucination rate, groundedness, latency/cost, CV error, etc.)
2. Where are the observation sources? (logs, tests, traces, user feedback)
3. What “lab notebook” format is canonical? (audit docs vs research logs)
4. Which experiment types are allowed in iteration 1? (offline eval / synthetic / ablation / shadow-mode)
5. What are hard safety stop conditions?
6. What is the promotion threshold? (∆metric, CI, replication count, budget)

### B) Epistemology & Discovery Agent

1. Which claim types must be formalized? (causal/statistical/normative/CBT)
2. Minimum negative controls (≥2): what are they?
3. Allowed sources: repo-only vs scientific articles (and how cited)?
4. Status taxonomy: hypothesis / supported / rejected / inconclusive.

### C) Physics & Sensor Modeling Agent (multimodal)

#### Camera
- Target capture conditions (indoor/outdoor/low light/motion blur)?
- MVP measurement: dish-level vs ingredients vs portion vs barcode/label?
- Scale calibration: reference object / AR ruler / depth / none?
- Distortions to model: perspective, WB, noise, compression, blur.
- Priority: accuracy vs calibrated uncertainty?

#### Microphone
- Extract: ASR text, commands only, or emotion/prosody (if ever)?
- Conditions: noise environments + languages.
- Confidence calibration required?
- Priors: SNR, denoise, echo models.

---

## Security Notes

- SDL can amplify cost if it triggers many LLM “experiments”. Future runtime PRs MUST have explicit budgets and quotas.
- Any coaching-related experiments must enforce wellness-only boundaries and explicit disclaimers.
- Retrieved/external content remains untrusted (prompt injection posture).
- No hidden memory, no autonomous merge, and no runtime autonomy are allowed through this rationale layer.

---

## Marketing & GTM (framing)

Do not sell SDL as “we do science”. Sell it as:

- “evidence-driven coaching with uncertainty + reproducible improvements”

---

## Decision

- **ACCEPT:** SDL (dev-only), `epistemology-discovery-agent`, `physics-sensor-agent`
- **REJECT:** “quantum magic” as an explanatory layer
