# Stitch AI Reference Adapter

Date created: March 11, 2026 (America/New_York)
Status: Phase 1 read-only adapter
Scope: Optional intake of Stitch concepts into PulsePlate's code-first UI workflow

## 1. Purpose

Define how `Stitch` may inform PulsePlate UI work without becoming a source of
truth.

This adapter is reference-only. It does not authorize direct promotion of
external outputs into runtime code, token contracts, or design governance.

## 2. Source precedence

Authoritative source precedence remains unchanged:

1. repo code, docs, and tests
2. `Figma` design lane where applicable
3. `/tokens`
4. governed runtime mirrors

`Stitch` is an optional ideation and reference lane only.

## 3. Allowed use

`Stitch` may be used for:

- layout ideation
- information hierarchy exploration
- visual variation brainstorming
- terminology discovery before normalization

`Stitch` may not be used as:

- runtime contract
- token authority
- component naming authority
- direct implementation source

## 4. Required normalization contract

Input:

- raw Stitch concept, screenshot, or textual reference

Output:

- `normalized_components[]`
- `layout_pattern`
- `states[]`
- `hierarchy`
- `token_mapping`
- `repo_reuse_candidates[]`
- `missing_primitives[]`
- `drift_warnings[]`
- `status: reference_only`

All output components must be mapped into:

- `docs/design/ui_component_vocabulary.json`

## 5. Normalization procedure

1. Capture the Stitch concept as external reference evidence.
2. Extract the apparent layout archetype.
3. Normalize every visible UI part into canonical vocabulary names.
4. Map colors, spacing, and typography intent to existing PulsePlate tokens.
5. Match existing repo components first.
6. Mark missing primitives explicitly.
7. Record drift warnings for any vendor-specific naming or visuals.

## 6. Drift warning classes

Record a drift warning when Stitch introduces:

- vague component naming
- token names not present in repo
- platform-incompatible controls
- visual styles outside PulsePlate luxury-clean guidance
- hidden modal/navigation ambiguity

## 7. Governance fit

This adapter must be read together with:

- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md`

Hard rule:

- no Stitch artifact is promoted to code or governed docs until it has been
  normalized and rewritten into PulsePlate contracts

## 8. Example normalization

Raw reference:

```text
A card with chips and a popup menu under a hero block.
```

Normalized output:

- `hero`
- `card`
- `badge`
- `dropdown-menu`

Potential drift warnings:

- `chips` ambiguous: normalized to `badge`
- `popup` ambiguous: normalized to `dropdown-menu`

## 9. Security Notes

- Treat Stitch output as untrusted external content.
- Do not paste unreviewed vendor output directly into repo specs or prompts.
- Preserve repo token and naming governance even when the external layout looks
  attractive.

## 10. Marketing & GTM

Used correctly, Stitch can accelerate:

- rapid layout ideation for wellness MVPs
- screenshot concept exploration
- landing-page variation brainstorming

Used incorrectly, it increases:

- generic AI look
- hidden naming drift
- loss of reusable component discipline
