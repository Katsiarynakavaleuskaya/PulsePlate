# Accessibility / Motion / State Contract

This document is the governed PR-6 contract for shared PulsePlate web and iOS
design-system primitives. It applies to primitive and shell-level components only;
product screen migrations require a separate handoff or supersede record.

## State Semantics

- Empty states expose a text title, text description, and optional governed action.
- Error states must use explicit error semantics in addition to visual styling.
- Loading states must expose an assistive label when they are the only status
  signal on screen.
- Status cannot rely on color alone; a visible or assistive text label must name
  the state.

## Focus And Keyboard

- Interactive web primitives must expose a visible `focus-visible` outline using
  governed token colors.
- Actions rendered by empty/error states use governed `Button` semantics rather
  than raw local button styles.
- Keyboard behavior must remain native; no custom key handling is introduced by
  this contract.

## Reduced Motion

- Decorative web motion must be guarded by reduced-motion aware classes.
- iOS primitive press and focus animations must resolve to no animation when
  `accessibilityReduceMotion` is enabled.
- Disabling motion must not change layout, routing, or data behavior.

## Touch Targets

- Web and iOS button/input primitives must preserve a minimum 44 px/pt target.
- Compact visual density may reduce padding, but not the minimum interactive
  target height.

## Assistive Technology Defaults

- Decorative skeletons are hidden from assistive technology by default.
- Skeletons that represent the page status must provide an explicit assistive
  label and use status semantics.
- Decorative icons inside empty/error states are hidden from assistive technology
  because the title and description carry the state meaning.
