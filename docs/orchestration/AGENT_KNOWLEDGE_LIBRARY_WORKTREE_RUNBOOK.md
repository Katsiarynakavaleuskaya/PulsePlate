# Agent Knowledge Library Runbook (Worktree + PR from Brainstorm)

**Purpose:** canonical template for running agent-driven knowledge enrichment
in a dedicated worktree and promoting validated outcomes via PR.

**Language note:** examples are written in English for tooling consistency;
teams may keep RU-first discussion and decision context in artifacts when needed.

## 1) Canonical links (SoT)

- Coordinator workflow: [`docs/orchestration/workflow.md`](./workflow.md)
- Capability matrix: [`docs/orchestration/AGENT_CAPABILITY_MATRIX.md`](./AGENT_CAPABILITY_MATRIX.md)
- Brainstorm protocol: [`docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`](./RESEARCH_BRAINSTORMING_PROTOCOL.md)
- Research intake protocol: [`docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`](./RESEARCH_TRACK_PROTOCOL.md)
- Message envelopes: [`docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`](./AGENT_MESSAGE_PROTOCOL.md)
- Parallel tracks protocol: [`docs/orchestration/PARALLEL_WORK_PROTOCOL.md`](./PARALLEL_WORK_PROTOCOL.md)
- KPP (knowledge promotion): [`docs/memory/kpp_knowledge_promotion_pipeline.md`](../memory/kpp_knowledge_promotion_pipeline.md)
- Deferred items ledger: [`docs/roadmap/BACKLOG_LEDGER.md`](../roadmap/BACKLOG_LEDGER.md)
- Orchestration templates:
  - [`docs/orchestration/task_analysis.template.md`](./task_analysis.template.md)
  - [`docs/orchestration/work_review.template.md`](./work_review.template.md)
  - [`docs/orchestration/synthesis.template.md`](./synthesis.template.md)
  - [`docs/orchestration/dod.template.md`](./dod.template.md)

## 2) Worktree bootstrap (separate branch)

```bash
git fetch origin
git worktree add -b worktree/agent-library-<topic> \
  "worktrees/agent_library_<topic>" origin/main
cd "worktrees/agent_library_<topic>"
```

Recommended branch naming:

- `worktree/agent-library-<topic>`
- `feature/brainstorm-<topic>`

## 3) Library structure (project knowledge base)

Use one canonical tree for reusable knowledge artifacts:

```text
docs/library/
  index.md
  brainstorm/
    YYYY-MM-DD_<topic>.md
  research/
    YYYY-MM-DD_<topic>_evidence.md
  decisions/
    ADR_<id>_<topic>.md
  promotion/
    YYYY-MM-DD_<topic>_promotion-log.md
```

Rules:

- One topic = one brainstorm file + one evidence file + one promotion log.
- Reusable invariant/policy goes to one SoT doc only (anti-duplication).
- If item is deferred, record in backlog ledger immediately.

## 4) Mandatory flow (brainstorm to PR)

1. Step 0. Pre-flight
   - owner: `agent-coordinator`
   - input: decision question + constraints
   - output: task framing block
   - gate: required context present
2. Step 1. Brainstorm
   - owner: matrix-routed agents
   - input: framing
   - output: `docs/library/brainstorm/...`
   - gate: options + risks + metrics captured
3. Step 2. Research (optional)
   - owner: `web-research-agent` + coordinator
   - input: external claims
   - output: `docs/library/research/...`
   - gate: claims sourced and bounded
4. Step 3. Synthesis
   - owner: `agent-coordinator`
   - input: brainstorm + evidence
   - output: synthesis section or file
   - gate: clear decision or explicit defer
5. Step 4. Promotion
   - owner: coordinator + domain owner
   - input: chosen decision
   - output: SoT update, ADR, tests, or ledger entry
   - gate: artifact selected (single path)
6. Step 5. PR prep
   - owner: coordinator
   - input: promoted artifacts
   - output: PR description + DoD
   - gate: scope and acceptance checks explicit

## 5) Matrix-driven routing block (fill each cycle)

Copy this block into each brainstorm file:

```md
## Routing Card
- Decision question:
- Success criteria (3-7):
- Constraints:
- Primary agents (from capability matrix):
- Advisory agents:
- Tracks to run in parallel:
- Formal reviewer(s):
```

Reference matrix: [`docs/orchestration/AGENT_CAPABILITY_MATRIX.md`](./AGENT_CAPABILITY_MATRIX.md).

## 6) Evidence contract (non-negotiable)

Every promoted claim must include at least one:

- `file:line` evidence pointer, or
- command + raw output snippet + exit code.

Forbidden:

- unsourced external claims,
- "model remembers" as evidence,
- silent learning outside repo artifacts.

KPP reference: [`docs/memory/kpp_knowledge_promotion_pipeline.md`](../memory/kpp_knowledge_promotion_pipeline.md).

## 7) Promotion log template (fill by agents)

Create `docs/library/promotion/YYYY-MM-DD_<topic>_promotion-log.md`:

```md
# Promotion Log: <topic>

- Date:
- Coordinator:
- Decision:
- Promotion target (choose one): SoT doc | ADR | tests/guards | backlog ledger
- Why this target:

## Evidence
- Evidence 1:
- Evidence 2:

## Deferred items
- Item:
  - Ledger link:
  - Owner:
  - Target PR:
```

## 8) PR template (brainstorm-driven)

Use this structure in PR body:

```md
## Scope (IN / OUT)
- IN:
- OUT:

## Brainstorm Origin
- Brainstorm doc:
- Research evidence doc:
- Synthesis reference:

## Promotion
- Promoted artifact:
- Why this artifact:
- SoT link:

## Validation
- Quality gates run:
- Deterministic checks:

## Deferred / Follow-ups
- Ledger item(s):
```

## 9) How agents enrich knowledge (without drift)

- Agents enrich by **promotion** into repo artifacts, not hidden memory.
- Use one-source policy wording and link to it from other docs.
- Keep raw research evidence separate from canonical policy.
- Convert repeated findings into guard tests where possible.

## 10) Definition of done for one cycle

- Brainstorm artifact exists and is matrix-routed.
- External claims (if any) are backed by evidence.
- Decision is explicit (implement or defer).
- Promotion target is committed in the same PR.
- Deferred items are logged in [`docs/roadmap/BACKLOG_LEDGER.md`](../roadmap/BACKLOG_LEDGER.md).

---

**Status:** active template
**Owner:** `agent-coordinator`
**Last updated:** 2026-02-19
