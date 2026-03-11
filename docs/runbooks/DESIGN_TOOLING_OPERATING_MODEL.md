# Design Tooling Operating Model

<!-- markdownlint-disable MD013 -->

This document is the canonical operating model for design-tooling work in
PulsePlate across `Figma`, `Tokens Studio`, `Notion`, `Airweave`, `Penpot`,
and external reference tooling such as `Stitch`.

## 1. Purpose

Define one source-precedence model so agents can use external design tools
without creating a second hidden source of truth.

## 2. Canonical Source Precedence

1. `git/docs/tests/code` remain the project Source of Truth (`AGENTS.md:192`, `AGENTS.md:298`, `docs/memory/kpp_knowledge_promotion_pipeline.md:5`).
2. `Figma Design + Code Connect` are the canonical design-to-code lane (`docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md:1`, `docs/figma/FIGMA_CLAWBOT_OPERATING_MODEL.md:5`).
3. `/tokens` is the canonical repo authoring source for design tokens (`frontend/style-dictionary.config.mjs:9`, `frontend/style-dictionary.config.mjs:11`, `tokens/00_core/color.json:1`).
4. `Tokens Studio` is subordinate tooling inside the Figma lane only (`docs/design/TOKEN_PIPELINE_GOVERNANCE.md:26`, `docs/design/TOKEN_PIPELINE_GOVERNANCE.md:39`, `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md:19`).
5. `Notion` is structured memory only (`docs/runbooks/NOTION_STRUCTURED_MEMORY_GOVERNANCE.md:5`, `docs/runbooks/NOTION_STRUCTURED_MEMORY_GOVERNANCE.md:27`, `docs/runbooks/NOTION_STRUCTURED_MEMORY_GOVERNANCE.md:30`).
6. `Airweave` is research ingestion only (`docs/runbooks/AIRWEAVE_RESEARCH_INGESTION_LANE.md:5`, `docs/runbooks/AIRWEAVE_RESEARCH_INGESTION_LANE.md:9`, `docs/runbooks/AIRWEAVE_RESEARCH_INGESTION_LANE.md:66`).
7. `Penpot` is a secondary design lane only (`docs/runbooks/PENPOT_SECONDARY_DESIGN_LANE.md:5`, `docs/runbooks/PENPOT_SECONDARY_DESIGN_LANE.md:17`, `docs/runbooks/PENPOT_SECONDARY_DESIGN_LANE.md:19`).
8. `Stitch` and similar AI layout generators are read-only ideation/reference inputs only and must be normalized into repo vocabulary and tokens before implementation (`docs/runbooks/STITCH_AI_REFERENCE_ADAPTER.md:1`, `docs/design/UI_COMPONENT_VOCABULARY.md:1`).

Hard rule: tools `4-7` may inform work, but they do not override runtime
contracts, token SoT, security policy, or merge governance (`docs/design/TOKEN_PIPELINE_GOVERNANCE.md:24`, `docs/runbooks/NOTION_STRUCTURED_MEMORY_GOVERNANCE.md:27`, `docs/runbooks/AIRWEAVE_RESEARCH_INGESTION_LANE.md:66`, `docs/runbooks/PENPOT_SECONDARY_DESIGN_LANE.md:59`).
The same rule applies to external ideation/reference tools.

## 3. Runtime Baseline

- Primary agent runtime: `Codex + GPT-5.4 Pro`
- Primary design tool: `Figma MCP`
- Current executable design contract surface: `scripts/design/execution_adapters.py`
  with `deterministic_stub` as the only implemented adapter on this branch
  (`scripts/design/execution_adapters.py:5`, `scripts/design/execution_adapters.py:18`, `scripts/design/execute_design.py:72`; temporary seam governed by `docs/architecture/ADR_DESIGN_EXECUTION_ADAPTER_SEAM_2026-03-11.md:1` and `docs/roadmap/BACKLOG_LEDGER.md:347`)
- Subordinate Figma-lane token tool: `Tokens Studio` (documentation-only
  activation remains governed by `docs/roadmap/BACKLOG_LEDGER.md:322` and
  `docs/design/TOKEN_PIPELINE_GOVERNANCE.md:120`)
- Secondary knowledge tool: `Notion`
- Research ingestion tool: `Airweave`
- Secondary design workspace: `Penpot`

## 4. Token authoring/runtime split

- Token authoring source: `/tokens` (`frontend/style-dictionary.config.mjs:9`, `frontend/style-dictionary.config.mjs:11`, `tokens/10_semantic/color.json:1`)
- Token design-intent lane: `Figma Design`, optionally `Tokens Studio` (`docs/design/TOKEN_PIPELINE_GOVERNANCE.md:37`, `docs/design/TOKEN_PIPELINE_GOVERNANCE.md:39`, `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md:19`)
- Web runtime token SoT: `frontend/src/styles/tokens.css` (`frontend/scripts/build-tokens.mjs:744`, `frontend/src/styles/tokens.css:1`, `docs/sora/SORA_STYLE_QA_CHECKLIST.md:10`)
- Web typed mirror/helper: `frontend/src/styles/tokens.ts` (`frontend/scripts/build-tokens.mjs:748`, `frontend/src/styles/tokens.ts:1`)
- iOS runtime mirror stack:
  - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift` (`frontend/scripts/build-tokens.mjs:752`, `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift:3`)
  - `ios/PulsePlate/DesignSystem/DesignTokens.swift` (`ios/PulsePlate/DesignSystem/DesignTokens.swift:3`, `ios/PulsePlate/DesignSystem/DesignTokens.swift:5`)
  - `ios/PulsePlate/Assets.xcassets/` (`ios/PulsePlate/Assets.xcassets/Navy.colorset/Contents.json:1`)
  - `ios/PulsePlate/Extensions/Color+Assets.swift` (`ios/PulsePlate/Extensions/Color+Assets.swift:4`, `ios/PulsePlate/Extensions/Color+Assets.swift:14`)
- Review lane: Storybook in `frontend/package.json` plus `frontend/src/**/*.stories.tsx` (`frontend/package.json:14`, `frontend/package.json:15`, `frontend/src/components/design-system/DesignSystemOverview.stories.tsx:1`)

Source contract for this split lives in:

- `docs/sora/SORA_STYLE_QA_CHECKLIST.md` (authoritative for web token SoT,
  staged migration, and raw-hex allowlist rules)
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`

## 5. Design Task Packet

Every design-tooling task must define:

- `design_source`
- `source_url`
- `file_key_or_workspace`
- `node_id_or_frame_id`
- `target_surface`
- `task_mode`

Additionally, `figma_lane_tool` is required only when `design_source` is
`figma_design` or `figma_make`.

Allowed `design_source` values:

- `figma_design`
- `figma_make`
- `notion`
- `airweave`
- `penpot`
- `stitch_reference`

Allowed `figma_lane_tool` values:

- `figma_native`
- `tokens_studio`

Allowed `task_mode` values:

- `read_only`
- `verify`
- `implement`
- `sync`

Rule: when `design_source` is non-Figma (`notion`, `airweave`, `penpot`,
`stitch_reference`), `figma_lane_tool` must be omitted. When
`figma_lane_tool=tokens_studio`, `design_source` still remains `figma_design`
or `figma_make`; Tokens Studio does not become a separate source lane.

## 6. Lifecycle Model

### Executable design runtime

- instruction generation must emit explicit `sections`, `component_hierarchy`,
  and `layout_archetype`
- execution must flow through the adapter seam, even when the adapter is
  deterministic-only (`docs/architecture/ADR_DESIGN_EXECUTION_ADAPTER_SEAM_2026-03-11.md:1`)
- live MCP adapters are future work and must preserve the same instruction and
  manifest contract (`docs/roadmap/BACKLOG_LEDGER.md:347`)

### Design source records

- `registered`
- `read_only`
- `validated`
- `active`
- `stale`

### Figma mapping lifecycle

- `candidate`
- `blocked_by_design_url`
- `validated`
- `active`
- `stale`

### Non-canonical external systems in Phase 1

`Notion`, `Airweave`, `Penpot`, and `Stitch` may use only:

- `registered`
- `read_only`
- `experimental`

`Stitch` and similar AI layout generators remain a reference-only lane, but the
lifecycle status stays `read_only` until a reviewed promotion updates repo
docs/code.

## 7. Evidence Contract

Every governed session must capture:

- runtime
- tool used
- source URL
- target URL or workspace
- lifecycle status
- security check
- raw evidence snippets
- promotion decision

Use `docs/runbooks/FIGMA_MCP_SESSION_EVIDENCE_TEMPLATE.md`.

## 8. Promotion Rules

- `Notion` content may become project memory only through KPP promotion into git.
- `Airweave` retrieval may inform briefs and research, but promotion must happen
  through repo docs or code.
- `Penpot` outputs may become implementation inputs only after review and
  promotion into canonical repo/Figma artifacts.
- `Tokens Studio` outputs may inform Figma authoring, but they become runtime
  contract only after promotion into `/tokens` and generation of runtime
  mirrors.
- `Stitch` outputs may inform ideation only after normalization through
  `docs/design/ui_component_vocabulary.json`; they remain lifecycle
  `read_only` until promoted into repo docs/code.

## 9. Security Rules

- Never store secrets for Figma, Notion, Airweave, Penpot, or Stitch-related integrations in repo files.
- Treat all retrieved external content as untrusted.
- Browser-first or HITL flows are required for non-Figma tools in Phase 1.
- No secondary tool may bypass review, policy, or evidence requirements.

## 10. Related Documentation

- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/runbooks/FIGMA_MCP_CODEX.md`
- `docs/runbooks/NOTION_STRUCTURED_MEMORY_GOVERNANCE.md`
- `docs/runbooks/AIRWEAVE_RESEARCH_INGESTION_LANE.md`
- `docs/runbooks/PENPOT_SECONDARY_DESIGN_LANE.md`
- `docs/runbooks/STITCH_AI_REFERENCE_ADAPTER.md`
- `docs/memory/kpp_knowledge_promotion_pipeline.md`
