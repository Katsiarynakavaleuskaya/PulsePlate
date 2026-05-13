<!-- markdownlint-disable MD013 -->
# Design Component Contract Registry

## Summary

This document defines the governed contract for the machine-readable design component registry.

The first seed is `docs/orchestration/contracts/design_component_registry.v1.json`. It is validated by `scripts/design/design_component_registry.py` and remains docs/tooling/test governance only. It does not add web implementation, iOS implementation, Storybook config, Figma write, Penpot write, Canva write, Kimi write, token edit, generated mirror edit, screenshot, binary asset, or Code Connect activation.

## Authority

The registry is a repo-governed contract index. It is not a design-tool authority.

Canonical precedence:

1. Repo code/docs/tests.
2. Backend/OpenAPI product contracts.
3. `/tokens` token authoring truth.
4. Web runtime token truth in `frontend/src/styles/tokens.css`.
5. iOS generated/runtime token mirrors as derived runtime outputs.
6. UI vocabulary docs and JSON.

Figma, Canva, Penpot, Storybook, and Code Connect are bridge/reference fields only unless a later repo-reviewed contract promotes a narrower authority.

Kimi prototype artifacts, Google Drive prototype folders, screenshots, generated code bundles, and desktop exports are evidence/reference inputs only. They must normalize through this registry before any bridge coverage or implementation planning.

## Seed Artifact And Validator

The current seed artifact is:

- `docs/orchestration/contracts/design_component_registry.v1.json`

The current repo-local validator is:

```bash
.venv/bin/python scripts/design/design_component_registry.py validate docs/orchestration/contracts/design_component_registry.v1.json
.venv/bin/python scripts/design/design_component_registry.py summarize docs/orchestration/contracts/design_component_registry.v1.json
```

The seed includes every component id currently present in `docs/design/ui_component_vocabulary.json`. It may use repo-confirmed web anchors from the vocabulary record, but every unconfirmed iOS, token, Storybook, Figma, Penpot, Code Connect, state, variant, accessibility, and visual-regression field remains exactly `unspecified`.

The validator fails closed on malformed JSON, missing required fields, duplicate ids, ids outside the UI vocabulary, invalid status values, empty strings, missing vocabulary ids, and external evidence tools promoted into canonical authority.

## Required Record Shape

Later machine-readable records must include these fields:

| Field | Meaning | Unknown value |
| --- | --- | --- |
| `component_id` | Stable registry id | `unspecified` |
| `canonical_name` | Human-readable repo name | `unspecified` |
| `repo_vocabulary_anchor` | UI vocabulary doc or JSON anchor | `unspecified` |
| `web_runtime_anchor` | Web runtime file/symbol anchor | `unspecified` |
| `ios_runtime_anchor` | iOS runtime file/symbol anchor | `unspecified` |
| `token_dependencies` | Repo-confirmed token dependencies | `unspecified` |
| `storybook_review_anchor` | Storybook review/documentation anchor | `unspecified` |
| `figma_reference_anchor` | Figma evidence/reference anchor | `unspecified` |
| `penpot_reference_anchor` | Penpot secondary-lane reference anchor | `unspecified` |
| `code_connect_anchor` | Code Connect traceability anchor | `unspecified` |
| `states` | Confirmed component states | `unspecified` |
| `variants` | Confirmed component variants | `unspecified` |
| `accessibility_contract` | Required a11y regression/contract anchor | `unspecified` |
| `visual_regression_contract` | Required visual regression/contract anchor | `unspecified` |
| `owner` | Repo owner or lane owner | `unspecified` |
| `status` | `covered`, `partial`, `missing`, or `unspecified` | `unspecified` |

Do not invent values. If repo truth does not confirm a value, write `unspecified`.

## Bridge Coverage Contract

Bridge coverage is the reportable status of each component across:

- repo vocabulary,
- web runtime,
- iOS runtime,
- Storybook review,
- Figma reference,
- Penpot reference,
- Code Connect traceability.

Bridge coverage can guide implementation ordering, but it cannot promote Figma, Canva, Penpot, Storybook, or Code Connect into source of truth.

## Visual And Accessibility Gates

Every implementation-ready component must have:

- a visual regression decision, and
- an accessibility regression decision.

If either is missing, the implementation PR must fail closed or record a `DEFERRED` disposition with a backlog anchor and PR-body follow-up.

## Unspecified Defaults

The following remain `unspecified` unless a later implementation PR proves them from repo truth:

- exact Figma file and node mappings,
- exact Penpot workspace/page mappings,
- exact Code Connect mappings,
- visual regression tool and threshold,
- accessibility regression tool and threshold,
- per-component implementation order.

The next design-line PR after this seed is the bridge coverage inventory. That lane may report coverage gaps; it must not treat missing coverage as permission to implement runtime UI.
