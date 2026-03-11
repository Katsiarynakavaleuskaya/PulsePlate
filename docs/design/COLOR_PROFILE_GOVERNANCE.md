# Color Profile Governance

<!-- markdownlint-disable MD013 -->

This document defines the color-profile policy that sits above the PulsePlate
token pipeline.

## 1. Purpose

Use one explicit policy for runtime color-space behavior, exported imagery, and
review evidence so web and iOS do not drift into ad-hoc profile handling.

Repo-grounded evidence:

- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md:22` defines repo artifacts as the
  final source of truth.
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md:45` sets the web runtime token
  contract.
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md:47` and
  `docs/design/TOKEN_PIPELINE_GOVERNANCE.md:48` define the generated and runtime
  iOS mirrors.
- `ios/PulsePlate/Extensions/Color+Assets.swift:64` currently bridges asset
  colors through `Color(..., colorSpace: .sRGB)`.

## 2. Baseline policy

- Default runtime/output baseline: `sRGB`
- Optional wide-gamut lane: `Display P3`
- Hard rule: `Display P3` is opt-in for reviewed assets only; it is not the
  default runtime color-space contract for components.
- Hard rule: component code must not introduce ad-hoc per-screen or per-view
  color-space behavior outside the governed token and asset lanes.

## 3. Relationship to token governance

- `docs/design/TOKENS_SOT.md` defines token meaning and ownership.
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md` defines authoring, generation, and
  runtime mirror governance for token values.
- This document governs color-profile choice, export policy, fallback behavior,
  and review evidence above that token pipeline.

## 4. Runtime rules

### Web

- Web runtime tokens remain the canonical semantic color source.
- CSS/runtime components must assume `sRGB` compatibility as the default.
- If a branded asset or marketing surface uses `Display P3`, it must ship with
  an `sRGB` fallback path or reviewed evidence that fallback is unnecessary for
  the scoped surface.

### iOS

- Generated and runtime token mirrors remain canonical for semantic color usage.
- Asset-backed color delivery may use profile-tagged assets, but the default app
  runtime contract remains `sRGB` unless a reviewed exception is documented.
- Do not add one-off `Display P3` component logic in SwiftUI/UIKit views.

## 5. Export and asset policy

- Every exported PNG/JPEG used for branded product surfaces must preserve an
  explicit color-profile choice.
- Default export profile for product/runtime imagery: `sRGB`
- `Display P3` assets are allowed only when:
  - the source design intentionally targets wide-gamut output
  - the asset is explicitly tagged
  - an `sRGB` fallback or parity justification exists
- Untagged imagery must be treated as non-compliant for new critical branded
  surfaces.

## 6. Review evidence

For color-sensitive branded changes, the review packet must include:

- affected runtime/artifact paths
- intended output profile (`sRGB` or `Display P3`)
- screenshot parity evidence for the critical surface on web and iOS when the
  change crosses platforms
- explicit note when `Display P3` is used and how fallback expectations were
  handled

## 7. Prohibited patterns

- Shipping component-level color-space decisions without a reviewed policy path
- Treating asset export defaults from design tools as canonical without repo
  promotion and review evidence
- Replacing runtime semantic token usage with raw wide-gamut literals in
  component code

## 8. Deferred automation

Deterministic asset-profile auditing and screenshot parity automation are
deferred follow-through items and must be tracked in
`docs/roadmap/BACKLOG_LEDGER.md`.

## 9. Related docs

- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
