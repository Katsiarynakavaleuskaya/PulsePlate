# Pilot: Parallel Task Orchestration (Demo)

- This document demonstrates a minimal, end-to-end example of coordinating two independent subtasks in parallel using the Parallel Work Protocol.
- Objective: show how the Coordinator routes work, aggregates outputs, and records follow-ups without affecting production code.

## Context

- Canonical workflow is defined in docs/orchestration/workflow.md and coordinator behavior in docs/orchestration/AGENT_MESSAGE_PROTOCOL.md.
- The Coordinator-first rule dictates that every new task starts with agent-coordinator analysis and routing.
- Parallel Work Protocol enables independent subtasks to be executed concurrently by different agents.

## Pilot Task

- Task: Design a tiny RAG plan for a hypothetical VIP feature and sanity-check its API surface.
- Subtasks:
  1. ai-innovation-specialist: draft a brief RAG strategy document for the VIP feature.
  2. architecture-specialist: validate the proposed API surface and contract shape for the VIP feature.

## Pre-flight Checklist (as per canonical SoT)

- Load context from docs/orchestration/AGENT_CONTEXT_MAP.md.
- Ensure eligibility of the task for parallel execution (no cross-dependencies).
- Confirm availability of the two target agents and their canonical docs (AI/architecture).
- Record postponed follow-ups in docs/roadmap/BACKLOG_LEDGER.md if any item is deferred.

## Task Analysis & Routing (example)

- Domain touched: AI/ML (RAG), Architecture (API contract).
- Complexity: multi-agent, parallelizable.
- Priority: P1 (demo).
- Capabilities: see agent capability matrix in docs/orchestration/AGENT_CAPABILITY_MATRIX.md.

## Execution Plan (Parallel)

- Create two parallel work streams:
  - Stream A (ai-innovation-specialist): produce a concise RAG plan for VIP feature.
  - Stream B (architecture-specialist): perform a quick API surface sanity check and draft a minimal OpenAPI contract outline.
- After completion, the Coordinator will synthesize the outputs into a single, coherent artifact and produce a DoD brief.

## Outputs & DoD

- Deliverables:
  - ai-innovation-specialist output: brief RAG plan (pdf/text sketch in repo)
  - architecture-specialist output: API surface sketch with endpoints and data types
- DoD: outputs exist, are coherent, and no cross-dependencies exist between streams; risks are documented; backlog items created for any follow-ups.

## Tracking & Post-flight

- Record the pilot in docs/roadmap/BACKLOG_LEDGER.md with owner, priority, and target PR.
- If included in a real PR, attach outputs as comments or files and reference the artefacts in the PR description.

## Notes

- This pilot is non-invasive and does not modify production code. Its purpose is to illustrate the orchestration workflow and ensure the process is understood by the team.

---

Pointers: see
- Coordination: docs/orghestration/workflow.md (canonical)
- Context: docs/orchestration/AGENT_CONTEXT_MAP.md
- Parallel protocol: docs/orchestration/PARALLEL_WORK_PROTOCOL.md
