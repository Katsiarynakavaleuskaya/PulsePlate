# GHSA-39q2-94rc-95cp - dompurify

## Summary

- Package: `dompurify`
- GHSA: `GHSA-39q2-94rc-95cp`
- Severity: medium
- Fixed version: `3.4.0`
- Current repo scope: frontend npm override and resolved lock entry

This lane remediates the new `dompurify` logic-bypass advisory by raising the
frontend override floor from `3.3.2` to `3.4.0` and regenerating the frontend
lockfile so the resolved npm artifact also lands on `3.4.0`.

## Repo Evidence

- `frontend/package.json:89` - `overrides.dompurify = 3.4.0`
- `frontend/package-lock.json:5885` - lockfile contains `node_modules/dompurify`
- `frontend/package-lock.json:5886` - resolved version is `3.4.0`
- `frontend/package-lock.json:5887` - resolved source is the npm registry tarball `dompurify-3.4.0.tgz`
- `tests/test_frontend_dependency_guards.py:18` - frontend guard floor is `Version("3.4.0")`
- `tests/test_frontend_dependency_guards.py:25` - guard asserts package override floor
- `tests/test_frontend_dependency_guards.py:34` - guard asserts lockfile resolution floor and npm-registry provenance

## Validation

```bash
npm --prefix frontend install --package-lock-only
pytest -q tests/test_frontend_dependency_guards.py
```

## Notes

- `frontend/package-lock.json:7830` still shows `jspdf` requesting `dompurify` via
  `^3.3.1`, but the repo-owned override forces the resolved artifact to `3.4.0`.
- This note is intentionally separate from the older `CVE-2026-0540` history
  because the current lane closes a different advisory with a higher patched floor.
