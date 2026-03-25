# GHSA-gc5v-m9x4-r6x2 — requests runtime/dev lock remediation

## Summary

- Advisory: `GHSA-gc5v-m9x4-r6x2`
- Package: `requests`
- Affected repo surfaces before remediation:
  - `requirements.txt:248`
  - `requirements-dev.txt:204`
  - `requirements-lock.txt:248`
- Fixed floor adopted by this repo: `requests>=2.33.0`

## Reason

`pip-audit` blocked the standard pre-push workflow because the repo baseline on
`origin/main` still pinned `requests==2.32.5`, which is below the safe version
required by the advisory. This was a repository-wide dependency blocker, not a
regression introduced by the verify-env tooling branch.

## Remediation Contract

The security-unblock PR applies the fix on all tracked dependency surfaces:

- `requirements.in` adds the canonical floor
- `constraints.txt` mirrors the floor for flexible installs
- `requirements.txt` pins the resolved safe version
- `requirements-dev.txt` pins the resolved safe version
- `requirements-lock.txt` pins the resolved safe version
- `tests/fixtures/dependency_security_schema.json` adds `requests: 2.33.0`

## Verification

Run:

```bash
rg -n "^requests" requirements.in requirements.txt requirements-dev.txt requirements-lock.txt constraints.txt
pytest -q tests/test_dependency_security_guard.py
pre-commit run --all-files
```
