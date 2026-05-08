<!-- markdownlint-disable MD013 -->
# Design System Automation Spec

## Summary

This spec records the PR-9 design-system automation lane for web+iOS runtime parity.

PR-9 is docs/tests/governance only. It does not implement web runtime, iOS runtime, Storybook config, token mirrors, Figma/Canva writes, screenshots, or Code Connect activation.

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
3. Visual regression lane.
4. Accessibility regression lane.
5. Token/runtime parity boundary.
6. Later web+iOS implementation slices.

Implementation slices may start only after the registry, coverage inventory, and regression lane decisions exist or record formal `DEFERRED` dispositions with backlog anchors.

## Component Contract Registry Requirement

The registry is the next mandatory machine-readable layer. It must index repo-confirmed contracts, not design-tool intent alone.

Every unconfirmed field must be `unspecified`. Do not infer component ownership, state coverage, Figma nodes, Penpot boards, Storybook paths, Code Connect mappings, visual thresholds, or accessibility thresholds without repo evidence.

## Bridge Coverage

Bridge coverage must report, at minimum:

- repo vocabulary anchor,
- web runtime anchor,
- iOS runtime anchor,
- Storybook review anchor,
- Figma reference anchor,
- Penpot reference anchor,
- Code Connect anchor.

Coverage status values for later implementation are `covered`, `partial`, `missing`, or `unspecified`.

## Visual And Accessibility Regression

Visual and accessibility regression decisions are mandatory fail-closed gates for later implementation PRs.

Fail-closed means missing visual or accessibility regression coverage blocks implementation readiness unless the coordinator records a `DEFERRED` disposition with a backlog anchor and PR-body follow-up.

## Runtime Boundary

PR-9 does not implement runtime.

Future web and iOS implementation slices must:

- stay thin over backend/OpenAPI and repo truth;
- not move product truth into clients;
- not edit generated mirrors by hand;
- not treat Storybook or Figma as authoring truth;
- not treat Code Connect as active unless file key, node ID, seat/plan, and repo contract prerequisites are confirmed.

Unconfirmed Code Connect activation status is `unspecified`.
