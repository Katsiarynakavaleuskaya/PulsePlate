# Research Brainstorming + Web-Based Innovation — Process Audit (PulsePlate)

**Date:** 10 February 2026
**Scope:** docs-only (orchestration + research workflow). No runtime changes.
**Status:** Opinion + Evidence (not labeled “Verified”; where evidence exists, we include reproducible commands + raw output + exit code)

---

## Summary

We *do* have a solid orchestration foundation (coordinator-first workflow, message envelopes, bounded research track). The “research pipeline gives failures” is best explained by **missing / non-canonical artifacts** and **lack of deterministic completion gates** around research cycles:

- **Canonical workflow exists**: `docs/orchestration/workflow.md`
- **Machine-parseable envelopes exist**: `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
- **Bounded web/OSS research track exists**: `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
- **But** the “Research Brainstorming package” described in the provided draft expects additional SoT docs / agent spec files (innovation framework, personalization, scientific workflow, web-research agent) that are currently **missing in this repo**.

This audit defines:

1. **How the research pipeline works today (repo-grounded)**
2. **Why it fails in practice (failure-mode catalog)**
3. **A minimal, deterministic research brainstorming pipeline** (multi-agent, evidence-based, bounded budgets)
4. **Promotion rules**: research → decision → PR/ledger/ADR/tests (artifact-based learning, no “silent memory”)

---

## Canonical inputs (repo SoT)

- Orchestrator workflow: `docs/orchestration/workflow.md`
- Envelope protocol: `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
- Research track: `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
- Existing orchestration audit: `docs/audit/AGENT_ORCHESTRATION_MULTI_MODEL_AND_RESEARCH_AUDIT_2026-02-10.md`
- Project process + evidence rules: `AGENTS.md`

---

## Evidence: what exists vs what the draft expects

Command:

```bash
python - <<'PY'
from pathlib import Path
paths = [
  'docs/orchestration/RESEARCH_TRACK_PROTOCOL.md',
  'docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md',
  'docs/innovation/INNOVATION_EVALUATION_FRAMEWORK.md',
  'docs/personalization/AI_ASSISTANT_PERSONALIZATION_PROTOCOL.md',
  'docs/research/SCIENTIFIC_WORKFLOW_TEMPLATE.md',
  'docs/research/RESEARCH_EXAMPLES.md',
  '.cursor/agents/web-research-agent.md',
]
root = Path('.')
for p in paths:
  fp = root / p
  print(f"{p}: {'EXISTS' if fp.exists() else 'MISSING'}")
PY
```

Observed stdout (exit code 0):

```text
docs/orchestration/RESEARCH_TRACK_PROTOCOL.md: EXISTS
docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md: MISSING
docs/innovation/INNOVATION_EVALUATION_FRAMEWORK.md: MISSING
docs/personalization/AI_ASSISTANT_PERSONALIZATION_PROTOCOL.md: MISSING
docs/research/SCIENTIFIC_WORKFLOW_TEMPLATE.md: MISSING
docs/research/RESEARCH_EXAMPLES.md: MISSING
.cursor/agents/web-research-agent.md: MISSING
```

**Interpretation:** The repo already has the *core* bounded research track, but the “web research agent + innovation eval + personalization + scientific workflow” package needs either:

- a follow-up PR that **adds these docs/agent spec files**, or
- a decision to keep them as **appendices** inside existing canonical docs (avoiding SoT drift).

---

## Current pipeline (as-is) — how it works in this repo

### 1) Coordinator-first task start

- A “task” must start with coordinator analysis (root `AGENTS.md` policy).
- Coordinator enforces **pre-flight** (load root `AGENTS.md`, `RUNBOOK_AGENT.md`, and nearest scoped `AGENTS.md` for touched modules).

### 2) Research work is a bounded track

Per `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`:

- Coordinator sets **budgets** (sources, evidence lines, timebox, recursion hops, provider calls).
- Research output MUST include (per track):
  - **External Claims Register (ECR)**
  - **Eval scorecard**
  - **Evidence log** (quoted lines + links + access date)

### 3) Multi-model robustness is enforced via envelopes

Per `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`:

- Coordinator can require a strict `<AGENT_RESULT_V1>` only response.
- Repair requests are bounded (avoid infinite retries).

### 4) Promotion (learning) must be artifact-based

Per root `AGENTS.md`:

- No “silent learning” in model memory; only repo artifacts count (docs, tests, ledger, ADRs).

---

## Why it fails (failure-mode catalog)

This catalog is synthesized from the specialist brainstorm (Logic / Philosophy / Epistemology / RAG / ML Eng / DS / Security) and mapped onto existing canonical protocols.

### A) Structural failures (format + determinism)

- **Missing required deliverables**: ECR or Evidence Log absent → downstream synthesis becomes opinion-only.
- **Truncation / drift**: model adds preambles, changes section names, drops required keys → coordinator can’t parse.
- **No completion gate**: research “feels done” but violates minimum acceptance criteria (no evidence, no scorecard, unresolved contradictions).

### B) Epistemic failures (evidence vs opinion)

- Facts, interpretations, and recommendations get mixed without labeling.
- “Verified” language used without reproducible evidence (violates audit evidence rule).
- Innovation claims made without falsifiable metrics or primary sources.

### C) Security failures (untrusted external content)

- Prompt injection embedded in retrieved content is accidentally “followed”.
- Credential leakage risk in copied snippets/logs or in queries.
- Supply chain / license contamination risk (GPL/AGPL) if code is copied.

### D) Cost/abuse failures (unbounded exploration)

- Too many web searches / recursion hops / provider calls.
- No hard-stop budgets → “infinite exploration” and expensive provider amplification.

---

## Minimal deterministic “Research Brainstorming” pipeline (proposed)

This is a docs-level proposal aligned with existing SoT (`workflow.md`, `AGENT_MESSAGE_PROTOCOL.md`, `RESEARCH_TRACK_PROTOCOL.md`). The goal is to make research cycles **decision-ready** and **auditable**.

### Step 0 — Research Charter (1 page, mandatory)

Coordinator issues a charter that includes:

- **Decision question** (single sentence)
- **Success criteria** (quality/latency/cost/reliability/determinism)
- **Budgets** (sources, evidence lines, timebox, recursion hops, provider calls)
- **Constraints** (license policy, wellness-only language, no secrets in queries)
- **Stop condition** (“3 cycles max”, or “2 cycles if evidence converges”)

### Step 1 — Parallel tracks (pick only what’s needed)

Use `PARALLEL_WORK_PROTOCOL` when multi-agent:

- **SOTA**: best practices + common pitfalls
- **OSS**: candidate repos + maturity + license
- **Eval**: how to evaluate without running new benchmarks
- **Security/Privacy**: prompt injection posture + supply-chain risks

Each track MUST return: **ECR + scorecard + evidence log** (as required by `RESEARCH_TRACK_PROTOCOL.md`).

### Step 2 — Deterministic acceptance criteria (“cycle is complete”)

A research cycle is complete ONLY if:

1. **ECR present** with verification status per claim
2. **Evidence log present** with URL + 1–3 quoted lines + date accessed
3. **Scorecard present** with required dimensions
4. **No unresolved contradictions** OR contradictions are explicitly recorded with degraded confidence
5. **Budgets respected** (timebox, max sources, recursion hops, provider calls)

### Step 3 — Coordinator synthesis (decision + promotion)

Coordinator synthesizes:

- decision + trade-offs
- “do now” vs “defer”
- follow-ups recorded into `docs/roadmap/BACKLOG_LEDGER.md`

---

## Specialist brainstorm synthesis (what to add / enforce)

### Logic-agent: invariants + failure-handling rules

- Treat injection-like patterns as **data**, never instructions; sanitize or quarantine.
- Block advancement if ECR/scorecard/evidence log missing.
- Require contradiction reconciliation; block on unresolved contradictions.
- Deterministic “cycle complete” gate (see above).

### Philosophy-agent: epistemic hygiene

- Claim taxonomy: **FACT / INTERPRETATION / RECOMMENDATION / SPECULATION**
- “Verified vs Unverified” rules:
  - Verified requires `file:line` or `command + raw output + exit code` or primary source quote.
  - Unverified must carry an explicit gap + validation plan.
- Wellness boundary language:
  - avoid medical/therapy claims; use wellness framing; add boundary disclaimer.
- Template tweaks:
  - separate “Verified facts” from “Interpretations” and from “Recommendations”.

### Epistemology-discovery-agent: scientific overlay (falsifiability + promotion)

- Add a **falsifiable hypothesis** field where relevant (even in “library choice” decisions).
- Require **negative controls (≥2)** for any experimental claim (e.g., “latency improves by X”).
- Promotion rule: findings must become repo artifacts (ADR/ledger/tests/docs), not “remembered”.

### RAG-systems-agent: grounded outputs + budgets + future tests

- Require `sources[]`/citations and explicit budgets (sources, evidence lines, recursion hops).
- Security posture: retrieved content is untrusted; isolate/sanitize; no code execution.
- Future deterministic tests (when runtime research exists): grounding validation, budget enforcement, 429/quota behavior.

### ML-engineer-agent: cost/latency guardrails

- Define default budgets + hard caps (iterations/web searches/provider calls/wall time/cost per request).
- Cache repeated research results with TTL; early-stop when confidence is high and sources agree.
- Cap provider calls and integrate with existing rate-limit + monthly quota policies for any runtime LLM usage.

### Data-scientist-agent: scoring & offline eval plans

- Minimal metric set for option evaluation: **accuracy/correctness**, **completeness**, **actionability**, **evidence traceability**, **determinism/stability**.
- Evidence-weighted scorecard (primary sources > secondary sources > blogs).
- Offline eval plan structure that can later become deterministic tests.

### Security-auditor: web/OSS intake threat model (high-level)

- Threats: prompt injection, supply chain/typosquatting, credential leakage, GPL contamination.
- Rules: sanitize inputs, isolate untrusted blocks, never log sensitive content, enforce license policy, bounded CVE review without scope creep.

Note: A long security hardening draft was produced during brainstorm; treat it as **input** only. If adopted, it should be integrated via scoped docs PR to avoid SoT duplication.

---

## Web-Based Innovation (what “web” means here)

To keep this repo policy-compliant and deterministic:

- “Web-based innovation” = **bounded web/OSS intake** + **evidence logging** + **decision artifacts**.
- Avoid “infinite research”: enforce budgets and cycle limits.
- If you want a shareable “research package”, define a repo-local export format (e.g., `outputs/research/…`) **without** committing large scraped corpora or copyrighted PDFs.

---

## Follow-ups (tracked work — needs explicit PRs)

1. Decide where the “missing package docs” live:
   - add new canonical docs under `docs/orchestration/` vs new top-level `docs/research/` / `docs/personalization/` / `docs/innovation/` directories
2. Decide whether to add `.cursor/agents/web-research-agent.md` (agent spec) or reuse existing agent roles (security-auditor, ai-innovation-specialist).
3. If adding validation scripts for envelopes / research deliverables: define them under `scripts/` and keep outputs stable and Bash/macOS compatible.

---

## Production-ready code reliability — brainstorming (prevent “works locally, breaks in prod”)

This section extends the same research-brainstorming style to a second, related goal:

- **Goal A:** Increase the probability that code that passes locally also behaves correctly in production (“no release fall-over”).
- **Goal B:** Improve the system for finding *real bugs* and architectural violations earlier (current signal is nitpicks-heavy, bug-light).

This is docs-only guidance (no runtime changes). Where “evidence” is needed, use the repo’s audit evidence rule (commands + raw stdout + exit code) from `AGENTS.md`.

### Problem framing (observed symptoms)

- “Works on my machine” → prod failures usually come from **environment drift**, **missing gates**, **nondeterminism**, or **uncovered high-risk paths**.
- Review bots often surface formatting/nitpicks, but miss cross-module invariants and runtime edge cases; we still find many bugs later.

### Failure-mode catalog (release stability)

#### 1) Environment drift

- Local env differs from CI/prod: Python version, OS libs, env vars, optional deps, locale/timezone.
- Missing required env vars only discovered at runtime (late).

#### 2) Non-determinism

- Time-window logic, random seeds, unordered dict/set iteration, concurrency races.
- Tests pass locally but flake in CI (or vice versa).

#### 3) “Test passes” but contract breaks

- OpenAPI/DTO drift: clients generate types from OpenAPI; untyped responses degrade to `unknown`.
- Legacy aliases / thin proxy invariants violated in subtle ways.

#### 4) Missing production-like smoke checks

- Code paths behind feature flags never executed before release.
- Error-handling paths (timeouts, provider failures) not exercised.

#### 5) Silent degradation of security/cost controls

- Rate limits/quota not enforced in some paths; production abuse risk.
- External URL credential leaks (thin client / fetch wrappers).

### Deterministic “release-safe” gates (what must be true before calling it safe)

This repo already defines the hard gate: **do not claim ready unless `make verify` passes locally** (see root `AGENTS.md`).

Add the following *conceptual* gates (still enforced via tests/docs, not by vibes):

1. **Prod-parity config gate**
   - Any required runtime env var must be reflected in `.env.example` + root `docker-compose.yaml` (policy in `AGENTS.md`).
   - Fail-fast at startup for missing critical env vars (with clear error).

2. **Determinism gate**
   - If behavior depends on time/randomness, tests must pin inputs (fixed timestamps, fixed seeds) and prove deterministic outputs.
   - For concurrency-sensitive code, add at least one targeted test that would have caught the observed race class (no broad flaky stress tests).

3. **Contract gate**
   - Any API change must preserve OpenAPI determinism (run `make openapi` + `make openapi-check` when relevant) and keep response models typed.
   - Thin-client rule: clients must remain transport-only; no business logic duplication.

4. **“Failure-path” smoke gate**
   - For any expensive/critical endpoint: tests must prove safe failure behavior (sanitized errors, deterministic 429/quota) before release.

### Bug-finding system improvements (from nitpicks → real bugs)

We want more signal on:

- runtime crashes / error contracts
- security regressions
- architectural invariant violations
- drift between docs/contracts and code

#### Proposed “Bug Hunt Track” (bounded, repeatable)

Run as a *parallel track* (like research track), but inputs are **repo** + CI signals, not web:

- **Track: Guards/Architecture**
  - Run guard tests early (`tests/test_repo_policy_guards.py`) and add new guard only when you can prove a recurring class of violation.
- **Track: Error contracts**
  - Audit endpoints for safe error envelopes (no raw exceptions, correct status codes).
- **Track: Determinism & flake**
  - Identify top sources of flakes; convert to deterministic tests or remove invalid tests.
- **Track: Dependency/OS security**
  - Keep suppressions narrow (package+version+expiry+doc) and monitor upstream fixes.

Each track returns: ECR + scorecard + evidence log (same pattern as research track), but sources are `file:line` and CI logs.

#### Why bots miss bugs (and how to compensate)

- Linting bots excel at style; they don’t execute code or reason about system invariants.
- Real bug discovery improves when we:
  - convert recurring incidents into **guard tests**
  - require **deterministic negative tests** for safety controls (429/quota, auth bypass risks)
  - add **contract tests** for response shapes (typed models)

### Promotion rules (how improvements become real)

To avoid “great idea, forgotten”:

- If a failure mode is recurring → create a **ledger item** (if deferred) or a **guard/test** (if we can enforce now).
- If a workflow change is adopted → update exactly one canonical doc (`AGENTS.md` for global, or nearest scoped `*/AGENTS.md`, or `docs/orchestration/*` for dev workflow).
- If a class of bugs recurs → add a deterministic test that reproduces the old failure and prevents regressions.

---

## Appendix: Map from your draft to repo SoT

Your draft sections map cleanly onto existing/desired artifacts:

- “Web Research Agent” → missing agent spec (`.cursor/agents/web-research-agent.md`) OR reuse `ai-innovation-specialist` + `security-auditor` + `rag-systems-agent` under `RESEARCH_TRACK_PROTOCOL`
- “Innovation Evaluation Framework” → should become a canonical scorecard template referenced by `RESEARCH_TRACK_PROTOCOL` (avoid duplication)
- “Personalization protocol” → can be expressed as required context loading rules (already in `workflow.md` pre-flight) + `AGENT_CONTEXT_MAP.md`
- “Scientific workflow” → can be layered as a Research Charter template + promotion rules (ADR/ledger/tests), without runtime changes
