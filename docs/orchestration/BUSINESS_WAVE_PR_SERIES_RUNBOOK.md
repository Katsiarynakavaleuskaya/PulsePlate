# Business Wave PR Series Runbook

**Version:** 2026-03-21 (`America/New_York`)
**Scope:** Governance-first business-line wave for B2B collateral automation, director-level business orchestration, and external-facing business materials.
**Execution surface:** `worktrees/business_wave_bootstrap`

## Purpose

This runbook is the canonical operating contract for the business-line wave launched from an isolated worktree.

It exists to keep:
- current dirty runtime/payment work untouched,
- business/executive artifacts documentation-first,
- agent orchestration synchronized with audience-pack SoT,
- collateral generation automated without promoting generated binaries into git.

## Contract Boundaries

- This runbook owns process, merge cadence, sync points, and hard rules for the wave.
- `docs/orchestration/BUSINESS_WAVE_TASK_PACKET_2026-03-21.md` owns branch-scoped success criteria, artifact inventory, and deliverable planning.

## Source of Truth

- Coordinator workflow: `docs/orchestration/workflow.md`
- Canonical orchestration governance contract: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
- Research brainstorming protocol: `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
- Worktree/promotion runbook: `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
- Audience-pack entrypoint: `docs/audience_pack/README.md`
- Facts SoT: `docs/audience_pack/FACTS_CANONICAL.md`
- Narrative/public summary: `docs/audience_pack/INVESTOR_PUBLIC_OVERVIEW.md`
- Freshness/ownership SoT: `docs/audience_pack/LIVING_DOCUMENT_PROTOCOL.md`

## Wave Objective

Build a reusable business-development system around existing repo canon:
- director-level business orchestration,
- B2B proposal and pitch-deck specs in Markdown,
- JS builders that generate `.docx` and `.pptx` from repo-managed specs,
- explicit review/merge cadence for a small PR series.

## PR Series

### PR-1: Bootstrap

- Create the isolated worktree and branch.
- Create the business-wave task packet and brainstorm/research/promotion artifacts.
- Create a thin executive brief that links back to audience-pack canon instead of duplicating facts.
- Record deferred follow-up items in `docs/roadmap/BACKLOG_LEDGER.md`.

### PR-2: Director-Level Agent Contract

- Extend `business-strategist-agent` to director-level ownership.
- Sync all orchestration/index/capability/context references.
- Keep `business-strategist-agent` canonical unless a hard gap remains.

### PR-3: B2B Collateral Automation Foundation

- Add B2B collateral markdown specs under `docs/audience_pack/`.
- Add JS builders under `scripts/business_collateral/`.
- Keep generated `.docx` / `.pptx` files under local-only temp/artifact paths.

### PR-4: Bug-Hunter / Merge / Cleanup

- Run bug-hunter review loop on current head.
- Re-run local gates and merge-readiness checks.
- Merge, sync local clone, prune merged worktree branch, remove temp outputs.

## Routing Card

- Decision question: How should PulsePlate automate business development and B2B collateral generation without breaking coordinator-first governance or duplicating canonical business facts?
- Primary agents: `agent-coordinator`, `business-strategist-agent`
- Secondary agents: `marketing-strategist`, `cursor-specialist-agent`
- Formal reviewer path: `qa-engineer-agent`, `bug-hunter`, `agent-coordinator`
- Recommended skills: `plan-work`, `agents-md`, `docs-sync`, `doc`, `slides`

## Sync Points

1. **Bootstrap locked**
   - Worktree clean
   - Task packet exists
   - Backlog carryover recorded
2. **Agent contract synced**
   - `business-strategist-agent` updated
   - coordinator/context/capability/index refs aligned
3. **Collateral foundation synced**
   - specs added in `docs/audience_pack/`
   - JS builders added in `scripts/business_collateral/`
   - smoke tests pass locally
4. **Merge-ready evidence**
   - `pre-commit run --all-files`
   - `make verify`
   - merge-readiness wrapper on PR head

## Hard Rules

- Do not edit the current dirty branch `feat/b4-billing-truth-closeout`.
- Do not treat external `.docx` or pasted JS snippets as canonical truth.
- Do not copy unsourced claims from external business plan documents or downloaded `.docx` drafts into repo SoT without placeholders or evidence anchors.
- Do not commit generated `.docx`, `.pptx`, montages, PDFs, or temp renders.
- Do not move business logic into clients or runtime routes as part of this wave.
- Do not create a new `business-director-agent` unless the existing role cannot be safely extended.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- `pytest -q tests/test_business_collateral_builders.py` (PR-3+ only, after builders are added)

## Deferred from This Wave

- Runtime completion/audit of `app/routers/business.py` and `core/business_bayesian_analyzer.py`
- Any new public runtime/API surface for business analyzer outputs
- Any executive document layer that duplicates facts already owned by `docs/audience_pack/*`
