# Emergency Wheel Mirror Parity Premortem

## Goal

Retire the runtime-effective emergency wheel fallback set only after proving the
approved private proxy can serve every previously active emergency wheel filename.
Keep the manifest file as an empty compatibility marker so this PR does not
widen into CI, Docker, or installer path removal.

## Scope

- Add a fail-closed all-entry parity checker for `scripts/ci/emergency_python_wheels.json`.
- Wire that checker into the existing private Python proxy health job after the
  representative health probe.
- Allow `install_locked_python_requirements.py` to load the retired empty marker
  as no active emergency artifacts.
- Update tests, runbook, dependency docs, and backlog state for retired-empty
  behavior.

## Out Of Scope

- Starlette/httpx runtime cleanup.
- FastAPI, Pydantic, app behavior, or lockfile refreshes.
- Docker runtime behavior or deletion of emergency manifest references.
- iOS, web, macOS, Cloudflare, or devpi operator configuration changes.

## Premortem Risks

| Risk | Mitigation |
| --- | --- |
| Representative health is mistaken for all-entry parity. | Add `check_emergency_wheel_mirror_parity.py` and run it after `check_private_python_proxy_health.py`. |
| Empty manifests are accepted accidentally. | `load_emergency_wheel_manifest` accepts only the dated `Retired:` marker as empty. |
| A future active entry points at a public or credentialed artifact URL. | The parity checker validates host, HTTPS, userinfo, query/fragment, basename, and sha256 before any proxy probe. |
| Missing ABI-specific wheels are hidden by package/version checks. | The checker compares every active manifest filename against the approved project page and validates Python target compatibility. |
| Protected-main `.netrc` credentials linger after the health job. | The workflow adds an `always()` cleanup step after parity. |
| Active expired entries silently disappear. | The parity checker fails active expired entries; only the retired marker can have `artifacts: []`. |

## Synthesis

It is 48 hours from now and this infra PR made dependency CI worse. The most
likely failure would be a false-green parity claim caused by checking only
representative projects instead of all prior emergency artifacts. The most
dangerous failure would be accidentally reopening a public wheel bypass or
credential leak while trying to retire the emergency path.

Hidden assumption: the approved proxy proof remains valid only if the checker
continues to validate exact filenames and not just package/version pairs.

Decision: proceed with changes. All premortem findings are addressed in this
PR rather than deferred.

## Finding Closure

| Finding | Disposition | Evidence |
| --- | --- | --- |
| Representative health is not all-entry parity. | FIXED | `scripts/ci/check_emergency_wheel_mirror_parity.py`; `.github/workflows/ci.yml` step `Emergency wheel mirror parity`. |
| Empty manifest could silently disable fallback by accident. | FIXED | `install_locked_python_requirements.py` accepts only the dated `Retired:` marker; `tests/test_install_locked_python_requirements.py` covers valid and malformed empty markers. |
| Future active entries could fetch or trust public artifacts. | FIXED | Parity checker validates artifact URL host/shape, rejects public-host Simple API hrefs, and never downloads artifact URLs; `tests/test_emergency_wheel_mirror_parity.py` rejects wrong hosts and public Simple hrefs. |
| ABI-specific missing wheels could be masked. | FIXED | Parity checker validates exact filenames, wheel compatibility, and per-target Python coverage; active pre-retirement manifest proof showed `artifacts=34 missing=0`. |
| Protected-main `.netrc` could linger. | FIXED | `.github/workflows/ci.yml` cleanup step uses `always()` and removes `$HOME/.netrc`. |
| Active expired entries could be ignored. | FIXED | Parity checker raises on active expired artifacts; dedicated test covers the failure. |

## Experiment Runner

Oracle-only governance reviewer result:
`artifacts/orchestration/experiments/results/exp-9f9bdba0070d.json`.

- Status: `accepted`
- Contribution kind: `commit_decision`
- Co-author trailer required:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
- Evidence: implementation commit `9af0917c1` includes the required trailer.

## Validation Plan

- `python -m pytest -q tests/test_emergency_wheel_mirror_parity.py`
- `python -m pytest -q tests/test_private_python_proxy_health.py`
- `python -m pytest -q tests/test_private_python_proxy_workflow_contract.py`
- `python -m pytest -q tests/test_install_locked_python_requirements.py`
- `python -m pytest -q tests/test_python_supply_chain_controls.py`
- `python3 scripts/ci/check_emergency_wheel_mirror_parity.py --manifest scripts/ci/emergency_python_wheels.json --python-version 3.11 --python-version 3.12 --python-version 3.13 --format text`
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only`
- `make validate-changed`
- `pre-commit run --all-files`
