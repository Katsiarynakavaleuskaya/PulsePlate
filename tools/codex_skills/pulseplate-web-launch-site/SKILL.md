---
name: pulseplate-web-launch-site
description: Plan, review, and implement PulsePlate launch-site surfaces, landing pages, lead-capture flows, and launch copy while preserving wellness-safe claims and coordinator-first governance.
---

# PulsePlate Web Launch Site Skill

## When To Use

Use this skill when the task touches PulsePlate public web launch surfaces:

- launch-site or landing-page structure,
- waitlist, lead-capture, CTA, or conversion funnel copy,
- SEO/ASO/Product Hunt launch page handoff,
- frontend implementation for public launch pages,
- deploy-adjacent launch workflow planning.

This skill complements `pulseplate-design-launch-system` and
`pulseplate-monetization-gtm`. It does not replace design-token governance,
pricing/subscription policy, or coordinator-owned PR gates.

## Inputs Required

- Coordinator packet or task goal.
- Candidate paths for web/docs/product changes.
- Target audience and launch surface.
- Intended call to action.
- Deploy target only when explicitly in scope.

## Procedure

1. Start from `agent-coordinator` output and preserve the declared role order.
2. Complete REQUIRED READING before edits:
   - `docs/ENGINEERING_LESSONS.md`
   - `RUNBOOK_AGENT.md`
   - nearest scoped `AGENTS.md`
3. Read relevant launch/product docs before edits:
   - `docs/dev/CODEX_SKILLS.md`
   - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
   - `docs/marketing/GTM_NOTES_DEV_ONLY.md`
   - `docs/marketing/WELCOME_GATE_GTM_OUTLINE.md`
   - `docs/product/FREE_PRO_SOFT_PAYWALL.md`
4. Separate launch-site concerns:
   - content and positioning,
   - information architecture,
   - conversion path,
   - frontend implementation,
   - deployment evidence.
5. For implementation work, keep frontend changes thin, token-driven, and aligned
   with existing components.
6. For copy, keep wellness language bounded: no medical, therapy, diagnosis, or
   guaranteed-outcome claims.
7. Run the scoped gates requested by `pulseplate-gates`.

## Output Format

Report:

- launch surface reviewed,
- target audience and CTA,
- files changed or proposed,
- claim-safety notes,
- conversion/funnel notes,
- gates to run,
- deferred follow-ups for anything outside the current PR.

## Guardrails

- Passive helper only. Do not replace `agent-coordinator` or
  `scripts/orchestration/task_bootstrap.py`.
- Do not auto-deploy, auto-merge, or post external marketing assets without
  explicit operator approval.
- Do not add hidden lead capture, broad scraping, or analytics collection beyond
  the approved product contract.
- Do not make regulated health, medical, therapy, diagnosis, or guaranteed
  wellness claims.
- Do not change pricing, billing, or subscription truth without
  `pulseplate-monetization-gtm`.
- Do not override design-token or launch-asset governance owned by
  `pulseplate-design-launch-system`.

## Source Of Truth Links

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/dev/CODEX_SKILLS.md`
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- `docs/product/FREE_PRO_SOFT_PAYWALL.md`
- `docs/marketing/GTM_NOTES_DEV_ONLY.md`
