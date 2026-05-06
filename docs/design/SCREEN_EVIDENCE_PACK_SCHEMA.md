<!-- markdownlint-disable MD013 -->
# Screen Evidence Pack Schema

**Status:** Design Intelligence PR-3 contract
**Purpose:** Define deterministic screen evidence metadata for PulsePlate web and iOS review surfaces.

## Summary

Screen evidence packs are review evidence only. They do not become PulsePlate source of truth, product truth, token truth, runtime UI, Figma truth, Storybook truth, App Store truth, or implementation authority.

The repo source of truth remains code, docs, tests, `/tokens`, generated token mirrors, UI vocabulary, backend/OpenAPI contracts, and runtime implementation.

## Hard Rule

No screenshot, video, browser trace, Storybook build, DerivedData output, simulator artifact, or binary image is committed by this schema.

Committed examples contain metadata only. Runtime capture outputs must stay local-only under ignored artifact paths such as `artifacts/design/screen_evidence/<run_id>/`.

## Required Fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `evidence_id` | string | yes | Stable repo-local evidence id |
| `generated_by` | string | yes | Tool or reviewer that created the metadata |
| `generated_at_policy` | string | yes | `omitted` or `local_artifact_only` |
| `platform` | string | yes | `web` or `ios` |
| `surface_id` | string | yes | Stable review surface id, for example `web:/marketing` |
| `surface_name` | string | yes | Human-readable surface name |
| `route_or_screen` | string | yes | Web route or iOS screen id |
| `source_of_truth_note` | string | yes | Must state the pack is review evidence and not source of truth |
| `capture_mode` | string | yes | `automated`, `manual`, or `sample` |
| `artifact_policy` | string | yes | `local_only` or `committed_sample_metadata` |
| `viewport` | string | yes | Viewport, device, or simulator target descriptor |
| `theme` | string | yes | Theme or design mode descriptor |
| `locale` | string | yes | Locale reviewed |
| `component_ids` | array | yes | PulsePlate UI vocabulary ids used or expected |
| `token_mirror_paths_checked` | array | yes | Token mirror paths checked for this evidence |
| `accessibility_evidence` | object | yes | Contrast, focus, keyboard, touch target, and landmark evidence |
| `responsive_evidence` | object | yes | Viewport and responsive behavior evidence |
| `motion_evidence` | object | yes | Motion and reduced-motion evidence |
| `copy_safety_evidence` | object | yes | Wellness-only copy evidence |
| `tabbar_or_navigation_evidence` | object | yes | Navigation shell or tabbar evidence |
| `overflow_evidence` | object | yes | Horizontal overflow and clipping evidence |
| `screenshot_artifact_path` | string | yes | Local-only screenshot path or empty string |
| `dom_artifact_path` | string | yes | Local-only DOM summary path or empty string |
| `a11y_artifact_path` | string | yes | Local-only accessibility report path or empty string |
| `storybook_artifact_path` | string | yes | Local-only Storybook evidence path or empty string |
| `ios_simulator_artifact_path` | string | yes | Local-only iOS artifact path or empty string |
| `warnings` | array | yes | Review warnings and known limitations |
| `status` | string | yes | `sample`, `captured`, `validated`, or `rejected` |

## Validation Rules

- Evidence manifests must never claim source-of-truth authority.
- `source_of_truth_note` must state the pack is review evidence and not source of truth.
- Component ids must exist in `docs/design/ui_component_vocabulary.json`.
- Token mirror paths must be known repo token mirror paths.
- Non-empty artifact paths must be repo-relative and stay under `artifacts/design/screen_evidence/`.
- Artifact paths must not include `DerivedData`, `storybook-static`, `node_modules`, `.venv`, or `worktrees`.
- `artifact_policy=committed_sample_metadata` requires all artifact path fields to be empty.
- `copy_safety_evidence` must not promote diagnosis, treatment, therapy, emergency, crisis, guaranteed outcome, or medical claims.
- `status=validated` requires non-empty evidence objects and token mirror path checks.
- `platform=web` requires `route_or_screen`.
- `platform=ios` with `capture_mode=automated` requires an iOS simulator artifact path.

## Tooling

`scripts/design/screen_evidence_pack.py` provides deterministic validation and summary tooling:

```bash
python3 scripts/design/screen_evidence_pack.py validate <manifest.json>
python3 scripts/design/screen_evidence_pack.py validate-dir <dir>
python3 scripts/design/screen_evidence_pack.py summarize <manifest.json>
python3 scripts/design/screen_evidence_pack.py web-plan --routes / /marketing --out <dir>
```

The tool does not crawl websites, open Figma, write Canva, mutate runtime UI, run Playwright, commit screenshots, or score design quality. PR-4 will consume evidence later for deterministic scoring.
