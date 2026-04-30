<!-- markdownlint-disable MD013 -->
# Task Analysis: PulsePlate Web Make Prototype

**Date:** 2026-04-30
**Task packet:** `72f36df2d589`
**Branch:** `codex/design-prototype-canvas-packet-v1`

## Goal

Create a design-only GitHub packet that reconciles the current Figma Make
`PulsePlate_Web` prototype with repo source of truth and defines follow-up
handoff slices for web, iOS, Figma Design, and Canva launch assets.

## Scope

In scope:

- Figma Make source context from `MrztJU3CQtxhADBbtAsWJ6`
- repo design-governance docs
- web/iOS launch design direction
- Canva reference lane boundaries
- GitHub docs packet and session evidence

Out of scope:

- runtime web code edits
- SwiftUI code edits
- backend/API/schema/auth/billing changes
- Figma writes
- Canva generation/publishing
- Code Connect activation
- production-domain changes

## Coordinator Routing

Declared order:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer` reference review
4. `app-store-release-agent` advisory
5. `monetization-gtm` advisory
6. `qa-engineer-agent`
7. `bug-hunter`

Bootstrap command emitted packet `artifacts/orchestration/task_packets/72f36df2d589.json`.
The local artifact is gitignored and is not committed.

## Policy Context

Loaded:

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/orchestration/AGENTS.md`
- `docs/ENGINEERING_LESSONS.md`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/figma/FIGMA_WEB_IOS_AUTHORITY_RECONCILIATION_PACKET.md`
- `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`

## Initial Gates

Passed before docs edits:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
```

## Risks

- Source can look implementation-ready but remains non-authoritative.
- Copy may include unsupported public proof claims.
- Routing/state shell remains prototype-only.
- Figma Make screenshot is unavailable through the current screenshot tool.
- Computer Use is not surfaced as a callable tool in this session.
