# PulsePlate App Icon Core v1.0 (Dual-master)

This directory is the **canonical, repo-owned icon core contract folder** for
PulsePlate App Icon Core v1.0. It may remain in a pre-lock state until the
canonical masters and hash fields are confirmed by a dedicated asset-lock PR.

**Design reference:** Figma Design metadata recorded in `meta.json` after lock.
**Repo truth:** this folder plus the repo validators and lock docs.

---

## Canonical files

- `icon_core_v1.svg` — **master SVG**
- `icon_core_v1_1024.png` — **master PNG (1024)**
- `icon_core_v1_60.png` — **control PNG (60)**
- `icon_core_v1_120.png` — derived PNG (120)
- `icon_core_v1_32.png` — derived PNG (32)
- `icon_core_v1_24.png` — derived PNG (24)
- `meta.json` — contract metadata (winner + figma fields + hashes)

Until lock completion, `README.md` and `meta.json` may be the only files
present. `make icon-core-validate` enforces folder shape and metadata schema.
Use explicit lock gates only when the repo-owned values are confirmed:

```bash
python3 scripts/validate_icon_core_v1.py --require-lock-values
python3 scripts/validate_icon_core_v1.py --require-canonical-masters
```

---

## Rules (6)

1) **Do not commit exports here.**
   Only canonical files listed above belong in this folder.

2) **No extra variants.**
   Do not add `light/dark/mono`, `v2`, `final_final`, `tmp`, `draft`, etc.

3) **All changes require version bump.**
   Any geometry/silhouette drift -> create a new version folder (e.g. `v1.1/`) and rerun the full dominance protocol.

4) **Figma Make is not SoT.**
   Only Figma Design URL/key/node stored in `meta.json` is considered design SoT.

5) **L4 gates are mandatory for lock updates.**
   Before adding or updating canonical asset files in this folder:
   - run `make icon-core-validate`
   - run `make icon-silhouette-lock`
   - update lock docs
   - set baselines
   - run `make icon-silhouette-check`
   - attach raw stdout in the evidence log

6) **No manual edits to PNG.**
   PNG masters must be exported from Figma from the canonical winner node.

---

## Quick checklist (before asset-lock PR)

- [ ] Files match the canonical allowed set (no extras)
- [ ] `make icon-core-validate` passes
- [ ] `make icon-silhouette-check` passes
- [ ] `docs/design/EMBLEM_CORE_v1.0_LOCK.md` updated
- [ ] `docs/design/APP_STORE_ICON_EXECUTION_EVIDENCE_LOG.md` contains raw stdout
- [ ] `meta.json` updated (hashes + figma fields)
