# Telemetry Compatibility Reference

## Purpose

This document describes the limits of the legacy telemetry vocabulary. It is
not proof that an event is emitted, delivered, stored, queryable, or suitable
for attribution.

## Evidence levels

Telemetry claims must distinguish these levels:

1. **Defined** — an enum, payload type, or registry entry exists.
2. **Callable** — a helper can be invoked by another module.
3. **Test-called** — a unit test invokes the helper.
4. **Production-called** — a production module contains an explicit call site.
5. **Delivered** — an admitted transport confirms receipt.
6. **Stored** — an admitted data sink confirms durable storage.
7. **Queryable** — a governed dataset and query contract exist.

Evidence at one level does not prove any later level. In particular, a defined
or callable paywall, trial, or upgrade helper does not prove a current
production call or acquisition event.

## Current public-Web applicability

Current public-Web paywall/trial measurement: **UNAVAILABLE / NOT EMITTED**.

This is the intended current posture, not an outage.

It must not be represented as `0`, `0%`, or any other zero-valued metric.

Apple-device, backend, billing, or subscription observations must not fill a
public-Web numerator or denominator.

Repeated event rows do not establish unique-user counts.

The public Web is free and information-only. Its current UI does not invoke
paywall-view, paywall-dismiss, upgrade-click, trial-start, purchase, restore, or
checkout telemetry as acquisition actions.

## Compatibility surface

The following files retain type and helper vocabulary for compatibility:

- `telemetry/eventRegistry.ts` — event names and payload validation
- `telemetry.ts` — callable helpers and feature-flag checks
- `useTelemetry.ts` — opt-in React wrappers
- `__tests__/telemetry.test.ts` and `__tests__/useTelemetry.test.tsx` —
  test-called evidence only

A production caller must be identified separately for each event. For example,
an explicit non-acquisition badge-view call does not establish a paywall view,
trial start, upgrade click, purchase, or entitlement change.

## Feature-flag boundary

`VITE_ANALYTICS_ENABLED` only permits an explicit existing caller to continue
through the helper. The flag does not mount a hook, create a caller, emit every
defined event, deliver data, create storage, or make a dataset queryable.

## Data and privacy claims

The local helper hands a validated payload to the configured logging seam when
an explicit caller runs and analytics is enabled. This document does not claim
that all events are non-blocking, contain no personal data, reach a remote
provider, persist successfully, or satisfy an attribution contract. Those
claims require separate runtime, transport, privacy, storage, and query
evidence.

Any future public-Web monetization telemetry requires a new external product,
legal, architecture, runtime, data, and privacy admission.
