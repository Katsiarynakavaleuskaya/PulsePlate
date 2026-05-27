<!-- markdownlint-disable MD013 -->
# Design System Automation Spec

## Summary

This spec records the PR-9 design-system automation lane for web+iOS runtime parity.

PR-9 is docs/tests/governance only. It does not implement web runtime, iOS runtime, Storybook config, token mirrors, Figma/Canva writes, screenshots, or Code Connect activation.

This token/runtime parity boundary is the final design-governance gate before frontend MVP. Frontend implementation is still blocked until this boundary lands, and the next PR is the first bounded frontend MVP product slice.

## Current Strengths

PulsePlate already has:

- design governance through workflow, templates, packets, premortem, and fixed mapping;
- Storybook parity as a review/documentation surface for implemented web components;
- token discipline through `/tokens`, web runtime token truth, and generated web+iOS mirrors;
- evidence automation through reference manifests, design intelligence docs, screen evidence packs, scorecards, and deterministic docs guards;
- source-of-truth boundaries that keep web and iOS thin over repo/backend truth.

## Bottleneck

The next bottleneck is machine-readable design infrastructure.

Future implementation cannot safely start from prompts, screenshots, Figma nodes, Storybook stories, or component names alone. It needs a governed registry that maps component contracts, bridge coverage, visual regression requirements, accessibility regression requirements, and token/runtime parity boundaries from repo truth.

## Source Boundaries

Canonical sources:

- repo code/docs/tests,
- backend/OpenAPI contracts for product/runtime truth,
- `/tokens` as token authoring truth,
- `frontend/src/styles/tokens.css` as web runtime token truth,
- generated and runtime iOS token mirrors as derived outputs,
- UI vocabulary docs and JSON as current component naming truth.

Reference layers:

- Figma,
- Canva,
- Penpot,
- Storybook,
- Code Connect,
- Browser/Chrome screenshots,
- scorecards,
- evidence packs,
- generated prompts.

Reference layers do not become source of truth without a later repo-reviewed contract.

## Required Implementation Sequence

Future work must proceed in this order:

1. Component contract registry.
2. Bridge coverage inventory.
3. Visual regression decision gate.
4. Accessibility regression decision gate.
5. Token/runtime parity boundary.
6. First bounded frontend MVP product slice.

Short form: registry -> bridge coverage -> visual regression decision -> accessibility regression decision -> token/runtime parity boundary -> first bounded frontend MVP product slice.

Implementation slices may start only after the registry, coverage inventory, regression lane decisions, and token/runtime parity boundary exist with repo evidence. Missing prerequisite gates are blockers, not `DEFERRED` permission to proceed. `DEFERRED` records follow-up tracking only. This PR does not implement frontend or iOS runtime.

## Component Contract Registry Requirement

The component contract registry seed is the current first mandatory machine-readable gate. It must index repo-confirmed contracts, not design-tool intent alone.

Current seed and validator:

- `docs/orchestration/contracts/design_component_registry.v1.json`
- `scripts/design/design_component_registry.py`

Every unconfirmed field must be `unspecified`. Do not infer component ownership, state coverage, Figma nodes, Penpot boards, Storybook paths, Code Connect mappings, visual thresholds, or accessibility thresholds without repo evidence.

This seed is not runtime implementation. It does not change web UI, iOS UI, tokens, generated mirrors, Storybook config, screenshots, binary assets, Figma, Canva, Penpot, Kimi, or Code Connect activation.

## Bridge Coverage

The current bridge coverage artifact is `docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json`, validated by `scripts/design/design_bridge_coverage_inventory.py`.

Bridge coverage must report, at minimum:

- repo vocabulary anchor,
- web runtime anchor,
- iOS runtime anchor,
- Storybook review anchor,
- Figma reference anchor,
- Penpot reference anchor,
- Code Connect anchor.

Coverage status values for later implementation are `covered`, `partial`, `missing`, or `unspecified`.

The bridge coverage inventory reports coverage only. Missing coverage blocks runtime implementation; it is not permission to copy Kimi, Figma, Canva, Penpot, Storybook, Code Connect, screenshot, or generated bundle evidence into web or iOS code.

## Visual And Accessibility Regression

Visual and accessibility regression decisions are mandatory fail-closed gates for later implementation PRs.

The visual regression decision gate follows the bridge coverage inventory. The current machine-readable artifact is `docs/orchestration/contracts/design_visual_regression_decisions.v1.json`, validated by `scripts/design/design_visual_regression_decisions.py`.

The visual regression decision gate reports decisions only. It does not run screenshots, does not commit screenshots or binaries, and does not choose a new visual regression service unless that service is already repo-confirmed.

Missing baseline, threshold, or tooling evidence blocks runtime implementation. Accessibility regression decision follows this visual decision gate, and token/runtime parity follows the visual and accessibility gates.

Kimi, Figma, Canva, Penpot, Storybook, Code Connect, screenshots, and generated design exports remain reference-only evidence. GPT-5.5 is the primary coding and governance model for repo changes in this lane; Kimi may provide bounded design review only.

Fail-closed means missing visual or accessibility regression coverage blocks implementation readiness. A `DEFERRED` disposition may track follow-up work, but it does not grant implementation permission.

## Token/Runtime Parity Boundary

The final machine-readable boundary for this governance train is `docs/orchestration/contracts/design_token_runtime_parity_boundary.v1.json`, validated by `scripts/design/design_token_runtime_parity_boundary.py`.

The boundary maps every registry/bridge component exactly once across token authoring status, web runtime token anchor, iOS runtime token anchor, generated mirror status, visual decision anchor, accessibility decision anchor, and implementation readiness.

Generated mirrors remain derived runtime evidence and are not token authoring truth. Missing visual or accessibility decision evidence keeps implementation readiness `blocked`. The next required gate after the boundary is not another design governance layer; it is the first bounded frontend MVP product slice.

Slack/Experiment Runner operator bridge remains after MVP observability exists, not before the first MVP slice.

## Runtime Boundary

PR-9 does not implement runtime.

Future web and iOS implementation slices must:

- stay thin over backend/OpenAPI and repo truth;
- not move product truth into clients;
- not edit generated mirrors by hand;
- not treat Storybook or Figma as authoring truth;
- not treat Code Connect as active unless file key, node ID, seat/plan, and repo contract prerequisites are confirmed.

Unconfirmed Code Connect activation status is `unspecified`.
