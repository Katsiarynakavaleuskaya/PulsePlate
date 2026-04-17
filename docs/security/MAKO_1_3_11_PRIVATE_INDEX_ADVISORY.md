# `mako 1.3.11` approved-index availability advisory

## Summary

`PR #1440` keeps the patched exact pin `mako==1.3.11`. The blocker is not
upstream availability: the patched release is published on PyPI, but the
approved private Python proxy still lags that release on `17 April 2026`.

To avoid a vulnerable repin while keeping the canonical private-proxy contract
as the default path, the repo now uses a **time-boxed, exact-wheel fallback**
for `mako 1.3.11` on Linux `amd64`:

- exact package: `mako`
- exact version: `1.3.11`
- exact wheel filename for the pure-Python `py3-none-any` release
- exact `sha256` digest
- explicit artifact-scoped expiry in `scripts/ci/emergency_python_wheels.json:87`
- fallback scope limited to the approved-proxy install path used by CI and Docker

This is a narrow security-hotfix intake path, not a broad `--extra-index-url`
policy change.

## Governance

- **Owner:** @katsiaryna_kavaleuskaya
- **Active date:** 2026-04-17
- **Current PR:** `PR #1440`
- **Removal backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-mako-private-index-sync`

## Current repo state (2026-04-17)

- **Current branch pins:** `requirements.txt`, `requirements-dev.txt`,
  `requirements-ci-lite.txt`, and `requirements-lock.txt` require `mako 1.3.11`.
- **Failure mode observed:** current-head CI showed the approved private index
  still exposing only `1.3.10`, which failed locked install preflight for
  `lint`, `security`, `OpenAPI sync`, and `test-pr (3.13)` on the active PR.
- **Fallback source of truth:** `scripts/ci/emergency_python_wheels.json:1`
- **Atomic wheel verification:** `scripts/ci/install_locked_python_requirements.py:401`
- **Fallback staging path:** `scripts/ci/install_locked_python_requirements.py:434`
- **Direct-proxy retry after proxy miss:** `scripts/ci/install_locked_python_requirements.py:870`
- **Shared CI wiring:** `.github/actions/python-setup/action.yml:70`
- **Docker wiring:** `Dockerfile:74`

## Operational decision

1. Keep PyPI as the upstream origin for emergency security intake.
2. Keep the approved private proxy as the primary package source.
3. Allow only the exact `mako 1.3.11` wheel listed in the manifest while the
   proxy is stale, without extending the default expiry window of unrelated
   emergency-wheel entries.
4. Remove the manifest-driven fallback once the approved proxy serves
   `1.3.11` natively.

## Prohibited shortcuts

- Do **not** repin below `1.3.11` to make CI green.
- Do **not** add broad `--extra-index-url` or unrestricted public PyPI installs.
- Do **not** widen this manifest into a generic package bypass lane.

## References

- `scripts/ci/emergency_python_wheels.json:1`
- `scripts/ci/install_locked_python_requirements.py:401`
- `scripts/ci/install_locked_python_requirements.py:434`
- `scripts/ci/install_locked_python_requirements.py:870`
- `.github/actions/python-setup/action.yml:70`
- `Dockerfile:74`
- `docs/security/GHSA-v92g-xgxw-vvmm-mako.md:1`
