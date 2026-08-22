# GHSA-39q2-94rc-95cp - dompurify

## Summary

- Package: `dompurify`
- GHSA: `GHSA-39q2-94rc-95cp`
- Severity: medium
- Current repo floor: `3.4.13`
- Current repo scope: frontend npm override and resolved lock entry

This advisory was originally remediated by raising the frontend override floor
to `3.4.0`. A later June 2026 Dependabot batch reported additional `dompurify`
findings against versions below newer affected boundaries. The historical lane
reached `3.4.10`; the 2026-08-21 seven-identity successor now selects
`3.4.13`. The current transition owner is
`docs/security/FRONTEND_NPM_SECURITY_BATCH_REMEDIATION_CLASS.md`.

## Repo Evidence

- `frontend/package.json:92` - `overrides.dompurify = 3.4.13`
- `frontend/package-lock.json:5568` -
  `packages["node_modules/dompurify"].version = 3.4.13`
- `frontend/package-lock.json:5569` - `packages["node_modules/dompurify"].resolved`
  uses the npm registry tarball `dompurify-3.4.13.tgz`
- `tests/test_frontend_dependency_guards.py:38` - frontend guard floor is
  `Version("3.4.13")`
- `tests/test_frontend_dependency_guards.py:188` - the current target table owns
  manifest carrier, full affected ranges, exact floor, and selected output

## Validation

```bash
npm --prefix frontend install --package-lock-only --ignore-scripts
.venv/bin/python -m pytest -q tests/test_frontend_dependency_guards.py
```

## Notes

- `frontend/package-lock.json` still shows `jspdf` requesting `dompurify` via
  `^3.3.1`, but the repo-owned override forces the resolved artifact to `3.4.13`.
- This note is intentionally separate from the older `CVE-2026-0540` history
  because the current lane closes a different advisory batch with a higher patched floor.
