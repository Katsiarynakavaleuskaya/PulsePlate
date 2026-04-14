# `pillow 12.2.0` approved-index availability advisory

## Summary

`PR #1415` keeps the patched exact pin `pillow==12.2.0`. The blocker is not
upstream availability: the patched release is published on PyPI, but the
approved private Python proxy still lags that release on `13 April 2026`.

To avoid a vulnerable repin while keeping the canonical private-proxy contract
as the default path, the repo now uses a **time-boxed, exact-wheel fallback**
for `pillow 12.2.0` on Linux `amd64` / CPython `3.11`, `3.12`, and `3.13`:

- exact package: `pillow`
- exact version: `12.2.0`
- exact wheel filenames for supported `linux/amd64` CI runtimes
- exact `sha256` digests
- explicit expiry in `scripts/ci/emergency_python_wheels.json:4`
- fallback scope limited to Linux `amd64` CI and Docker install lanes only

This is a narrow security-hotfix intake path, not a broad `--extra-index-url`
policy change.

## Governance

- **Owner:** @katsiaryna_kavaleuskaya
- **Active date:** 2026-04-13
- **Current PR:** `PR #1415`
- **Removal backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pillow-private-index-sync`

## Current repo state (2026-04-13)

- **Current branch pins:** `requirements.txt`, `requirements-ci-lite.txt`, and
  `requirements-lock.txt` require `pillow 12.2.0`.
- **Failure mode observed:** current-head CI and Docker installs showed the
  approved private index exposing only `12.1.1`, which failed locked install
  for `lint`, `security`, `OpenAPI sync`, `test-pr`, and Docker image lanes
  across the active `3.11` / `3.12` / `3.13` CI matrix.
- **Fallback source of truth:** `scripts/ci/emergency_python_wheels.json:1`
- **Atomic wheel verification:** `scripts/ci/install_locked_python_requirements.py:401`
- **Fallback staging path:** `scripts/ci/install_locked_python_requirements.py:434`
- **Direct-proxy retry after proxy miss:** `scripts/ci/install_locked_python_requirements.py:870`
- **Shared CI wiring:** `.github/actions/python-setup/action.yml:55`
- **Docker wiring:** `Dockerfile:55`

## Operational decision

1. Keep PyPI as the upstream origin for emergency security intake.
2. Keep the approved private proxy as the primary package source.
3. Allow only the exact `pillow 12.2.0` wheels listed in the manifest while the
   proxy is stale.
4. Remove the manifest-driven fallback once the approved proxy serves
   `12.2.0` natively.

## Prohibited shortcuts

- Do **not** repin below `12.2.0` to make CI green.
- Do **not** add broad `--extra-index-url` or unrestricted public PyPI installs.
- Do **not** widen this manifest into a generic package bypass lane.

## References

- `scripts/ci/emergency_python_wheels.json:1`
- `scripts/ci/install_locked_python_requirements.py:401`
- `scripts/ci/install_locked_python_requirements.py:434`
- `scripts/ci/install_locked_python_requirements.py:870`
- `.github/actions/python-setup/action.yml:55`
- `Dockerfile:55`
