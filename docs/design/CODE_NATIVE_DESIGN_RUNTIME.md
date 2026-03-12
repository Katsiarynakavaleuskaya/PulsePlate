# Code-Native Design Runtime

Date created: March 11, 2026 (America/New_York)
Status: Active direction
Scope: Primary runtime lane for prompt-to-design work without mandatory Figma

## 1. Purpose

PulsePlate should be able to assemble and render governed UI specs from:

- design tokens in `/tokens`
- canonical vocabulary in `docs/design/ui_component_vocabulary.json`
- layout archetypes and reusable section templates
- code-first screen briefs and prompt contracts

This makes design executable by agent-owned code, without requiring Figma or
similar tools as the primary runtime dependency.

## 2. Source of truth

- `/tokens` remains the token source of truth
- `docs/design/ui_component_vocabulary.json` remains the naming source of truth
- `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md` remains the brief assembly contract
- reusable layout templates are the canonical topology source for sections and
  static component hierarchy. Evidence:
  `scripts/design/layout_templates.py:383`,
  `scripts/design/generate_figma_instructions.py:878`
- generated instruction JSON remains the executable machine contract. Evidence:
  `scripts/design/generate_figma_instructions.py:1047`,
  `scripts/design/contracts.py:138`
- `pulseplate_canvas_v1` is the canonical internal runtime artifact emitted from
  the governed instruction contract. Evidence:
  `scripts/design/canvas_artifact.py:125`,
  `scripts/design/execution_adapters.py:92`

## 3. Runtime model

Primary execution lane:

- `scripts/design/generate_figma_instructions.py:875`
- `scripts/design/layout_templates.py:383`
- `scripts/design/canvas_artifact.py:1`
- `scripts/design/execution_adapters.py:79`

Preferred adapter for local design runtime:

- `code_native_canvas` via `scripts/design/execution_adapters.py:79`

Compatibility adapter:

- `deterministic_stub` via `scripts/design/execution_adapters.py:20`

## 4. Output contract

The runtime should be able to materialize:

- `layout_archetype`
- `sections`
- `component_hierarchy`
- deterministic `render_ops` derived from the instruction contract. Evidence:
  `scripts/design/canvas_artifact.py:96`,
  `scripts/design/contracts.py:642`
- canonical JSON artifact `pulseplate_canvas_v1`. Evidence:
  `scripts/design/canvas_artifact.py:125`,
  `scripts/design/execution_adapters.py:141`

Required artifact fields:

- `canvas_version`. Evidence: `scripts/design/canvas_artifact.py:42`,
  `scripts/design/contracts.py:75`, `scripts/design/contracts.py:553`
- `screen_id`. Evidence: `scripts/design/canvas_artifact.py:43`,
  `scripts/design/contracts.py:76`, `scripts/design/contracts.py:553`
- `platform`. Evidence: `scripts/design/canvas_artifact.py:44`,
  `scripts/design/contracts.py:77`, `scripts/design/contracts.py:553`
- `surface`. Evidence: `scripts/design/canvas_artifact.py:45`,
  `scripts/design/contracts.py:78`, `scripts/design/contracts.py:553`
- `layout_archetype`. Evidence: `scripts/design/canvas_artifact.py:46`,
  `scripts/design/contracts.py:79`, `scripts/design/contracts.py:553`
- `layout_pattern`. Evidence: `scripts/design/canvas_artifact.py:47`,
  `scripts/design/contracts.py:80`, `scripts/design/contracts.py:553`
- `dimensions`. Evidence: `scripts/design/canvas_artifact.py:48`,
  `scripts/design/contracts.py:81`, `scripts/design/contracts.py:553`
- `background_token`. Evidence: `scripts/design/canvas_artifact.py:49`,
  `scripts/design/contracts.py:82`, `scripts/design/contracts.py:553`
- `token_constraints`. Evidence: `scripts/design/canvas_artifact.py:50`,
  `scripts/design/contracts.py:83`, `scripts/design/contracts.py:553`
- `sections`. Evidence: `scripts/design/canvas_artifact.py:51`,
  `scripts/design/contracts.py:84`, `scripts/design/contracts.py:553`
- `nodes`. Evidence: `scripts/design/canvas_artifact.py:52`,
  `scripts/design/contracts.py:85`, `scripts/design/contracts.py:553`
- `render_ops`. Evidence: `scripts/design/canvas_artifact.py:53`,
  `scripts/design/contracts.py:86`, `scripts/design/contracts.py:553`

Manifest-safe metadata for `code_native_canvas` must also record:

- `artifact_type`. Evidence: `scripts/design/execution_adapters.py:111`,
  `scripts/design/execute_design.py:136`
- `artifact_version`. Evidence: `scripts/design/execution_adapters.py:112`,
  `scripts/design/execute_design.py:137`
- `section_count`. Evidence: `scripts/design/execution_adapters.py:106`,
  `scripts/design/execute_design.py:130`
- `component_count`. Evidence: `scripts/design/execution_adapters.py:107`,
  `scripts/design/execute_design.py:132`

## 5. Non-goals for current phase

- no live external design-tool execution
- no browser-dependent rendering pipeline
- no second hidden source of truth outside the repo

## 6. Security Notes

- external design tools remain optional reference lanes only
- runtime adapters must fail closed on unknown adapter names
- execution should remain deterministic and local-only until explicitly promoted

## 7. Marketing & GTM

This supports a stronger product story:

- not "Figma automation"
- but "design as code from design system + prompt"

That is a better foundation for agent-native design tooling and internal
workflow differentiation.
