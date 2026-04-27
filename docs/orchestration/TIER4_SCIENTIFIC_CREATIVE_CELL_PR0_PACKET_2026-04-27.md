# Tier 4 Scientific / Creative Cell — PR0 Task Packet

**Date:** 2026-04-27 (`America/New_York`)
**Status:** Active governance packet for the first Tier 4 lane slice (docs + deterministic router cues only).
**Wave:** coordinator-first; no production runtime changes in this slice.

## Goal

Establish a **repo-canonical** execution contract for the **Tier 4 — scientific / creative cell** (organizational tier in the local agent workforce model) so that coordinator packets, skill routing, and review gates stay aligned without inventing a new `task_classification` label.

## Preconditions

- **Reliability cell (Tier 1 org sense) stable:** Tier 1 CI/CD consolidation wave is materially landed; merge governance and canonical backend/shared lane are documented (canonical packet + runbook: [`TIER1_CI_CD_TASK_PACKET_2026-03-26.md`](./TIER1_CI_CD_TASK_PACKET_2026-03-26.md), [`TIER1_CI_CD_PR_SERIES_RUNBOOK.md`](./TIER1_CI_CD_PR_SERIES_RUNBOOK.md)). PR0 does not reopen Tier 1 scope.
- **Design packet reference:** [`PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md`](./PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md) §8 — Tier 4 introduces *Scientific Insight* and *Creative Concept* roles only after the reliability cell is stable; this PR documents that linkage and defers autonomous execution.

## Mapping to canonical task classes

Tier 4 work in this repository **must** use existing classifier labels only:

- **`creative_research`** — brainstorm, hypotheses, literature-style framing, GTM/research-adjacent ideation bounded by [`RESEARCH_BRAINSTORMING_PROTOCOL.md`](./RESEARCH_BRAINSTORMING_PROTOCOL.md) and [`CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md`](./CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md).
- **`experiment`** — offline eval, benchmarks, ablations bounded by [`AGENT_EXPERIMENTATION_PROTOCOL.md`](./AGENT_EXPERIMENTATION_PROTOCOL.md).

There is **no** eighth `scientific` label; see [`AGENT_SKILL_ROUTING_POLICY.md`](./AGENT_SKILL_ROUTING_POLICY.md) §2a.

## Decision question

How should PulsePlate route Tier 4 coordinator tasks deterministically so that `skill_router` and scoped orchestration docs encode the scientific/creative lane **without** widening runtime, merge authority, or skill execution authority?

## Success criteria

1. Scoped [`docs/orchestration/AGENTS.md`](./AGENTS.md) lists primary agent, phased execution order, mandatory post-open `qa-engineer-agent -> bug-hunter`, and links to this packet.
2. [`skill_router.py`](../../scripts/orchestration/skill_router.py) scores Tier 4 wording and `docs/orchestration/TIER4_*` paths toward `creative_research` (or `experiment` when eval semantics dominate) with deterministic tests.
3. [`BACKLOG_LEDGER.md`](../roadmap/BACKLOG_LEDGER.md) records the epic slice with Owner, Priority, Target PR, Reason, Links, DoD.
4. No OpenAPI, no app runtime behavior changes, no autonomous merge or thread-resolution claims.

## Out of scope

- Product API or schema changes
- New merge blockers or workflow permissions changes
- Hidden agent memory or promotion of brainstorm output without KPP ([`docs/memory/kpp_knowledge_promotion_pipeline.md`](../memory/kpp_knowledge_promotion_pipeline.md))

## Routing (phased — Role-Agent Order Contract)

Declared by **`agent-coordinator`** per task; phases are **sequential**, not a flat parallel stack of every domain agent.

| Phase | Purpose | Agents (example) |
|-------|---------|------------------|
| A | Scope lock, backlog alignment | `agent-coordinator` |
| B | Privileged/script surface review when `scripts/orchestration/**` changes | `security-auditor` |
| C | Scientific / epistemic framing | `epistemology-discovery-agent`, `data-scientist-agent`, `rag-systems-agent`, `logic-agent`, `philosophy-agent` |
| D | Wellness-safe language | `nutritionist-agent`, `cbt-psychologist-agent`, `bayesian-uq-agent` |
| E | Architecture / AI product boundaries | `ai-app-architect`, `ai-innovation-specialist` |
| F | Optional trends / market context (advisory only) | `ai-trend-reporter` |
| G | Implementation when code changes | `backend-engineer`, `ml-engineer-agent` |
| H | **Mandatory post-open** | `qa-engineer-agent` → `bug-hunter` |

Optional: `cursor-specialist-agent` when `.cursor/**` or Codex skill surfaces change; `designer-artist-agent` when runbook visuals are in scope.

## Skill helpers (advisory)

- Always: `pulseplate-workflow`, `pulseplate-gates`
- Review / governance: `pulseplate-pr-review`, `pulseplate-ledger`, `pulseplate-guards`
- CI: `ci-fix`, `loop-on-ci`, `babysit`
- Bounded external intake: `web-research-agent` only under [`RESEARCH_TRACK_PROTOCOL.md`](./RESEARCH_TRACK_PROTOCOL.md)

## Deliverables (PR0)

- This packet (linked from workforce design packet §8).
- `docs/orchestration/AGENTS.md` Tier 4 lane block.
- Ledger anchor + router/tests as specified in the PR body.

## Execution record

Phased agent-pass and verification evidence for PR #1548 (no synthetic logs): [`TIER4_PR1548_AGENT_PASS_RECORD_2026-04-27.md`](./TIER4_PR1548_AGENT_PASS_RECORD_2026-04-27.md).

## Deferred / follow-ups

- Tier 4 PR1+ slices (optional launcher hooks, additional eval harnesses) must open as separate backlog-backed PRs with their own packets.
