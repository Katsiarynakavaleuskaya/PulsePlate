# GHSA-whj4-6x5x-4v2j — pillow runtime/dev lock remediation

## Summary

- Advisory: `GHSA-whj4-6x5x-4v2j`
- Package: `pillow`
- Fixed floor adopted by this repo: `pillow>=12.2.0`
- Tracked repo surfaces remediated by this PR:
  - `requirements.in`
  - `requirements-dev.in`
  - `requirements-ci-lite.in`
  - `constraints.txt`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `requirements-ci-lite.txt`
  - `requirements-lock.txt`
  - `tests/fixtures/dependency_security_schema.json`

## Reason

`pip-audit` blocked the standard pre-push workflow because the repo baseline on
`origin/main` still pinned `pillow==12.1.1`, which is below the safe version
required by the advisory. This was a repository-wide dependency blocker, not a
regression introduced by the Figma docs-only audit branch.

## Remediation Contract

The security-unblock PR applies the fix on all relevant dependency surfaces:

- `requirements.in` adds the canonical runtime floor
- `requirements-dev.in` mirrors the floor for dev tooling surfaces
- `requirements-ci-lite.in` mirrors the floor for lightweight CI installs
- `constraints.txt` mirrors the floor for flexible installs
- `requirements.txt` pins the resolved safe version
- `requirements-dev.txt` pins the resolved safe version
- `requirements-ci-lite.txt` pins the resolved safe version
- `requirements-lock.txt` pins the resolved safe version
- `tests/fixtures/dependency_security_schema.json` adds `pillow: 12.2.0`

## Evidence Anchors

- `requirements.in`
- `requirements-dev.in`
- `requirements-ci-lite.in`
- `constraints.txt`
- `requirements.txt`
- `requirements-dev.txt`
- `requirements-ci-lite.txt`
- `requirements-lock.txt`
- `tests/fixtures/dependency_security_schema.json`

## Verification

Run:

```bash
rg -n "^pillow" requirements.in requirements-dev.in requirements-ci-lite.in constraints.txt requirements.txt requirements-dev.txt requirements-ci-lite.txt requirements-lock.txt
pytest -q tests/test_dependency_security_guard.py
pre-commit run --all-files
```
