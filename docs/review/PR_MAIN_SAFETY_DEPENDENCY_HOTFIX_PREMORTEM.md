# Premortem: Main Safety Dependency Hotfix After PR #1982

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Packet: `artifacts/orchestration/task_packets/e783c0240b3a.json`

## Frame

It is 48 hours from now. This hotfix made the `main` security state worse. We
are looking backward to understand why.

## Scope Inspected

- `requirements.in`
- `requirements-ci-lite.in`
- `requirements-dev.in`
- `requirements-docker-runtime.in`
- `requirements.txt`
- `requirements-ci-lite.txt`
- `requirements-dev.txt`
- `requirements-docker-runtime.txt`
- `requirements-lock.txt`
- `constraints.txt`
- `requirements-security.txt`
- `scripts/ci/emergency_python_wheels.json`
- `tests/fixtures/dependency_security_schema.json`
- `tests/test_dependency_security_guard.py`
- `tests/test_install_locked_python_requirements.py`
- `tests/test_python_supply_chain_controls.py`
- `docs/security/*`
- `docs/roadmap/BACKLOG_LEDGER.md`

## Failure Modes

### P1: Safety floor is raised in one surface but not all guarded surfaces

**Failure story:** The PR fixes `requirements.txt`, but `requirements-ci-lite`,
Docker runtime, dev, or combined lock surfaces still carry an older pin. Local
Safety looks better on one manifest while another current-head CI job keeps
installing the vulnerable package.

**Underlying assumption:** The runtime lock is the only effective dependency
surface.

**Early warning signs:** `rg` still finds `cryptography==46.0.7`,
`python-multipart==0.0.27`, or `starlette==1.0.1` in requirement surfaces; the
dependency security schema still records old minimums.

**Containment action:** Block PR open until schema and every source/lock surface
carry `48.0.1`, `0.0.31`, and `1.3.1`.

**Disposition:** FIXED. The dependency schema and all guarded source/lock
surfaces now carry the new floors; focused dependency guard tests passed.

### P1: Private index or emergency manifest blocks install before Safety runs

**Failure story:** The dependency pins are correct, but the approved private
Python proxy has not mirrored one new wheel, or the emergency manifest remains
expired. CI fails during setup and never reaches the repaired Safety audit,
leaving `main` red.

**Underlying assumption:** Upstream availability is enough for this repo's
approved proxy path.

**Early warning signs:** `install_locked_python_requirements.py --preflight-only`
reports a resolver miss; `tests/test_install_locked_python_requirements.py` says
the emergency manifest is expired.

**Containment action:** Keep the approved proxy as primary, rotate only exact
needed emergency artifacts with `sha256` and short TTL, and do not add broad
public-index bypasses.

**Disposition:** FIXED for observed local state. `make venv-sync` passed through
the approved proxy/fallback path on the updated locks. The manifest expiry was
rotated to `2026-06-30`, old `cryptography` and `python-multipart` fallback
artifacts were replaced with exact safe-floor wheels, and no `starlette`
fallback was added because no local proxy miss was observed.

### P1: Generated lock churn introduces an unsafe `pip==...` pin

**Failure story:** `pip-compile --allow-unsafe` regenerates dev locks and adds
`pip==26.1.2`. The hotfix removes one Safety failure but reopens the repo's
known pip unsafe-lock alert class.

**Underlying assumption:** Raw pip-compile output is automatically acceptable.

**Early warning signs:** `rg -n "^pip==" requirements-dev.txt requirements-lock.txt`
returns a result; `test_repo_managed_lock_surfaces_do_not_pin_pip` fails.

**Containment action:** Reject raw unsafe `pip` pins and keep the diff limited to
the three Safety-blocked packages plus required evidence.

**Disposition:** FIXED. Generated `pip==...` entries were removed and
`tests/test_dependency_security_guard.py` passed.

### P2: Secrets baseline refresh records local-only artifacts

**Failure story:** Updating wheel `sha256` values requires a detect-secrets
baseline refresh, but the scan captures local `artifacts/orchestration` paths or
cache files. The PR then violates the local-artifact policy or creates noisy
false positives unrelated to the hotfix.

**Underlying assumption:** Any baseline regeneration command is equivalent.

**Early warning signs:** `.secrets.baseline` diff includes `artifacts/`,
`.pytest_cache`, `.ruff_cache`, or filter configuration churn.

**Containment action:** Keep `.secrets.baseline` limited to the three expected
wheel digest fingerprints and timestamp metadata.

**Disposition:** FIXED. The committed baseline delta only rotates the three
`scripts/ci/emergency_python_wheels.json` hash fingerprints and timestamp.

### P2: Starlette compatibility is assumed from resolver success only

**Failure story:** `starlette==1.3.1` installs, but TestClient, WebSocket, cookie,
or app monitoring behavior shifts. CI turns green for Safety but later runtime
tests fail or a user-visible endpoint breaks.

**Underlying assumption:** FastAPI metadata compatibility is enough runtime
proof.

**Early warning signs:** Health/metrics, WebSocket auth, or web session tests
fail on the updated `.venv`.

**Containment action:** Run focused ASGI/runtime smoke tests on the updated
environment before PR open and rely on current-head CI for broader parity.

**Disposition:** FIXED locally. The focused Starlette/FastAPI/WebSocket/session
smoke set passed on `.venv` with `starlette==1.3.1`.

## Synthesis

Most likely failure: the approved proxy or emergency manifest blocks the new
floors before Safety can run. This was most likely because the manifest was
already expired on 2026-06-16.

Most dangerous failure: a hidden lock-surface miss leaves one CI lane on an
older vulnerable pin while the PR claims to restore main security.

Hidden assumption: Safety remediation and install availability are the same
problem. They are separate gates and both must pass.

Revised plan:

- Keep the diff to Python dependency security surfaces only.
- Update every guarded source/lock surface and the deterministic schema.
- Rotate emergency fallback only for observed existing fallback packages and
  short TTL, without adding broad bypasses.
- Treat local Safety as auth-blocked without `SAFETY_API_KEY`; require
  current-head CI `CI / security` to prove the repaired audit.

Pre-merge checklist:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- focused dependency/security pytest bundle
- `make validate-changed`
- `pre-commit run --all-files`
- current-head `CI / security` green with no unresolved actionable reviews
- strict merge-readiness wrapper with auth

## Decision

Proceed with changes. No premortem blocker remains locally, but merge readiness
must still wait for current-head CI Safety evidence because local
`run_safety_audit.py` requires `SAFETY_API_KEY` in `cicd` stage.
