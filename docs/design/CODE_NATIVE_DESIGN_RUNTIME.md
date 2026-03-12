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
- generated instruction JSON remains the executable machine contract

## 3. Runtime model

Primary execution lane:

- `scripts/design/generate_figma_instructions.py:875`
- `scripts/design/layout_templates.py:383`
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
- stable render operations grouped by semantic role
- a deterministic local render artifact such as `pulseplate_canvas_v1`

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
