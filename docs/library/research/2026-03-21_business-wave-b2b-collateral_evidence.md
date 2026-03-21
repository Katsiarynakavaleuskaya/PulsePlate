# Research Evidence: Business Wave B2B Collateral

**Date:** 2026-03-21 (`America/New_York`)
**Protocol:** `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
**Decision scope:** business-line PR wave, director-level business orchestration, markdown-driven B2B collateral automation

## Evidence Log

### Repo canonical inputs

- `docs/audience_pack/README.md`
- `docs/audience_pack/FACTS_CANONICAL.md`
- `docs/audience_pack/INVESTOR_PUBLIC_OVERVIEW.md`
- `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md`
- `docs/audience_pack/SALES_SOCIAL_ONBOARDING_BASE.md`
- `docs/audience_pack/LIVING_DOCUMENT_PROTOCOL.md`
- `docs/audience_pack/PROOF_PACK.md`
- `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
- `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`

### Runtime surfaces audited but explicitly left out of this wave

- `app/routers/business.py`
- `core/business_bayesian_analyzer.py`
- `docs/reports/CURRENT_STATUS.md`

### External inputs treated as non-canonical source material

- `ATTACHMENT: PulsePlate_BusinessPlan.docx` (local external draft, non-canonical)
  - Use: business framing input, pricing/partnership idea extraction, B2B deck/proposal inspiration
  - Restriction: not a source of truth; any claim promoted into repo docs must either link to repo evidence or remain a `[VERIFY_*]` placeholder
- User-provided JS snippets for `docx` / `pptx`
  - Use: implementation shape reference only
  - Restriction: narrative text must move into repo-managed markdown specs, not stay hardcoded in builders

## Conclusions

1. `docs/audience_pack/*` is already the correct canonical layer for business and external communication. Evidence: `docs/audience_pack/README.md:15`, `docs/audience_pack/LIVING_DOCUMENT_PROTOCOL.md:16`
2. The missing layer is not a second fact canon; it is a thin executive packaging layer plus deterministic builders. Evidence: `docs/orchestration/BUSINESS_WAVE_TASK_PACKET_2026-03-21.md:16`, `docs/orchestration/BUSINESS_WAVE_PR_SERIES_RUNBOOK.md:29`
3. `business-strategist-agent` should absorb director-level business ownership instead of spawning a duplicate role. Evidence: `.cursor/agents/business-strategist-agent.md:23`, `docs/orchestration/BUSINESS_WAVE_TASK_PACKET_2026-03-21.md:15`
4. Generated partner-facing assets should be built from repo markdown and remain local-only artifacts. Evidence: `docs/orchestration/BUSINESS_WAVE_TASK_PACKET_2026-03-21.md:17`, `docs/orchestration/BUSINESS_WAVE_PR_SERIES_RUNBOOK.md:54`

## Promotion Decision

Promote this evidence into:
- PR-1 governance artifacts and executive brief
- PR-2 agent-contract sync
- PR-3 audience-pack collateral specs and automation scripts
