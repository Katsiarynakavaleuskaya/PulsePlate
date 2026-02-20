# App Store Icon Execution Batch Plan

Version: v1.0
Scope: P1 emblem hardening in current Cursor + Figma MCP runtime
Reference flow: `docs/design/ICON_PIPELINE_FLOW.md`

## Runtime Assumption

- Figma Design (`figma.com/design`) is design SoT; Make links are not SoT for lock artifacts.
- Figma MCP in current runtime is used for context/export/evidence operations.
- Final dominance automation runs locally on exported PNG files.
- Git docs remain the contract source of truth.

## Batch Order

1. Build 3 deterministic icon variants in Figma from:
   - `docs/design/EMBLEM_BLUEPRINT_CONCEPTS_v1.md`
2. Export baseline assets per variant:
   - canonical master pair: `SVG` + `PNG 1024`
   - `60`, `120`, `1024`
   - `light`, `dark`, `mono`
3. Run local dominance harness:
   - blur(4px), grayscale, invert, distance(10%)
   - shadow/background noise L3 stress gate
4. Record results and pick winner.
5. Create lock artifact:
   - `docs/design/EMBLEM_CORE_v1.0_LOCK.md`
6. Run silhouette gate (mandatory before Results/Evidence updates):
   - `make icon-silhouette-check`
7. Save canonical winners in repo:
   - `assets/brand/icon/core/v1.0/icon_core_v1.svg`
   - `assets/brand/icon/core/v1.0/icon_core_v1_1024.png`
   - `assets/brand/icon/core/v1.0/icon_core_v1_60.png`
   - `assets/brand/icon/core/v1.0/meta.json`

## Figma Naming Contract

- Frame naming:
  - `icon_vA_pulse_hearth`
  - `icon_vB_plate_compass`
  - `icon_vC_orbit_crest`
- Export naming:
  - `<variant>__<mode>__<size>.png`
  - Example: `icon_vA_pulse_hearth__dark__120.png`

## Evidence Contract

- Capture MCP evidence:
  - design URL (`figma.com/design/...`)
  - file key
  - node ID
  - auth check result
  - node references (frame IDs / node IDs)
  - exported file list
- Store test outputs:
  - winner master SVG path
  - winner master PNG 1024 path
  - matrix pass/fail
  - failure tags
  - winner rationale

## Decision Rule

- Winner is selected only if:
  - all mandatory matrix cells pass
  - no L3 noise-stress failure
  - no automatic blocker from dominance protocol

- If all fail:
  - iterate geometry only (not palette)
  - re-run full matrix for updated variants
