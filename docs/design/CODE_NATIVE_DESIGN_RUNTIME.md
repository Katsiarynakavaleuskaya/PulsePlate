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
  `scripts/design/generate_figma_instructions.py:743`,
  `scripts/design/contracts.py:258`
- `pulseplate_canvas_v1` is the canonical internal runtime artifact emitted from
  the governed instruction contract. Evidence:
  `scripts/design/canvas_artifact.py:153`,
  `scripts/design/execution_adapters.py:98`
- `interaction_contract` is an additive governed presentation contract carried
  from instruction payload into `pulseplate_canvas_v1` without changing domain
  logic or topology ownership. Evidence:
  `scripts/design/generate_figma_instructions.py:71`,
  `scripts/design/canvas_artifact.py:166`,
  `scripts/design/contracts.py:206`
- HTML/browser preview is a derived review lane generated from
  `pulseplate_canvas_v1`; it is not a second topology source. Evidence:
  `scripts/design/html_preview.py:67`,
  `scripts/design/execute_design.py:117`,
  `scripts/design/verify_design.py:267`

## 3. Runtime model

Primary execution lane:

- `scripts/design/generate_figma_instructions.py:875`
- `scripts/design/layout_templates.py:383`
- `scripts/design/canvas_artifact.py:1`
- `scripts/design/execution_adapters.py:96`

Preferred adapter for local design runtime:

- `code_native_canvas` via `scripts/design/execution_adapters.py:90`

Compatibility adapter:

- `deterministic_stub` via `scripts/design/execution_adapters.py:26`

## 4. Output contract

The runtime should be able to materialize:

- `layout_archetype`
- `sections`
- `component_hierarchy`
- `interaction_contract` with governed adaptive presentation semantics for
  copy/layout/modality/order of disclosure only
- deterministic `render_ops` derived from the instruction contract. Evidence:
  `scripts/design/canvas_artifact.py:124`,
  `scripts/design/contracts.py:694`
- canonical JSON artifact `pulseplate_canvas_v1`. Evidence:
  `scripts/design/canvas_artifact.py:153`,
  `scripts/design/execution_adapters.py:146`

Required artifact fields:

- `canvas_version`. Evidence: `scripts/design/canvas_artifact.py:50`,
  `scripts/design/contracts.py:107`, `scripts/design/contracts.py:680`
- `screen_id`. Evidence: `scripts/design/canvas_artifact.py:51`,
  `scripts/design/contracts.py:108`, `scripts/design/contracts.py:680`
- `platform`. Evidence: `scripts/design/canvas_artifact.py:52`,
  `scripts/design/contracts.py:109`, `scripts/design/contracts.py:680`
- `surface`. Evidence: `scripts/design/canvas_artifact.py:53`,
  `scripts/design/contracts.py:110`, `scripts/design/contracts.py:680`
- `layout_archetype`. Evidence: `scripts/design/canvas_artifact.py:54`,
  `scripts/design/contracts.py:111`, `scripts/design/contracts.py:680`
- `layout_pattern`. Evidence: `scripts/design/canvas_artifact.py:55`,
  `scripts/design/contracts.py:112`, `scripts/design/contracts.py:680`
- `dimensions`. Evidence: `scripts/design/canvas_artifact.py:56`,
  `scripts/design/contracts.py:113`, `scripts/design/contracts.py:680`
- `background_token`. Evidence: `scripts/design/canvas_artifact.py:57`,
  `scripts/design/contracts.py:114`, `scripts/design/contracts.py:680`
- `token_constraints`. Evidence: `scripts/design/canvas_artifact.py:58`,
  `scripts/design/contracts.py:115`, `scripts/design/contracts.py:680`
- `interaction_contract`. Evidence: `scripts/design/canvas_artifact.py:59`,
  `scripts/design/contracts.py:116`, `scripts/design/contracts.py:680`
- `sections`. Evidence: `scripts/design/canvas_artifact.py:60`,
  `scripts/design/contracts.py:117`, `scripts/design/contracts.py:680`
- `nodes`. Evidence: `scripts/design/canvas_artifact.py:61`,
  `scripts/design/contracts.py:118`, `scripts/design/contracts.py:680`
- `render_ops`. Evidence: `scripts/design/canvas_artifact.py:62`,
  `scripts/design/contracts.py:119`, `scripts/design/contracts.py:680`

Manifest-safe metadata for `code_native_canvas` must also record:

- `artifact_type`. Evidence: `scripts/design/execution_adapters.py:116`,
  `scripts/design/execute_design.py:199`
- `artifact_version`. Evidence: `scripts/design/execution_adapters.py:117`,
  `scripts/design/execute_design.py:200`
- `section_count`. Evidence: `scripts/design/execution_adapters.py:111`,
  `scripts/design/execute_design.py:195`
- `component_count`. Evidence: `scripts/design/execution_adapters.py:112`,
  `scripts/design/execute_design.py:202`
- `interaction_contract`. Evidence: `scripts/design/execute_design.py:183`,
  `scripts/design/verify_design.py:302`
- `preview_artifact` when HTML preview generation is enabled. Evidence:
  `scripts/design/execute_design.py:141`,
  `scripts/design/verify_design.py:267`
- `preview_artifact.output_path` as a repo-relative local artifact path, not an
  absolute workstation path. Evidence: `scripts/design/html_preview.py:41`,
  `scripts/design/verify_design.py:284`

## 5. Non-goals for current phase

- no live external design-tool execution
- no public or browser-authoritative rendering pipeline
- no second hidden source of truth outside the repo

## 6. Security Notes

- external design tools remain optional reference lanes only
- runtime adapters must fail closed on unknown adapter names
- interaction/adaptation semantics must fail closed on unknown values
- execution should remain deterministic and local-only until explicitly promoted

## 7. Marketing & GTM

This supports a stronger product story:

- not "Figma automation"
- but "design as code from design system + prompt"

That is a better foundation for agent-native design tooling and internal
workflow differentiation.
