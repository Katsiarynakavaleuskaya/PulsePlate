---
name: pulseplate-design-launch-system
description: Govern PulsePlate design-system readiness, launch asset bundles, token/brand consistency, and fail-closed design packet metadata without bypassing coordinator-first policy or promoting design tooling into execution authority.
---

# PulsePlate Design Launch System

## When to use

- Shaping or reviewing design-system readiness for launch-facing surfaces.
- Governing launch asset bundles that must stay aligned with PulsePlate token and brand SoT.
- Auditing design packet metadata and source precedence before a Figma or code-native design lane becomes execution-ready.
- Validating that Figma, code-native runtime, and token authoring precedence stay aligned with repo-governed design launch rules.

## Inputs required

- Launch/design surface in scope (`design_system_readiness`, `launch_asset_bundle`, `token_brand_consistency`, `design_packet_governance`, or `source_precedence_review`).
- Candidate file paths, packet paths, or design-source paths being changed.
- Expected outcome (`governance-only`, `readiness-review`, or `packet-audit`).

## Procedure (commands)

1. Load design-tooling source precedence and token SoT:

   ```bash
   sed -n '1,220p' docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md
   sed -n '1,220p' docs/design/TOKENS_SOT.md
   sed -n '1,220p' docs/design/TOKEN_PIPELINE_GOVERNANCE.md
   ```

2. Verify fail-closed design packet metadata and launch-governance surfaces before editing:

   ```bash
   rg -n "design_source|source_url|file_key_or_workspace|node_id_or_frame_id|target_surface|task_mode|code_native_design_brief_path|figma_lane_tool|explicit_creation_mode|blocked_by_" docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md docs/design
   rg -n "launch asset|launch assets|brand consistency|token consistency|design system readiness" docs/design docs/runbooks tools/codex_skills
   ```

3. Keep coordinator-first and passive-boundary rules fail-closed:

   ```bash
   python3 scripts/orchestration/check_preflight.py
   python3 scripts/orchestration/check_agent_consistency.py
   sed -n '1,220p' docs/dev/CODEX_SKILLS.md
   ```

## Output format

- `Design launch surface`: exact readiness / asset / governance area touched.
- `Source precedence`: repo/code-native, Figma lane, token authoring, and reference-tool ordering used.
- `Packet status`: required metadata present, missing, or blocked.
- `Evidence`: docs, token surfaces, or policy references used.
- `Boundary notes`: passive discovery-only constraints and any blocked execution steps.
- `Follow-up`: implementation or launch-site work that stays out of scope for this lane.

## Guardrails

- Do not bypass `agent-coordinator` or `scripts/orchestration/task_bootstrap.py`.
- Do not convert this skill into design execution authority or a second control plane.
- Do not treat Figma, Tokens Studio, Notion, Airweave, Penpot, or screenshots as Source of Truth over repo code, tokens, and docs.
- Do not mix this governance skill with `pulseplate-web-launch-site` implementation work.
- Do not promote incomplete design packets into execution-ready state without required metadata and blockers being resolved.
- Do not treat this skill as approval for Figma writes, token publication, asset export, or launch sign-off; it is passive/discovery-only governance.

## SoT links

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/dev/CODEX_SKILLS.md`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
