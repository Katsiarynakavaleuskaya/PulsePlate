# Innovation Evaluation Framework (Deterministic Scorecard)

**Purpose:** Provide a deterministic, repo-native way to evaluate “innovation proposals” (AI features, RAG patterns,
CV flows, orchestration improvements) and decide **do now vs defer** without hand-wavy narratives.

**Status:** Canonical (dev-only). This document adds *innovation-specific* evaluation dimensions; it does not replace
the canonical research track scorecard.

**Anti-drift rule:** The canonical web/OSS research deliverables and baseline scorecard live in
`docs/orchestration/RESEARCH_TRACK_PROTOCOL.md` (`docs/orchestration/RESEARCH_TRACK_PROTOCOL.md:L1-L6`, `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md:L76-L86`).

Use this framework **in addition** when proposals are novel, cross-cutting, or high-risk.

---

## What qualifies as “innovation” in this repo

An “innovation proposal” is any change that:

- introduces a new AI capability (RAG, coaching, CV, personalization)
- changes budgets/cost dynamics (provider calls, recursion, caching)
- expands the attack surface (untrusted content, external URLs, file uploads)
- creates a new cross-module workflow (agents, protocols, promotion rules)

---

## Evaluation packet (required)

Each proposal MUST be summarized as:

- **Problem statement** (1–3 sentences)
- **Proposed solution** (1–3 sentences)
- **Constraints** (budgets, determinism requirements, “no runtime changes” if docs-only)
- **User value** (who benefits, which tier, how measured)
- **Risks** (top 3; include security and failure modes)
- **Acceptance criteria** (what “done” means)
- **Promotion plan** (ledger/ADR/tests/guards)

If external facts are used → run the Research Track and attach Evidence Log entries.

---

## Scorecard (recommended, deterministic)

### Baseline dimensions (from Research Track)

Keep the baseline dimensions (quality, latency, cost, reliability, determinism) per
`docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`.

### Innovation-specific dimensions (additive)

Score 1 (poor) → 5 (excellent). Provide a 1-line justification per dimension.

- **Safety posture**: prompt injection / untrusted content / data leakage / abuse prevention.
- **Testability**: can we write deterministic tests for success + failure paths?
- **Operability**: observability, failure modes, rollback, rate-limit/quota alignment.
- **Scope discipline**: can this land as a small PR with clear DoD?
- **Maintainability**: avoids duplication; respects layer boundaries; minimal new knobs.
- **User trust** (wellness): avoids medical claims; communicates uncertainty clearly.

---

## Decision rules (minimum)

### “Do now” (green) requires

- clear user value + measurable outcome
- deterministic acceptance criteria
- no known policy conflicts (rate limits/quota/OpenAPI determinism/thin-client)
- an explicit test plan for failure modes (when runtime work begins)

### “Defer” (default) triggers

- missing acceptance criteria
- unclear scope or cross-module blast radius
- cannot define deterministic tests
- unclear safety posture or data/PII boundary

Deferred items MUST be recorded in `docs/roadmap/BACKLOG_LEDGER.md` with DoD.
