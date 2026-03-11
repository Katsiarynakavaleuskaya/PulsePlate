# OpenAI-First External Docs Freshness Pilot — Decision

**Date:** 10 March 2026 (`America/New_York`)
**Status:** Decision (docs + command-evidence pilot)
**Scope:** Dev-agent docs freshness only; no runtime product changes

---

## 1. Executive Summary

**Decision:** keep the repo-native context lane as canonical, keep `openai-docs`
as the default OpenAI source, and choose **Context7** as the optional pilot
winner for live MCP integration in Codex/Cursor.

**Context Hub** remains in the comparison set as the OSS comparator, but it is
not the first-choice pilot for this repo's OpenAI-first use case as of
`10 March 2026`.

Pilot owner and lifecycle:

- Owner: `@katsiaryna_kavaleuskaya`
- Timeline: one review cycle after PR `#1100`, then explicit keep/adjust/stop
  decision
- Ledger item:
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-openai-docs-freshness-pilot`

Why:

- PulsePlate already has deterministic repo context bootstrap and skill routing:
  `scripts/orchestration/context_pack.py:14`,
  `scripts/orchestration/task_bootstrap.py:45`,
  `docs/dev/CODEX_SKILLS.md:32`.
- Canonical project learning must stay in git through KPP, not in hidden local
  agent notes: `docs/memory/kpp_knowledge_promotion_pipeline.md:11`,
  `docs/memory/kpp_knowledge_promotion_pipeline.md:32`,
  `docs/memory/kpp_knowledge_promotion_pipeline.md:43`.
- Official OpenAI guidance for new work points to the **Responses API**, which
  is the exact failure mode this pilot is trying to prevent:
  <https://platform.openai.com/docs/guides/responses-vs-chat-completions>.

Exit criteria:

- Success metric: on repeated OpenAI integration prompts, the chosen lane
  produces Responses API-oriented, source-linked answers without invented
  parameters.
- Graduation criteria: the runbook stays accurate for one review cycle, at
  least one durable insight is promoted through KPP, and the optional lane does
  not require CI/runtime changes.
- Rollback triggers: stale or unsafe auth guidance, repeated OpenAI lookup
  misses versus official docs, or pressure to treat external caches/annotations
  as repo canon.

---

## 2. Repo Fit Constraints

### 2.1 What is already canonical here

- Repo context pack is deterministic and source-controlled:
  `scripts/orchestration/context_pack.py:14`
- Coordinator bootstrap already carries context + recommended skills:
  `scripts/orchestration/task_bootstrap.py:69`
- `openai-docs` is already explicitly approved for matching tasks:
  `docs/dev/CODEX_SKILLS.md:64`

### 2.2 What external tools must not become

- External doc caches, MCP outputs, and local annotations must not become
  canonical policy by accident.
- Durable learning must be promoted through KPP into exactly one repo artifact:
  `docs/memory/kpp_knowledge_promotion_pipeline.md:32`

---

## 3. Pilot Inputs And Spot-Check Evidence

### 3.1 Official OpenAI baseline

- Source checked on `10 March 2026`: OpenAI docs page
  <https://platform.openai.com/docs/guides/responses-vs-chat-completions>
- Pilot criterion: a winning tool must help the agent prefer **Responses API**
  over legacy Chat Completions patterns.

### 3.2 Context Hub CLI spot-check

Command: `npx -y @aisuite/chub --help`

Raw stdout:

```text
Usage: chub [options] [command]

Context Hub - search and retrieve LLM-optimized docs and skills
```

Exit code: `0`

Command: `npx -y @aisuite/chub search openai --json`

Raw stdout:

```text
{
  "results": [
    {
```

Exit code: `0`

Command: `npx -y @aisuite/chub search responses openai --json`

Raw stdout:

```text
{
  "results": [],
  "total": 0,
```

Exit code: `0`

Interpretation:

- `Context Hub` is real, usable, and OSS-friendly for CLI lookup.
- In this terminal spot-check, it did **not** surface a dedicated OpenAI
  `responses` hit, which weakens it for an OpenAI-first freshness pilot.

### 3.3 Context7 packaging spot-check

Command: `npx -y @upstash/context7-mcp --help`

Raw stdout:

```text
Usage: context7-mcp [options]

Options:
```

Exit code: `0`

Interpretation:

- `Context7` is packaged as a direct MCP server, which matches the primary
  integration surface for Codex/Cursor.
- Its published setup instructions include explicit Codex/Cursor MCP config
  examples, which reduces integration ambiguity for dev agents.

---

## 4. Comparison And Decision

| Lane | Strength in this repo | Weakness in this repo | Decision |
| --- | --- | --- | --- |
| Repo-native + official OpenAI docs | Deterministic, governed, already approved | No live third-party docs retrieval layer by itself | Keep as baseline |
| Context7 | Direct MCP fit for Codex/Cursor; version-specific docs positioning | External service lane; not canonical memory | **Pilot winner** |
| Context Hub | OSS, CLI-first, skill-copy workflow, local annotations | OpenAI-first lookup signal was weaker in the live spot-check; annotations are non-canonical | Keep as comparator |

**Decision note:** this is a repo-fit decision, not a universal product verdict.
`Context Hub` may still be useful for OSS/local workflows, but it is not the
first local adoption target for this repo's OpenAI-first pilot.

---

## 5. Implementation Boundaries

### IN

- Docs-only runbook for local setup and verification
- Optional local MCP/config examples
- Explicit governance rule for KPP promotion

### OUT

- CI integration
- Runtime app code
- OpenAPI generation path
- Production endpoints
- Hidden local notes promoted as policy

---

## 6. Security Notes

- Treat external docs tools as untrusted input surfaces.
- Do not auto-promote MCP output or local annotations into repo canon.
- Prefer project-scoped examples where the client supports them.
- Never commit API keys or local tool tokens.

---

## 7. Marketing & GTM

- This rollout is internal-only.
- Success metric is faster, more correct agent output for OpenAI integration
  tasks, not user-facing feature velocity.
- If the pilot stays useful for one review cycle, package it as a short team
  enablement pattern with a narrow "use / do not use" note.

---

## 8. Chosen Next Step

1. Keep repo-native context + `openai-docs` as the canonical baseline.
2. Add a local-only runbook with:
   - `Context7` as the first MCP lane
   - `Context Hub` as the CLI/OSS comparator
3. Reuse one OpenAI-first prompt pack for future spot-checks.
4. Promote only durable findings through KPP.
5. Track pilot graduation or rollback in
   `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-openai-docs-freshness-pilot`.

---

## References

- OpenAI docs: <https://platform.openai.com/docs/guides/responses-vs-chat-completions>
- Context Hub repo: <https://github.com/andrewyng/context-hub>
- Context Hub npm: <https://www.npmjs.com/package/@aisuite/chub>
- Context7 repo: <https://github.com/upstash/context7>
