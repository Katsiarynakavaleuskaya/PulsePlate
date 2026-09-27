# Private Python Proxy Health Gate

## Purpose

The private Python proxy is a canonical bootstrap dependency for PulsePlate. The
health gate makes proxy and mirror failures fail fast before expensive Python CI
jobs spend time inside dependency installation.

This is an infra/dependency gate. It does not repair Cloudflare, DigitalOcean,
devpi, Starlette/httpx compatibility, Docker images, runtime application code,
or dependency lockfiles.

## Protected Contract

Evidence anchor: `scripts/ci/check_private_python_proxy_health.py:784` defines
the default representative project set, and
`tests/test_private_python_proxy_workflow_contract.py:62` validates the CI
health job command contract.

- `PULSEPLATE_PYTHON_INDEX_URL` must stay credential-free.
- The default packages host is `packages.pulseplate.app`.
- Public package hosts such as `pypi.org`, `test.pypi.org`, and
  `files.pythonhosted.org` are rejected for the canonical index URL.
- Inline Basic Auth URLs are rejected. Authenticated reads use non-root CI
  credentials through temporary `.netrc` handling. Pull-request and non-main
  branch diagnostics use repository `vars` only; protected `main` checks may
  create a temporary `.netrc` from non-root `DEVPI_CI_USER` /
  `DEVPI_CI_PASSWORD` secrets before probing project pages.
- The checker probes Simple API project pages under the configured simple root,
  for example `root/pulseplate/+simple/aiosqlite/`.
- Same-host wrong roots such as `https://packages.pulseplate.app/` or
  `https://packages.pulseplate.app/simple/` are rejected because they do not
  exercise the canonical devpi root `root/pulseplate/+simple/`.
- HTTP 200 is not enough. Representative pages must include exact versions from
  the pinned requirements files, including the CI-lite, test-only, and dev-tool
  pins used by `ci-test`, lint, and pre-commit jobs.
- The representative health gate scopes exact-pin conflict detection to probed
  projects via `parse_exact_pins_for_projects(...)`. This lets the CI gate
  include `requirements-dev.txt` without failing on unrelated cross-profile
  transitive drift, while still failing closed when a probed package has
  conflicting exact pins. The general `parse_exact_pins(...)` helper remains a
  strict all-package conflict detector.

## Failure Classes

- `origin_unhealthy`: Cloudflare/devpi origin path is unhealthy, including HTTP
  521/522/5xx or Cloudflare origin-error bodies.
- `tls_or_connect_timeout`: the origin or edge path did not respond inside the
  bounded timeout.
- `empty_project_page` / `simple_page_malformed`: the project page is reachable
  but does not look like a usable Simple API page.
- `mirror_lag_exact_pin_missing`: the page is reachable but does not advertise
  the exact locked version.
- `credentialed_index_url`, `public_index_url`, and `unexpected_packages_host`:
  the bootstrap source violates supply-chain policy.

## Operational Boundary

`packages.pulseplate.app` and the marketing apex `pulseplate.app` are separate
operational surfaces. A marketing apex 521 can be an intentional release gate;
`packages.pulseplate.app` returning 521 is a CI/dependency blocker.

The emergency wheel manifest is not an origin-down fallback. It is only a
time-boxed exact-pin mirror-lag bridge for entries explicitly listed in
`scripts/ci/emergency_python_wheels.json`.

## Validation

Use focused validation for this machine-heavy CI/tooling lane:

```bash
python3 scripts/ci/check_private_python_proxy_health.py \
  --requirements-file requirements.txt \
  --requirements-file requirements-ci-lite.txt \
  --requirements-file requirements-test.txt \
  --requirements-file requirements-dev.txt \
  --project aiosqlite \
  --project cryptography \
  --project requests \
  --project pytest-xdist \
  --project hypothesis \
  --project mypy \
  --project ruff \
  --project librt \
  --project ast-serialize \
  --project pgvector
python3 scripts/ci/install_locked_python_requirements.py --preflight-only
python -m pytest -q tests/test_private_python_proxy_health.py
python -m pytest -q tests/test_private_python_proxy_workflow_contract.py
python -m pytest -q tests/test_python_supply_chain_controls.py
make validate-changed
pre-commit run --all-files
```

Full `make verify` remains the normal merge-readiness gate, but this lane may
use the operator-approved machine-heavy exception when the PR body and fixed
mapping document the deferral and current-head CI carries the heavy signal.

## Rollback

Revert the checker, workflow job, tests, and documentation updates. No runtime
state, package pins, Docker base image, or application behavior changes are part
of this gate.
