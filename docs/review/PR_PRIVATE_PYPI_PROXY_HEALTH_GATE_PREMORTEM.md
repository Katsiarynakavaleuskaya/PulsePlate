# Private PyPI Proxy Health Gate Premortem

## Scope

Proposed PR title:

```text
ci(deps): add private PyPI proxy health gate and mirror parity contract
```

This PR adds a stdlib-only private proxy health checker, an early CI gate, focused
tests, and dependency docs. It follows operator recovery of
`packages.pulseplate.app`; it does not repair the Cloudflare/DigitalOcean/devpi
origin itself.

## Phase A Evidence

- Canonical project page probe:
  `https://packages.pulseplate.app/root/pulseplate/+simple/aiosqlite/`
  returned repeated HTTP 200 responses after DigitalOcean restart.
- `scripts/ci/install_locked_python_requirements.py --preflight-only` exited 0.
- Representative exact pins were present on project pages:
  `aiosqlite==0.22.1`, `pydantic-core==2.41.5`,
  `cryptography==48.0.1`, and `requests==2.33.0`.

## Risks And Mitigations

Frame: it is 48 hours from now, this CI/dependency tooling PR made the nightly
failure harder to diagnose. We are looking backward to understand why.

| Risk | Mitigation |
| --- | --- |
| PR leaks package proxy credentials in logs or workflow env. | Pull-request resolver uses repository vars only; checker rejects URL userinfo and redacts diagnostics. |
| Health job becomes advisory instead of fail-closed. | Job has no `continue-on-error`; downstream Python setup jobs declare `needs: private_python_proxy_health`. |
| Probe checks the wrong surface. | Checker builds PEP 503 project pages under the configured simple root and rejects the marketing apex. |
| HTTP 200 hides mirror lag. | Checker verifies exact locked versions on representative project pages. |
| Public PyPI fallback slips in. | Checker rejects public hosts and workflow uses no pip install or public index fallback. |
| The gate blocks CI while origin is down. | Expected behavior; operator recovery must restore `packages.pulseplate.app` before dependency-heavy jobs run. |
| Full local `make verify` is too heavy for this tooling lane. | Use the operator-approved machine-heavy exception with focused local gates and current-head CI as the heavy signal. |

## Premortem Synthesis

Most likely failure: the workflow gate is present but not truly upstream of every
dependency-heavy job, so the Python matrix still burns time before proxy failure
classification. Mitigation is an explicit workflow contract test requiring every
job that uses `.github/actions/python-setup` to depend on
`private_python_proxy_health`.

Most dangerous failure: the checker or workflow prints credential-bearing index
URLs during diagnostics. Mitigation is fail-closed URL validation before output,
safe result summaries, and pull-request diagnostics that read repository vars
instead of secrets.

Hidden assumption: the private packages host may be healthy enough to return
HTTP 200 while still missing exact locked artifacts. The checker therefore
classifies exact-pin absence as `mirror_lag_exact_pin_missing` instead of
accepting a non-empty project page.

Decision: proceed with changes. The PR is admissible only with the checker,
workflow placement tests, docs/runbook updates, focused local gates, and
operator-approved machine-heavy `make verify` deferral documented in the PR
body.

## Out Of Scope

- Starlette/httpx/FastAPI/Pydantic migration.
- Dependency lockfile refresh.
- Docker base image or runtime changes.
- Emergency wheel manifest retirement.
- Cloudflare/DigitalOcean/devpi configuration changes in the repo.
- Marketing apex behavior.

## Required Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
PYTHONPATH= python3 -I -S scripts/ci/check_private_python_proxy_health.py --help
python -m pytest -q tests/test_private_python_proxy_health.py
python -m pytest -q tests/test_private_python_proxy_workflow_contract.py
python -m pytest -q tests/test_python_supply_chain_controls.py
python3 scripts/ci/check_private_python_proxy_health.py \
  --requirements-file requirements.txt \
  --requirements-file requirements-ci-lite.txt \
  --requirements-file requirements-test.txt \
  --project aiosqlite \
  --project cryptography \
  --project requests \
  --project pytest-xdist \
  --project hypothesis \
  --project pgvector
python3 scripts/ci/install_locked_python_requirements.py --preflight-only
make validate-changed
pre-commit run --all-files
```

Do not claim merge readiness until post-open review passes, current-head CI, and
the repo merge-readiness wrapper satisfy the standard PR lifecycle.
