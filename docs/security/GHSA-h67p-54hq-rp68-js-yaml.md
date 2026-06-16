# GHSA-h67p-54hq-rp68 - js-yaml

## Summary

- Package: `js-yaml`
- GHSA: `GHSA-h67p-54hq-rp68`
- CVE: `CVE-2026-53550`
- Severity: medium
- Current repo floor: `4.2.0`
- Current repo scope: frontend npm override and resolved lock entry

GitHub Dependabot alert `#164` reported `js-yaml` versions `<=4.1.1` from
`frontend/package-lock.json`. The repo already had a safe top-level
`node_modules/js-yaml@4.2.0`, but `@redocly/openapi-core` still resolved a
nested `node_modules/@redocly/openapi-core/node_modules/js-yaml@4.1.1`.

This lane adds a manifest-backed frontend override and regenerates the lockfile
so every resolved `js-yaml` package entry lands on the npm `4.2.0` release.

## Repo Evidence

- `frontend/package.json:94` - `overrides.js-yaml = 4.2.0`
- `frontend/package-lock.json:7347` - `packages["node_modules/js-yaml"].version = 4.2.0`
- `frontend/package-lock.json` - no resolved package entry remains at
  `node_modules/@redocly/openapi-core/node_modules/js-yaml`
- `tests/test_frontend_dependency_guards.py:20` - frontend guard floor is
  `Version("4.2.0")`
- `tests/test_frontend_dependency_guards.py:82` - guard scans every lock package
  path ending in `node_modules/js-yaml`

## Validation

```bash
npm --prefix frontend install --package-lock-only --ignore-scripts
npm --prefix frontend ls dompurify js-yaml --package-lock-only --all
.venv/bin/python -m pytest -q tests/test_frontend_dependency_guards.py
```

## Notes

- `@redocly/openapi-core` still declares `js-yaml: 4.1.1` in its dependency
  metadata, but npm override resolution dedupes the actual installed lock entry
  to `node_modules/js-yaml@4.2.0`.
- `ws` / Storybook audit findings are intentionally out of scope for this
  `dompurify` / `js-yaml` Dependabot lane.
