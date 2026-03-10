# Telemetry Policy

## Scope

- Lightweight request spans are always on for backend request handling.
- Full payload capture is exceptional, encrypted, and pointer-only in spans.
- Client telemetry remains thin-client only: platform, version, tier context, feature flags.

## Runtime Rules

- Canonical middleware: `app/middleware/request_telemetry.py`
- Bootstrap registration: `app/bootstrap/telemetry.py`
- Sampling contract:
  - deterministic sampler: `app/telemetry/sampler.py`
  - hourly reservoir: `app/telemetry/reservoir.py`
  - detector escalation: `app/telemetry/detectors.py`
  - encrypted vault pointer storage: `app/telemetry/vault.py`
- Existing Prometheus route metrics remain in place via `app/bootstrap/metrics.py`.

## Data Handling

- Raw request and response bodies must never be written to span attributes.
- Full captures are minimized before encryption using `core/compliance/minimization.py`.
- Spans may store:
  - `pp.req.fingerprint`
  - low-cardinality route/status/timing fields
  - detector names
  - `pp.full_pointer_sha256`
- Spans must not store:
  - raw prompts
  - raw health-profile text
  - raw provider traces
  - raw response bodies

## Feature Flags

- `TELEMETRY_FULL_CAPTURE_RATE`
- `TELEMETRY_FULL_CAPTURE_RESERVOIR_PER_HOUR`
- `TELEMETRY_DETECTORS_ENABLED`
- `TELEMETRY_CLIENT_DEBUG_FULL`
- `TELEMETRY_VAULT_DIR`
- `TELEMETRY_VAULT_KEY`

## Rollout Order

1. Lightweight spans only
2. Detector-triggered capture decisions
3. Encrypted vault pointer mode
4. QA-only debug capture in non-prod
5. Production ramp from `0% -> 0.5% -> 1.5%`
