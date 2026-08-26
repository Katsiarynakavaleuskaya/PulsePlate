# FitChef Support Choice Funnel

**Status:** E1-05B merge-bound measurement contract
**Surface:** Web `/app`
**Owner:** Product + Frontend

## Purpose

This contract defines local, privacy-bounded evidence for the explicit FitChef
support-choice flow. It does not claim that production telemetry exists or that
the descriptor causes activation, retention, conversion, revenue, or plan use.

The user flow is:

```text
view choice
-> explicitly submit daily or weekly support need
-> receive a latest-request validated descriptor
-> optionally acknowledge the pointer
-> no navigation, execution, or plan mutation
```

Implementation anchors:

- `frontend/src/features/fitchef/supportChoiceEvents.ts`
- `frontend/src/features/fitchef/SupportChoiceCard.tsx`
- `frontend/src/api/fitchefSupportHandoff.ts`

## Current measurement state

- `transport=none`
- `production_counts=unavailable`
- `causal_status=not_assessed`
- `measurement_ready` means only that the closed event schemas and future
  formulas below are deterministic. It does not mean that events are sent,
  counted, analyzed, or causally interpreted in production.

## Closed event universe

| Event | Emission point | Required event-specific fields |
| --- | --- | --- |
| `fitchef_support_choice_viewed` | Once per mounted component instance | Base fields only |
| `fitchef_support_need_selected` | Immediately before an accepted explicit submit | `supportNeed`, submit-time `authState` |
| `fitchef_support_handoff_received` | Latest request only, after complete response validation | `supportNeed`, `targetSurface`, submit-time `authState` |
| `fitchef_support_handoff_confirmed` | First acknowledgement of the current validated descriptor | `supportNeed`, `targetSurface`, submit-time `authState` |
| `fitchef_support_handoff_exited` | Explicit dismiss, active selection change, or a classified request failure | closed `outcome`; only already-known `supportNeed` and `targetSurface` |

Every payload also requires exactly:

- `surface=app`
- `componentId=fitchef-support-choice`
- `routePath=/app`

The closed exit outcomes are:

- `dismissed`
- `changed_selection`
- `network_error`
- `auth_error`
- `feature_unavailable`
- `validation_error`

Unknown names, keys, values, incompatible need/surface pairs, and extra or
sensitive fields are rejected before the local sink. Sink failures never alter
the user flow.

## Privacy and authority boundary

The events contain no free text, raw error/body, user goal, plan content,
nutrition target, weight, BMI, email, name, session/API credential, timestamp,
cookie/tracking identifier, or device identifier. The module performs no
`fetch`, beacon, cookie, browser-storage, navigation, or plan-setting action.

`received` means only that the latest response passed the exact descriptor
recognizer. `confirmed` means acknowledgement only. Neither event proves that a
product surface opened, an action ran, a plan changed, or the pointer was useful.

## Future formulas

These formulas are definitions for a separately admitted transport. Their
inputs are unavailable today:

```text
selection_rate = fitchef_support_need_selected / fitchef_support_choice_viewed
delivery_rate = fitchef_support_handoff_received / fitchef_support_need_selected
confirmation_rate = fitchef_support_handoff_confirmed / fitchef_support_handoff_received
failure_mix(outcome) = fitchef_support_handoff_exited{outcome} / fitchef_support_need_selected
```

No denominator is inferred when it is zero or unavailable. A future transport
must add consent, retention, aggregation, replay/deduplication, monitoring, and
causal-analysis contracts in its own reviewed carrier before any product-value
claim is allowed.
