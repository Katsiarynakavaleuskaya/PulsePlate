# PulsePlate Emblem Blueprint Concepts

Version: v1.0
Status: concept blueprint set for Figma MCP execution
Palette lock: `#0F172A`, `#339FFF`, `#20C997`, `#FF5D5D` (accent only)

## Concept A - Pulse Hearth Monogram

### Geometry Recipe

- Layer 1: base disc, perfect centered circle, full-height occupancy
- Layer 2: inner plate ring, concentric stroke ring inset by 14-16%
- Layer 3: pulse cut, single smooth waveform through center (negative boolean cut)
- Layer 4: heart seed, tiny geometric heart at pulse apex (~12% of disc)
- Layer 5: optional micro arc, short curved gesture above heart (non-mascot, abstract)

### Token Mapping

- base: `#0F172A`
- ring/pulse: `#339FFF`
- micro highlight: `#20C997`
- heart accent only: `#FF5D5D`

### Readability Rules

- 24px: simplify pulse to one hump + one dip, remove optional arc
- 32px: keep heart block shape, increase negative space
- 60px: full pulse shape allowed
- 120px+: restore spacing nuance and micro highlight

### 1024 Notes

- occupancy target: 78-82%
- subtle radial depth only, no glossy 3D finish
- preserve edge sharpness for storefront compression

## Concept B - Plate Compass

### Geometry Recipe

- Layer 1: rounded-square container aligned to icon safe area
- Layer 2: compass plate circle with shallow cardinal notches (N/E/S/W)
- Layer 3: intelligence arc, 220-degree arc in upper-right quadrant
- Layer 4: needle-pulse hybrid, tapered lozenge from center to 1-2 o'clock
- Layer 5: warm core dot at center

### Token Mapping

- container/base: `#0F172A`
- plate/arc/needle: `#339FFF`
- center core: `#20C997`
- optional needle-tip accent: `#FF5D5D` (<=2% area)

### Readability Rules

- 24px: remove notches and red tip
- 32px: keep only N/S notch pair
- 60px: full notch set allowed
- 120px+: allow subtle taper details

### 1024 Notes

- keep needle length at 42-46% radius
- avoid sharp notch corners that artifact on export
- maintain calm geometry (no aggressive clinical feel)

## Concept C - FitChef Orbit Crest

### Geometry Recipe

- Layer 1: crest badge, solid centered circle
- Layer 2: orbit ring, thin inset ring with one controlled break
- Layer 3: spoon-leaf fusion glyph, vertical abstract nutrition anchor
- Layer 4: chef-orbit stroke, short upper arc with open end
- Layer 5: single spark dot near orbit end

### Token Mapping

- crest: `#0F172A`
- orbit + core glyph: `#339FFF`
- leaf notch/highlight: `#20C997`
- spark accent only: `#FF5D5D` (or green fallback for contrast)

### Readability Rules

- 24px: remove spark and taper nuances
- 32px: increase orbit and glyph stroke by ~8%
- 60px: restore orbit break and spark if contrast is stable
- 120px+: full spacing fidelity allowed

### 1024 Notes

- matte depth over gloss
- center glyph width target: 20-24% of badge diameter
- run blur preview check before approval

## Shared Constraints (All Concepts)

- primitive count target: 6-10 shapes before boolean operations
- no mascot anatomy (eyes/mouth/face) in emblem core
- no medical symbol cues or ECG monitor framing
- pass mandatory matrix in `docs/design/APP_STORE_ICON_DOMINANCE_TEST_PROTOCOL.md`
