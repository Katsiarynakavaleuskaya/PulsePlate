# PulsePlate App Icon Core v1.0 (Dual-master)

This directory contains the **canonical, production-locked masters** for the
PulsePlate App Icon Core v1.0.

**Source of truth (design):** Figma Design (see `meta.json` + lock docs).
**Repo truth (masters):** This folder only.

---

## Canonical files (must exist)

- `icon_core_v1.svg` — **master SVG**
- `icon_core_v1_1024.png` — **master PNG (1024)**
- `icon_core_v1_60.png` — **control PNG (60)**
- `meta.json` — contract metadata (winner + figma fields + hashes)

---

## Rules (6)

1) **Do not commit exports here.**
   Only canonical masters listed above belong in this folder.

2) **No extra variants.**
   Do not add `light/dark/mono`, `v2`, `final_final`, `tmp`, `draft`, etc.

3) **All changes require version bump.**
   Any geometry/silhouette drift -> create a new version folder (e.g. `v1.1/`) and rerun the full dominance protocol.

4) **Figma Make is not SoT.**
   Only Figma Design URL/key/node stored in `meta.json` is considered design SoT.

5) **L4 gates are mandatory.**
   Before updating any file in this folder:
   - run `make icon-core-validate`
   - run `make icon-silhouette-lock`
   - update lock docs
   - set baselines
   - run `make icon-silhouette-check`
   - attach raw stdout in the evidence log

6) **No manual edits to PNG.**
   PNG masters must be exported from Figma from the canonical winner node.

---

## Quick checklist (before PR)

- [ ] Files match the canonical set (no extras)
- [ ] `make icon-core-validate` passes
- [ ] `make icon-silhouette-check` passes
- [ ] `docs/design/EMBLEM_CORE_v1.0_LOCK.md` updated
- [ ] `docs/design/APP_STORE_ICON_EXECUTION_EVIDENCE_LOG.md` contains raw stdout
- [ ] `meta.json` updated (hashes + figma fields)
