# Compliance Control Plane

**Status:** Canonical compliance index
**Last updated:** 2026-03-08
**Scope:** Backend + legal/docs + guards

This directory is the compliance control-plane source of truth for the current
PulsePlate wellness runtime.

## Documents

- `DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md`
  - Canonical matrix for endpoint/store/purpose/sensitivity/retention/deletion/third-party exposure.
- `AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`
  - Canonical automated-analysis and wellness-boundary notices.
- `PROVIDER_INVENTORY.md`
  - Configurable processor families and their disclosure posture.
- `DSAR_AND_DELETION_MAP.md`
  - Internal artifact map for access/export/delete handling.
- `US_REGULATED_LANE_RFC_42_CFR_PART_2.md`
  - Future-state regulated-lane boundary for provider/clinical expansion.

## Runtime Sources

- `core/compliance/privacy.py`
- `core/compliance/transparency.py`
- `core/compliance/minimization.py`
- `core/compliance/dsar.py`
- `legacy_app.py`

## Legal Publication Endpoints

- `GET /privacy`
- `GET /terms`

## Current Position

- PulsePlate is a **consumer wellness** product.
- The current runtime is **not** a clinical or 42 CFR Part 2 lane.
- AI surfaces are treated as **automated wellness analysis**, not diagnosis or treatment support.
