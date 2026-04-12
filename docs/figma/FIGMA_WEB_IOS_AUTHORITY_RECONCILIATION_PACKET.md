# Figma / iOS Authority Reconciliation Packet

**Date:** April 11, 2026
**Status:** Canonical cross-file governance packet
**Scope:** web `v3` + iOS `v2` authority lock with explicit Code Connect bypass

## 1. Purpose

This packet removes ambiguity between the current PulsePlate web `v3`,
implementation-safe iOS `v2`, Figma Make, and spec/index surfaces.

Its job is to keep the current delivery model repo-native and to prevent three
drift patterns:

1. treating Figma or terminal tooling as hidden product authority
2. mixing web `v3` execution truth with iOS `v2` implementation reference truth
3. reintroducing Code Connect as a required path, blocker, or next mandatory step

Hard rule:

- repo code, docs, tests, and runtime contracts remain the business-logic SoT

## 2. Coordinator Role Order

This packet follows the coordinator-owned role order for the lane:

1. `agent-coordinator`
2. `figma-designer`
3. `prompt-engineer`
4. `ios-specialist`
5. `frontend-engineer`
6. `qa-engineer-agent`
7. `bug-hunter`

No role in this chain may be skipped without an explicit coordinator packet
update.

## 3. Authority Matrix By File Key

| File key | Surface | Status | Allowed use | Forbidden use |
| --- | --- | --- | --- | --- |
| `2JDwOByQIbcPgp93FDzHii` | Clean `v3` web/design-system file | `canonical_execution` | governed web/design-system execution lane | redefining repo business logic |
| `qJBtE5J6efmavcHCm6SF0O` | `PulsePlate_v3` legacy file | `reference_only` | audit, provenance, comparison | execution target, authority promotion |
| `AhyS6u4dZXMRHVUDO3Cfn6` | `ios prototype v2` | `implementation_safe` | iOS implementation-safe visual/node reconciliation | defining iOS behavior, tokens, or flow |
| `MrztJU3CQtxhADBbtAsWJ6` | Active Make/prototype file | `reference_only` | prototype comparison, drift review | runtime/design authority |
| `umcCk7TtO760DJ3N6M7mvh` | Design spec/index surface | `spec_index_only` | spec lookup, CTA registry reference, stale-evidence provenance | canonical design file, execution lane, authority source |

Hard rules:

- `2JDwOByQIbcPgp93FDzHii` is the only web/design-system
  `canonical_execution` lane in this delivery model.
- `AhyS6u4dZXMRHVUDO3Cfn6` is implementation-safe only; it remains
  repo-subordinate and cannot define behavior, tokens, or flow.
- `qJBtE5J6efmavcHCm6SF0O`, `MrztJU3CQtxhADBbtAsWJ6`, and
  `umcCk7TtO760DJ3N6M7mvh` are not execution targets.

## 4. Source Precedence

Use this order whenever repo artifacts, Figma files, AI output, or auxiliary
tooling disagree.

1. repo code, docs, tests, runtime contracts, and governed design docs
2. repo token and component mirrors
   - `frontend/src/styles/tokens.css`
   - `frontend/src/styles/tokens.ts`
   - `frontend/.storybook/`
   - `ios/PulsePlate/Assets.xcassets/`
   - `ios/PulsePlate/Extensions/Color+Assets.swift`
3. this packet plus the lane-specific reconciliation packets
4. `2JDwOByQIbcPgp93FDzHii` for governed web/design-system execution
5. `AhyS6u4dZXMRHVUDO3Cfn6` for implementation-safe iOS reconciliation
6. `qJBtE5J6efmavcHCm6SF0O` and `MrztJU3CQtxhADBbtAsWJ6` as
   `reference_only`
7. `umcCk7TtO760DJ3N6M7mvh` as `spec_index_only`
8. Figma AI, Figma Make, MCP captures, internal bridge systems, web terminal,
   and Cursor terminal as auxiliary evidence only

Hard rule:

- if repo and Figma disagree, repo SoT wins until a reviewed repo change says
  otherwise

## 5. Explicit Code Connect Bypass Policy

Current delivery bypasses Code Connect completely.

For this PR and the follow-up lanes governed by this packet:

- Code Connect is `not_required`
- Code Connect is not planned
- Code Connect is not gating
- workspace seat or Code Connect availability is not a blocker
- this packet does not open, unblock, or prepare a Code Connect activation lane

Existing Code Connect docs and artifacts remain only as historical context:

| Doc / artifact | Status in this lane |
| --- | --- |
| `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md` | `historical_reference_only` |
| `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md` | `historical_reference_only` |
| `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md` | `historical_reference_only` |
| `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md` | `historical_reference_only` |

These references may preserve blocker history or provenance, but they cannot
redefine the current delivery path.
They also cannot seed a future activation lane by implication.

## 6. Allowed Tooling Matrix

| Tool / surface | Role | Authority status |
| --- | --- | --- |
| repo code/docs/tests | business-logic and governance SoT | authoritative |
| repo packets and runbooks | governance and lane control | authoritative for process, not product invention |
| Storybook and component inventory | repo-backed review surfaces | review/evidence only |
| Figma MCP (`whoami`, metadata, screenshots, design context, non-authoritative evidence writes only) | inspection, validation, evidence capture | auxiliary evidence only |
| Figma AI / Make | critique, token extraction, layout variation, microcopy drafting, proposal scaffolding, screenshot-assisted analysis | advisory only |
| internal bridge systems | comparison and reconciliation support | auxiliary evidence only |
| web terminal | capture, inspection, parity checks | auxiliary evidence only |
| Cursor terminal | capture, inspection, parity checks | auxiliary evidence only |
| Code Connect | historical mapping path outside current delivery model | `not_required` |

Hard rules:

- bridge tooling is read-only with respect to authority
- web terminal, Cursor terminal, and MCP cannot promote file or node authority
- design review references are tool-neutral traceability artifacts only

## 7. Promotion / Demotion Rules

Promotion or demotion between lanes is allowed only through a reviewed repo
packet or follow-up PR.

Allowed promotions:

- `implementation_safe` may be refined with fresh MCP evidence when the repo
  runtime still matches and the packet is updated in Git
- `reference_only` material may inform comparison, but only repo-reviewed docs
  may promote a surface into a stronger status

Forbidden promotions:

- no Make file may be promoted into `canonical_execution` by visual quality
  alone
- no spec/index file may be promoted into execution authority from captured
  node IDs or browser search alone
- no AI-generated output may be promoted into canonical product truth without
  repo review
- no bridge or terminal evidence may establish canonical requirements on its own

Demotion triggers:

- stale or invalid node evidence
- drift from repo-backed CTA, onboarding, paywall, or runtime contracts
- undocumented local style invention
- conflicting multi-surface authority claims

## 8. Stale Facts And Anti-Drift Locks

The following facts are fixed for this packet:

- `umcCk7TtO760DJ3N6M7mvh` is usable only as a spec/index reference surface
- node `1:72` under `umcCk7TtO760DJ3N6M7mvh` is stale/invalid historical evidence,
  not an activation-safe authority anchor
- `MrztJU3CQtxhADBbtAsWJ6` is active as a Make/prototype reference lane only
- Figma, Make, MCP agents, browser capture, and terminal bridges do not define
  onboarding truth, paywall truth, CTA semantics, or iOS runtime truth

## 9. AI-Assisted Design Policy

Figma AI may assist with critique, token extraction, layout variation,
microcopy drafting, proposal scaffolding, and screenshot-assisted analysis.

Its output is advisory only and must be normalized against repo code, docs, and
tests before any acceptance or promotion.

Hard rules:

- treat all Figma AI output as proposal material, not as authority
- Figma AI cannot create, override, or promote canonical product truth
- any adopted result must remain traceable back to repo SoT and reviewed in Git

## 10. Decision Log

- **February 19, 2026:** browser/OpenClaw-era capture evidence recorded
  `umcCk7TtO760DJ3N6M7mvh` as a design/spec surface with unresolved critical
  node capture and only stale `1:72` history; this remains historical evidence,
  not current authority.
- **March 7, 2026:** the accepted Penpot + Storybook fallback seam confirmed
  repo-native web review sources and kept Code Connect non-canonical and
  non-blocking while blockers remained.
- **March 11-12, 2026:** Figma MCP runtime evidence confirmed live metadata,
  screenshots, and design-push capability; `AhyS6u4dZXMRHVUDO3Cfn6` was created
  and normalized as `ios prototype v2`, while Code Connect remained blocked and
  non-authoritative.
- **April 11, 2026:** this packet locks the current delivery model to explicit
  Code Connect bypass and fixes the split authority model across web `v3`, iOS
  `v2`, Make, and spec/index surfaces.

## 11. Acceptance Contract

This lane is aligned only when all are true:

- readers cannot confuse web `v3` execution authority with iOS `v2`
  implementation-safe reference
- `umcCk7TtO760DJ3N6M7mvh` is never described as a full canonical design file
- Code Connect is nowhere described as required, planned, or gating in the
  touched docs
- internal bridge and terminal systems are described only as auxiliary tooling
- no wording creates new business rules outside repo truth
