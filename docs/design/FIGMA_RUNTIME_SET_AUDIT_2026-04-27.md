# Figma Runtime Set Audit — 2026-04-27

<!-- markdownlint-disable MD013 -->

## Summary

Figma runtime visual pass completed for Button, Input, FormField and the additional **visual review surfaces** listed below (Figma compositions; not all are promoted repo primitives).
The repository remains the source of truth. Figma RuntimeSets are design-review artifacts unless a repo PR promotes the matching API or component contract.

Token and runtime precedence align with `docs/design/TOKEN_PIPELINE_GOVERNANCE.md` (repo code and runtime artifacts are final SoT; Figma is design-intent lane).

## Figma source anchors (this audit)

For traceability without blocking on node-id capture in this governance PR:

- **Figma file:** `PulsePlate_v3_Canonical_Foundations_Welcome_Gate`
- **Page:** `01_Components`
- **Primary reviewed RuntimeSets:** `PP/Shared/Button/RuntimeSet`, `PP/Shared/Input/RuntimeSet`, `PP/Shared/FormField/RuntimeSet`

## Evidence anchors (repo contracts)

- Web `Button` API: `frontend/src/components/ui/Button.tsx:3-4` (`ButtonVariant` including success/warning, `ButtonSize`); loading props in `frontend/src/components/ui/Button.tsx:10-11`.
- Web `Input`: `frontend/src/components/ui/Input.tsx:5-11` (`InputSize` + `InputProps` parity API), `frontend/src/components/ui/Input.tsx:47-76` (runtime `loading`/`invalid`/`fullWidth` behavior), `frontend/src/components/ui/__tests__/Input.test.tsx:30-41` (native `type` passthrough).

## Visual PASS

### PP/Shared/Button/RuntimeSet

Status: visual PASS

Variants:

- tone=primary, state=default, size=md
- tone=primary, state=hover, size=md
- tone=primary, state=pressed, size=md
- tone=primary, state=focus, size=md
- tone=primary, state=loading, size=md
- tone=primary, state=disabled, size=md
- tone=secondary, state=default, size=md
- tone=ghost, state=default, size=md
- tone=success, state=default, size=md
- tone=warning, state=default, size=md
- tone=danger, state=default, size=md
- tone=primary, state=default, size=sm
- tone=primary, state=default, size=lg

Code parity:

- Figma tones **`primary`**, **`secondary`**, **`ghost`**, **`success`**, and **`warning`** align by name with `ButtonVariant` in `Button.tsx` (`frontend/src/components/ui/Button.tsx:3-4`, `frontend/src/components/ui/Button.tsx:15-26`).
- Figma **`tone=danger`** maps to repo **`variant="destructive"`** only (no `danger` prop alias); destructive styling remains `frontend/src/components/ui/Button.tsx:20-21`.
- **`loading`** is implemented as optional `loading` / `loadingLabel` with `aria-busy`, disabled while loading, and safe prop spread order (`frontend/src/components/ui/Button.tsx:72-77`, render branch `frontend/src/components/ui/Button.tsx:79`).

### PP/Shared/Input/RuntimeSet

Status: visual PASS

Variants:

- type=text, state=default, size=md
- type=text, state=focused, size=md
- type=text, state=filled, size=md
- type=text, state=error, size=md
- type=text, state=disabled, size=md
- type=number, state=default, size=md
- type=search, state=default, size=md
- type=secret, state=default, size=md
- type=text, state=default, size=sm

Code parity:

- Core Input RuntimeSet parity is backed by `frontend/src/components/ui/Input.tsx:5-11`, `frontend/src/components/ui/Input.tsx:47-76`: `size`, `invalid`, `loading`, native HTML input `type`, and disabled behavior.
- `type=text`, `type=number`, `type=search`, and `type=secret` map to native input types (`text`, `number`, `search`, `password`) via passthrough in `frontend/src/components/ui/Input.tsx:66-76` and tests in `frontend/src/components/ui/__tests__/Input.test.tsx:30-41`.
- `type=text, state=default, size=sm` maps to `size="sm"` (`frontend/src/components/ui/Input.tsx:14-17`, `frontend/src/components/ui/__tests__/Input.test.tsx:18-22`).
- `state=error` maps to `invalid` / `aria-invalid` (`frontend/src/components/ui/Input.tsx:60-69`, `frontend/src/components/ui/__tests__/Input.test.tsx:44-60`).
- `state=disabled` maps to native `disabled` and loading-enforced disabled (`frontend/src/components/ui/Input.tsx:61-76`, `frontend/src/components/ui/__tests__/Input.test.tsx:62-81`).
- Unit, prefix, suffix, and clear-action remain accessory-shell follow-ups and are not promoted in PR #1553.

### PP/Shared/FormField/RuntimeSet

Status: visual PASS

Variants:

- text default md
- text focused md
- text filled md
- text error md
- text success md
- text disabled md
- number default md
- secret default md
- select default md
- text default compact

Code parity:

- This PR **did not audit** a dedicated repo `FormField` component API or OpenAPI contract; only the Figma RuntimeSet was reviewed visually.
- FormField remains a **design-review surface** unless a future repo PR backs it with an explicit component contract and tests.

## Visual review surfaces (Figma)

The following are **Figma compositions / review surfaces** checked during the same session. A visual PASS here does **not** imply each item is a shipped production primitive or has a 1:1 repo component.

Visual PASS recorded for:

- ListCard
- ProgressMeter
- SubscriptionOption
- MetricBar
- FieldStack
- InlineActionRow
- SoftPaywallCallout
- InsightCallout
- ResultPanel
- ProfileSummary
- CoverageBadgeRow
- StatTile
- SectionHeader
- EmptyState
- MetaRow
- StatTileGroup
- DetailGroup
- SupportRow
- SectionBlock
- SummaryPanel
- ActionCluster
- OptionGroup
- ReviewBlock

## Governance decision

Do not promote new Figma-only primitives directly to code.

Any new runtime primitive or expanded API must go through:

1. Repo PR or RFC,
2. Token and code parity check,
3. Tests or Storybook review lane,
4. `docs/roadmap/BACKLOG_LEDGER.md` entry if deferred.

Related backlog:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-button-runtime-code-parity`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-input-runtime-code-parity`

## Follow-ups

- Button RuntimeSet parity: **resolved in PR #1552** (`Button.tsx`, Vitest, Storybook, audit anchors above).
- Input core parity: **resolved in PR #1553** (`Input.tsx`, Vitest, Storybook, audit anchors above).
