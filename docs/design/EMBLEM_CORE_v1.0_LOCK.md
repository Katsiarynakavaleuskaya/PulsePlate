# PulsePlate App Icon Core v1.0 (LOCK)

Status: `Production Locked`
Contract ID: `EMBLEM_CORE_v1.0_LOCK`
Control Level: `L4`
Date (UTC):
Owner:
Source: `docs/design/APP_STORE_ICON_DOMINANCE_RESULTS.md`

---

## 1. Canonical Winner

- variant ID:
- geometry version:
- figma design URL:
- figma file key:
- figma node ID:
- figma source type: `design` (not `make`)
- master policy: `dual-master-svg-png`
- canonical master SVG path:
- canonical master PNG 1024 path:

## 2. Silhouette Snapshot

Required artifacts:

- `1024` base
- `60px` reduced
- `blur(4px)`
- `grayscale`

Attach references:

- `assets/brand/icon/core/v1.0/icon_core_v1_1024.png`
- `assets/brand/icon/core/v1.0/icon_core_v1_60.png`
- `assets/brand/icon/core/v1.0/icon_core_v1_blur4.png`
- `assets/brand/icon/core/v1.0/icon_core_v1_gray.png`

## 3. Geometry Contract

- outer shape:
- inner safe padding:
- stroke system:
- cut/notch rules:
- accent placement rules:
- minimum stroke width:
- tolerance policy: `exact-zero` (no geometry drift allowed)

## 4. Geometry Hash (L4 Control)

- geometry hash algorithm: `SHA-256`
- master SVG SHA256:
- master PNG 1024 SHA256:
- raster `60` SHA256:
- master-pair parity status: pass/fail

Verification commands:

```bash
shasum -a 256 "<path-to-canonical-svg>"
shasum -a 256 "<path-to-raster-1024>"
shasum -a 256 "<path-to-raster-60>"
```

Match rule:

- hash mismatch = `HARD FAIL` (release blocked)

## 4.1 Silhouette Mask Control (L4+)

- method: grayscale -> threshold -> 1-bit mask bytes -> SHA-256
- threshold: `10` (locked)
- resize policy: `none`
- normalization: `1-bit mask` semantics (0/1 bytes)
- tolerance: `exact-zero`
- silhouette mask SHA256 (`1024`):
- silhouette mask SHA256 (`60`):

Deterministic verification command:

```bash
python scripts/silhouette_hash.py assets/brand/icon/core/v1.0/icon_core_v1_60.png
python scripts/silhouette_hash.py assets/brand/icon/core/v1.0/icon_core_v1_1024.png
```

Threshold rule:

- threshold change requires version bump and full rerun of dominance protocol
- threshold mismatch = `HARD FAIL`

## 4.2 Silhouette Density Check

- baseline white pixel ratio (`60`):
- baseline white pixel ratio (`1024`):
- warning threshold: `> 1%` absolute ratio delta
- hard-fail threshold: `> 3%` absolute ratio delta

Density check command examples:

```bash
python scripts/silhouette_hash.py assets/brand/icon/core/v1.0/icon_core_v1_60.png --baseline-white-ratio <ratio> --baseline-black-ratio <ratio>
python scripts/silhouette_hash.py assets/brand/icon/core/v1.0/icon_core_v1_1024.png --baseline-white-ratio <ratio> --baseline-black-ratio <ratio>
```

## 5. Token Contract

- primary fill:
- secondary accent:
- background modes:
- canonical token set: `#0F172A`, `#339FFF`, `#20C997`, `#FF5D5D` (accent only)

## 6. Mutation Policy

Allowed:

- shadow softness adjustment <= 5%
- export color-profile adjustments without geometry change
- metadata/path naming updates

Forbidden:

- changing silhouette
- moving notch/cut topology
- adding gradients that alter semantic shape
- changing stroke grammar
- accent relocation that alters focal semantics

## 7. Versioning Rule

Any geometry change:

- requires version bump
- requires full dominance matrix rerun
- requires new lock file (`EMBLEM_CORE_vX.Y_LOCK.md`)

Gate condition:

- changed geometry hash without version bump = `REJECT`

## 8. Competitive Dominance Snapshot

Store references:

- neighbor icon set capture (10 competitors)
- blur/grayscale/invert comparative sheet
- evidence file refs:

Dominance statement:

- winner keeps <1s recognition under grid pressure
- no medical/semantic ambiguity under stress modes

## 9. Sign-off

- design owner:
- coordinator:
- policy/security reviewer (if required):
