# GHSA-39q2-94rc-95cp - dompurify

## Summary

- Package: `dompurify`
- GHSA: `GHSA-39q2-94rc-95cp`
- Severity: medium
- Current repo floor: `3.4.10`
- Current repo scope: frontend npm override and resolved lock entry

This advisory was originally remediated by raising the frontend override floor
to `3.4.0`. A later June 2026 Dependabot batch reported additional `dompurify`
findings against versions below the newer safe floor. The current repo floor is
therefore `3.4.10`, the latest npm release observed on 2026-06-16.

## Repo Evidence

- `frontend/package.json:92` - `overrides.dompurify = 3.4.10`
- `frontend/package-lock.json:5568` -
  `packages["node_modules/dompurify"].version = 3.4.10`
- `frontend/package-lock.json:5569` - `packages["node_modules/dompurify"].resolved`
  uses the npm registry tarball `dompurify-3.4.10.tgz`
- `tests/test_frontend_dependency_guards.py:19` - frontend guard floor is
  `Version("3.4.10")`
- `tests/test_frontend_dependency_guards.py:44` - guard asserts package override
  floor, lockfile resolution floor, and npm-registry provenance

## Validation

```bash
npm --prefix frontend install --package-lock-only --ignore-scripts
.venv/bin/python -m pytest -q tests/test_frontend_dependency_guards.py
```

## Notes

- `frontend/package-lock.json` still shows `jspdf` requesting `dompurify` via
  `^3.3.1`, but the repo-owned override forces the resolved artifact to `3.4.10`.
- This note is intentionally separate from the older `CVE-2026-0540` history
  because the current lane closes a different advisory batch with a higher patched floor.
