# Figma Runtime Set Audit — 2026-04-27

<!-- markdownlint-disable MD013 -->

## Summary

Figma runtime visual pass completed for Button, Input, FormField and listed runtime rebuild sections.
The repository remains the source of truth. Figma RuntimeSets are design-review artifacts unless a repo PR promotes the matching API or component contract.

Token and runtime precedence align with `docs/design/TOKEN_PIPELINE_GOVERNANCE.md` (repo code and runtime artifacts are final SoT; Figma is design-intent lane).

## Evidence anchors (repo contracts)

- Web `Button` API: `frontend/src/components/ui/Button.tsx:3-4` (`ButtonVariant`, `ButtonSize`).
- Web `Input`: `frontend/src/components/ui/Input.tsx:4-24` (generic `HTMLInputElement` wrapper; no dedicated size/accessory/loading API).

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

- `primary`, `secondary`, `ghost`, `destructive` map to current `Button.tsx` (`frontend/src/components/ui/Button.tsx:3-20`).
- `success` and `warning` are design-intent only until `Button.tsx` supports them.
- `danger` should be reconciled with code naming `destructive`.
- `loading` is design-intent only until the Button API supports a loading state.

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

- Generic text/number/search/password usage maps to HTML input semantics via `Input` props.
- `size`, `unit`, `loading`, `prefix`, `suffix`, and clear-action require repo API promotion before becoming canonical.

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

- FormField remains a design-review surface unless backed by the current repo component contract.

## Runtime rebuild sections reviewed

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

- Button code parity PR: reconcile success/warning/danger/loading with `Button.tsx`.
- Input code parity PR: decide size/unit/loading/prefix/suffix/clear-action API.
