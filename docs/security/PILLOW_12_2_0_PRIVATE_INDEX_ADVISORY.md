# `Pillow 12.2.0` approved-index availability advisory

## Summary

`PR #1416` keeps the patched exact pin `pillow==12.2.0` required by
`GHSA-whj4-6x5x-4v2j`. The blocker is not upstream availability: the patched
release is published on PyPI, but the approved private Python proxy still lags
that release on `13 April 2026`.

To avoid a vulnerable repin while keeping the canonical private-proxy contract
as the default path, the repo now uses a **time-boxed, exact-wheel fallback**
for `Pillow 12.2.0`:

- exact package: `pillow`
- exact version: `12.2.0`
- exact wheel filenames for `linux/amd64` / Python `3.13`
- exact `sha256` digests
- explicit expiry in `scripts/ci/emergency_python_wheels.json:4`

This is a narrow security-hotfix intake path, not a broad `--extra-index-url`
policy change and not a weakening of the repo dependency floor.

## Governance

- **Owner:** @katsiaryna_kavaleuskaya
- **Active date:** 2026-04-13
- **Current PR:** `PR #1416`
- **Removal backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pillow-private-index-sync`

## Current repo state (2026-04-13)

- **Current branch pins:** `requirements.txt`, `requirements-ci-lite.txt`, and
  `requirements-lock.txt` require `pillow==12.2.0`.
- **Advisory:** `GHSA-whj4-6x5x-4v2j`
- **Fallback source of truth:** `scripts/ci/emergency_python_wheels.json:1`
- **Atomic wheel verification:** `scripts/ci/install_locked_python_requirements.py:395`
- **Fallback staging path:** `scripts/ci/install_locked_python_requirements.py:433`
- **Wheelhouse retry after proxy miss:** `scripts/ci/install_locked_python_requirements.py:823`
- **Direct-proxy retry after proxy miss:** `scripts/ci/install_locked_python_requirements.py:869`
- **Shared CI wiring:** `.github/actions/python-setup/action.yml:138`
- **Docker wiring:** `Dockerfile:74`, `Dockerfile:272`

## Operational decision

1. Keep the patched repo pin at `pillow==12.2.0`.
2. Keep the approved private proxy as the primary package source.
3. Allow only the exact `Pillow 12.2.0` wheels listed in the manifest while the
   proxy is stale.
4. Remove the manifest-driven fallback once the approved proxy serves
   `12.2.0` natively.

## Prohibited shortcuts

- Do **not** repin below `12.2.0` to make CI green.
- Do **not** add broad `--extra-index-url` or unrestricted public PyPI installs.
- Do **not** widen this manifest into a generic package bypass lane.

## References

- `https://github.com/advisories/GHSA-whj4-6x5x-4v2j`
- `scripts/ci/emergency_python_wheels.json:1`
- `scripts/ci/install_locked_python_requirements.py:395`
- `scripts/ci/install_locked_python_requirements.py:433`
- `scripts/ci/install_locked_python_requirements.py:823`
- `scripts/ci/install_locked_python_requirements.py:869`
- `.github/actions/python-setup/action.yml:138`
- `Dockerfile:74`
- `Dockerfile:272`
