# `cryptography 46.0.7` approved-index availability advisory

## Summary

`PR #1378` keeps the patched exact pin `cryptography==46.0.7`. The blocker is
not upstream availability: the patched release is published on PyPI, but the
approved private Python proxy still lags that release on `09 April 2026`.

To avoid a vulnerable repin while keeping the canonical private-proxy contract
as the default path, the repo now uses a **time-boxed, exact-wheel fallback**
for `cryptography 46.0.7`:

- exact package: `cryptography`
- exact version: `46.0.7`
- exact wheel filenames for `linux/amd64`
- exact `sha256` digests
- explicit expiry in `scripts/ci/emergency_python_wheels.json:4`

This is a narrow security-hotfix intake path, not a broad `--extra-index-url`
policy change.

## Governance

- **Owner:** @katsiaryna_kavaleuskaya
- **Active date:** 2026-04-09
- **Current PR:** `PR #1378`
- **Removal backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cryptography-private-index-sync`

## Current repo state (2026-04-09)

- **Current branch pins:** `requirements.txt`, `requirements-ci-lite.txt`,
  `requirements-dev.txt`, `requirements-lock.txt`, and `constraints.txt`
  require `cryptography 46.0.7` / `>=46.0.7`.
- **Fallback source of truth:** `scripts/ci/emergency_python_wheels.json:1`
- **Atomic wheel verification:** `scripts/ci/install_locked_python_requirements.py:351`
- **Fallback staging path:** `scripts/ci/install_locked_python_requirements.py:387`
- **Wheelhouse retry after proxy miss:** `scripts/ci/install_locked_python_requirements.py:761`
- **Direct-proxy retry after proxy miss:** `scripts/ci/install_locked_python_requirements.py:799`
- **Shared CI wiring:** `.github/actions/python-setup/action.yml:55`
- **Docker wiring:** `Dockerfile:248`

## Operational decision

1. Keep PyPI as the upstream origin for emergency security intake.
2. Keep the approved private proxy as the primary package source.
3. Allow only the exact `cryptography 46.0.7` wheels listed in the manifest
   while the proxy is stale.
4. Remove the manifest-driven fallback once the approved proxy serves
   `46.0.7` natively.

## Prohibited shortcuts

- Do **not** repin below `46.0.7` to make CI green.
- Do **not** add broad `--extra-index-url` or unrestricted public PyPI installs.
- Do **not** widen this manifest into a generic package bypass lane.

## References

- `scripts/ci/emergency_python_wheels.json:4`
- `scripts/ci/install_locked_python_requirements.py:351`
- `scripts/ci/install_locked_python_requirements.py:387`
- `scripts/ci/install_locked_python_requirements.py:761`
- `scripts/ci/install_locked_python_requirements.py:799`
- `.github/actions/python-setup/action.yml:55`
- `Dockerfile:248`
- `docs/security/CVE-2026-26007-cryptography.md:1`
