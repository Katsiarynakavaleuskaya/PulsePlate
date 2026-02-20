# App Store Icon Dominance Test Protocol

Version: v1.0
Owner: `designer-artist-agent`
Scope: PulsePlate emblem/app icon release gate

## Goal

Select an icon that stays recognizable, on-brand, and premium across storefront
conditions and small-size constraints.

## Mandatory Test Matrix

| Size | Light | Dark | Mono | Blur (4px) | Invert | Distance 10% |
| --- | --- | --- | --- | --- | --- | --- |
| 60px | TODO | TODO | TODO | TODO | TODO | TODO |
| 120px | TODO | TODO | TODO | TODO | TODO | TODO |
| 1024px | TODO | TODO | TODO | TODO | TODO | TODO |

## Automatic Blockers

Release is blocked if ANY of the following is true:

- silhouette is not recognizable within 1 second
- palette drift from canonical tokens
- loss of core plate/pulse semantic meaning
- grayscale collapse (identity depends only on color)
- contrast below accessibility threshold for key edges
- clinical/medical interpretation risk

## Apple Icon Grid Discipline

- 8px base alignment grid
- centered dominant symbol
- no edge-touching elements
- minimum inner padding: 12% of canvas
- safe zone preserved for rounded-mask clipping

## Figma MCP Automation Checks

- Token parity check
  - verify only canonical token colors are used
  - flag any non-token hex value
- Blur dominance check
  - apply Gaussian blur 4px
  - fail if silhouette collapses
- Grayscale dominance check
  - convert to grayscale
  - fail if recognition drops materially
- Inverted mode check
  - invert colors
  - fail on semantic instability
- Distance check
  - downscale to 10%
  - fail if core symbol is unreadable

## Shadow / Background Noise Stress Test (L3 Gate)

Purpose:
Simulate App Store grid pressure and visual competition context.

Test conditions:

1. Random background grid simulation
   - 12 mixed-color competitor-style icon tiles
   - mixed light/dark backgrounds
   - saturation range: 60-100%
2. Shadow overlay test
   - subtle drop shadow on surrounding icons only
   - candidate icon remains neutral
3. Peripheral blur simulation
   - slight blur on full grid except candidate
   - reverse pass: blur candidate only

Pass criteria:

- silhouette remains recognizable in < 1 second scan
- primary symbol (plate/pulse/crest) identifiable without zoom
- no medical cross misinterpretation in noisy context
- no semantic confusion with finance/fitness-only competitor classes

Fail conditions:

- icon blends into competitive grid
- meaning requires isolated context
- shape collapses under peripheral blur
- visual identity is mistaken for generic wellness app

## Evidence Required in PR

- tested variant IDs and source file references
- completed matrix with pass/fail per cell
- blocker list (if any) and remediation status
- final winner rationale (why chosen over alternatives)

## Release Decision

- `PASS`: all matrix cells pass and no blocker triggered
- `FAIL`: at least one failed cell or any blocker triggered
