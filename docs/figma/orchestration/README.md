# Figma Orchestration Kit (H+P+Pr)

Purpose: run Figma-focused multi-agent sessions with deterministic outputs.

## Mandatory pre-flight

Before any brainstorming/session work, run context refresh first using:

- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`

Record in `01_TASK_ANALYSIS.md`:

- `context_version` (date + commit hash)
- changed-pack snapshot

## Canonical constraints

- Follow global workflow SoT: `docs/orchestration/workflow.md`
- Keep dialogue cap at 3 iterations: `docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md`
- Use research brainstorming protocol when needed: `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`

## Session layout

Create a folder per session:

- `01_TASK_ANALYSIS.md`
- `02_BRAINSTORM_TRACKS.md`
- `03_SYNTHESIS_DECISION.md`
- `04_DOD_CHECK.md`

## Seed session

Initial seeded session is available at:

- `docs/figma/orchestration/sessions/2026-02-18_hpp_seed/`
