# PulsePlate Visual Governance Index

Version: v1.0
Last updated: 2026-02-20
Scope: PulsePlate visual generation governance across Sora/Figma/product surfaces

## Purpose

This index is the single navigation map for visual governance.
It defines source-of-truth ownership and prevents silent rule drift.

## Hierarchy (SoT)

1. Identity SoT
   - `docs/sora/prompts/brand_core/FITCHEF_IDENTITY_PROFILE_v1.md`
   - Purpose: mascot identity invariants and continuity markers
   - Owner: `designer-artist-agent`

2. Prompt Engineering SoT
   - `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
   - Purpose: master/nano prompt standards, anti-drift dictionary, release flow
   - Owner: `sora-prompt-engineer`

3. Style QA SoT
   - `docs/sora/SORA_STYLE_QA_CHECKLIST.md`
   - Purpose: pass/fail rubric, failure tags, drift severity (L1-L4)
   - Owner: `sora-prompt-engineer`

4. Prompt Pack SoT
   - `docs/sora/prompts/brand_core/FITCHEF_BRAND_CORE_PROMPT_PACK_v1.md`
   - `docs/sora/prompts/hpp/MASTER_NANO_PROMPT_PACK.md`
   - Purpose: reusable execution-ready prompt families
   - Owner: `sora-prompt-engineer`

5. Throughput + GTM SoT
   - `docs/sora/BRAND_THROUGHPUT_METRICS_GTM_MATRIX.md`
   - Purpose: output velocity and business feedback loop
   - Owner: `ai-trend-reporter` + `marketing-strategist`

6. Icon Dominance SoT
   - `docs/design/APP_STORE_ICON_DOMINANCE_TEST_PROTOCOL.md`
   - Purpose: release gate for icon readability and shelf impact
   - Owner: `designer-artist-agent`

## Rule Introduction Policy

Canonical policy location:
- `AGENTS.md` -> `Visual Governance Policy (Hard Rule)`

This index references that policy and must not duplicate global rule text.

## Figma MCP Integration Contract

- Git docs are the contract layer (decision and rule source of truth).
- Figma MCP is the execution layer (geometry realization, visual verification, variants).
- Geometry must be blueprint-locked in Git before Figma execution.
- Figma outputs that fail SoT checks are rejected even if they look visually strong.
- Icon governance requires `figma_design_url` + `figma_file_key` + `figma_node_id`
  in lock/results/evidence artifacts.
- Figma Make links are non-SoT and cannot satisfy source-of-truth fields.

## Change Control

- Minor clarifications: patch version (`v1.0 -> v1.1`)
- New rule families: minor version (`v1.x -> v2.0`)
- Any governance scope expansion requires explicit rationale in PR description.
