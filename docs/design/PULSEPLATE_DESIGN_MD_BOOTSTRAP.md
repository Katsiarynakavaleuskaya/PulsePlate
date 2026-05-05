<!-- markdownlint-disable MD013 -->
# PulsePlate DESIGN.md Bootstrap

**Status:** Bootstrap contract, not completed DESIGN.md
**Purpose:** Define the future PulsePlate DESIGN.md role without creating a manual second source of truth.

## Summary

PulsePlate may later introduce a DESIGN.md file as an agent-readable semantic wrapper over existing repo truth. PR-0 does not create the final DESIGN.md and does not claim the contract is complete.

Future DESIGN.md must be generated or drift-checked from repo token and component contracts. It cannot be a manual design authority.

## DESIGN.md Role

DESIGN.md should help agents answer:

- what the brand intends to feel like,
- which tokens exist,
- which components are canonical,
- which screen grammar patterns are allowed,
- what accessibility and motion constraints apply,
- which platform deltas are intentional,
- where evidence links live.

It is a semantic wrapper for agent readability, not a source of truth.

## Source-Of-Truth Boundaries

- `/tokens` remains the token authoring SoT.
- `docs/design/UI_COMPONENT_VOCABULARY.md` and `docs/design/ui_component_vocabulary.json` remain the normalization contract.
- Storybook remains the web review/documentation lane.
- Figma remains the design-intent lane.
- Generated mirrors are not manually edited:
  - `frontend/src/styles/tokens.css`
  - `frontend/src/styles/tokens.ts`
  - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
- Backend and OpenAPI remain product/runtime contract truth.
- Web and iOS clients remain thin presentation layers.

## Future Generator / Checker Plan

PR-1 should add either:

- a generator that emits DESIGN.md from `/tokens`, component vocabulary, Storybook inventory, and current design docs, or
- a checker that fails when manually edited DESIGN.md drifts from those sources.

Minimum checker requirements:

- token names and generated mirror notes match repo token truth,
- component names match UI vocabulary,
- Figma is described as design-intent only,
- Storybook is described as review-only,
- no external reference appears as source of truth,
- wellness-only and App Store-safe boundaries are present,
- generated timestamp or source hash is recorded if generation is used.

## Sample Future Structure

```markdown
# PulsePlate DESIGN.md

## Brand Intent

Calm, premium, planning-first wellness. No medical diagnosis, treatment, therapy, crisis-support, or emergency-care claims.

## Tokens

Generated from `/tokens`; generated mirrors are derived runtime outputs.

## Typography

Generated from token scale and implemented component usage.

## Spacing

Generated from token scale and platform-specific constraints.

## Radius

Generated from token scale and component usage.

## Components

Normalized through `docs/design/UI_COMPONENT_VOCABULARY.md` and implemented repo components.

## Screen Grammar

Derived from implemented product surfaces, approved packets, and future evidence packs.

## Accessibility

Contrast, keyboard/focus, touch targets, motion comfort, non-color state semantics.

## Motion

Reduced-motion-safe; no motion that carries required product meaning alone.

## Do / Don't

Do use repo tokens, vocabulary, and thin-client contracts. Do not copy external references or move backend truth into clients.

## Platform Deltas

Web and iOS differences are allowed only when platform conventions require them.

## Evidence Links

Links to token docs, component vocabulary, Storybook evidence, Figma read-only nodes, and review artifacts.
```

## Bootstrap Controls

- DESIGN.md cannot be manually treated as canonical.
- Any future generated DESIGN.md must point back to `/tokens`, component vocabulary, Storybook review evidence, and Figma read-only evidence.
- Any external reference summary must cite a manifest id and scorecard decision.
- If DESIGN.md conflicts with `/tokens` or runtime code, repo token/runtime truth wins until a reviewed PR changes it.
