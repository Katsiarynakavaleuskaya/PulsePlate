# Operational Signals

Operator-facing index for the runtime signals that already exist in PulsePlate today.

## Runtime probes

| Surface | Purpose | Expected behavior | Source of truth |
| --- | --- | --- | --- |
| `/health` | Liveness | Always `200`; does not depend on the DB | `app/routers/health.py`, `app/main.py`, `app/AGENTS.md` |
| `/health/db` | DB readiness | `200` when DB is reachable, `503` otherwise | `app/routers/health.py`, `app/main.py`, `app/AGENTS.md` |
| `/ready` | Readiness alias | Same behavior as `/health/db`; hidden from OpenAPI | `app/routers/health.py`, `app/main.py`, `app/AGENTS.md` |
| `/api/v1/health` | Compatibility alias | Mirrors `/health` payload | `app/routers/health.py`, `app/main.py` |
| `/debug_env` | Local/operator debug surface | Returns limited debug configuration when debug/operator access is enabled; otherwise stays unavailable to avoid production leakage | `app/routers/admin_operations.py`, `app/services/admin_operations.py` |

Use `/health` for liveness checks and `/ready` or `/health/db` for dependency-aware readiness checks.

## Metrics

- Surface: `/metrics`
- Registration path: `app.main` calls `register_metrics(app)`
- Format:
  - happy path: Prometheus text format (`text/plain; version=0.0.4`)
  - fallback: JSON error envelope if exporter fails
- Current scope:
  - HTTP request count
  - HTTP request duration
- Primary implementation docs live in `app/AGENTS.md`

## Tracing and request telemetry

- `app.main` also calls:
  - `register_request_telemetry(app)`
  - `register_tracing(app)`
- Tracing is OpenTelemetry-based and configured through env toggles such as:
  - `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
  - `OTEL_SDK_DISABLED`
  - `PULSE_OBS_HMAC_KEY`
- Request telemetry exists in-process for local and runtime diagnostics even when a full external sink is not configured.

## What this means for contributors

- The repo already has health, readiness, metrics, and tracing entrypoints.
- These surfaces are intentionally split:
  - health/readiness endpoints live in the canonical `app.routers.health` router
    registered from `app.main`
  - metrics/tracing/request telemetry are also registered from the canonical
    `app.main` bootstrap
- When documenting or validating runtime behavior, prefer linking to this file first instead of rediscovering those surfaces from code.

## Current gap

The main observability gap is not missing probes or missing instrumentation hooks.

The current missing piece is a clearly documented, centralized error-reporting sink for production incidents. In other words:

- probes exist
- metrics exist
- tracing hooks exist
- request telemetry exists
- centralized error reporting is still follow-up work

Keep that distinction explicit so compatibility reviews do not imply that metrics or tracing are absent when they are already present in code.

If the probe paths, metrics surface, or bootstrap registration points move,
update this file in the same PR so the operator-facing index stays aligned with
runtime truth.

## Quick verification

Use these commands when you need lightweight operator proof that the documented
surfaces still exist:

Run these from the repository root in a local development shell with project
dependencies available. The first snippet imports `app.main`, so keep
`TESTING=true` as shown and prefer a local virtualenv rather than a production
runtime shell.

```bash
python - <<'PY'
import os
os.environ["TESTING"] = "true"
from app.main import app

paths = {route.path for route in app.routes}
for expected in ["/metrics", "/health", "/health/db", "/ready", "/api/v1/health"]:
    print(expected, "OK" if expected in paths else "MISSING")
PY
```

```bash
python - <<'PY'
import os

for key in [
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    "OTEL_SDK_DISABLED",
    "PULSE_OBS_HMAC_KEY",
]:
    print(f"{key}={'set' if os.getenv(key) else 'unset'}")
PY
```
