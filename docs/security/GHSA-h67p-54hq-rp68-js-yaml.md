# GHSA-h67p-54hq-rp68 - js-yaml

## Summary

- Package: `js-yaml`
- GHSA: `GHSA-h67p-54hq-rp68`
- CVE: `CVE-2026-53550`
- Severity: medium
- Current repo floor: `4.3.1`
- Current repo scope: frontend npm override and resolved lock entry

GitHub Dependabot alert `#164` reported `js-yaml` versions `<=4.1.1` from
`frontend/package-lock.json`. The repo already had a safe top-level
`node_modules/js-yaml@4.2.0`, but `@redocly/openapi-core` still resolved a
nested `node_modules/@redocly/openapi-core/node_modules/js-yaml@4.1.1`.

That historical lane added a manifest-backed frontend override and regenerated
the lockfile so every resolved `js-yaml` package entry landed on `4.2.0`. The
2026-08-21 seven-identity successor raises the same carrier to `4.3.1` for
`GHSA-52cp-r559-cp3m` and `GHSA-5p4m-2wfm-xmqj`. Its current transition owner is
`docs/security/FRONTEND_NPM_SECURITY_BATCH_REMEDIATION_CLASS.md`; the chronology
recorded here remains intact.

## Repo Evidence

- `frontend/package.json:94` - `overrides.js-yaml = 4.3.1`
- `frontend/package-lock.json:7347` - `packages["node_modules/js-yaml"].version = 4.3.1`
- `frontend/package-lock.json` - no resolved package entry remains at
  `node_modules/@redocly/openapi-core/node_modules/js-yaml`
- `tests/test_frontend_dependency_guards.py:39` - frontend guard floor is
  `Version("4.3.1")`
- `tests/test_frontend_dependency_guards.py:188` - the current target table owns
  complete affected ranges, the override carrier, and lock postcondition

## Validation

```bash
npm --prefix frontend install --package-lock-only --ignore-scripts
npm --prefix frontend ls dompurify js-yaml --package-lock-only --all
.venv/bin/python -m pytest -q tests/test_frontend_dependency_guards.py
```

## Notes

- `@redocly/openapi-core` still declares `js-yaml: 4.1.1` in its dependency
  metadata, but npm override resolution dedupes the actual installed lock entry
  to `node_modules/js-yaml@4.3.1`.
- This projection does not rewrite the older GHSA remediation or claim that
  future advisories, provider refresh, or the whole frontend security state are
  complete.
