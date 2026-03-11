# GHSA-v8w9-8mx6-g223 — hono (transitive via @modelcontextprotocol/sdk) — Dependabot alert #48 remediation

## Summary

- **GHSA**: GHSA-v8w9-8mx6-g223
- **CVE**: none assigned as of March 11, 2026
- **Package**: `hono`
- **Alert type**: GitHub Dependabot alert `#48`
- **Scope**: transitive runtime dependency in the root npm graph

Dependabot reported a prototype-pollution hardening issue in `hono` when
`parseBody({ dot: true })` allows `__proto__` path segments. The first patched
version is `4.12.7`.

## Root Cause

The root npm graph brings in `hono` transitively:

- `package.json:24` — root direct dependency on `@goplus/agentguard`
- `package-lock.json:681` — `@modelcontextprotocol/sdk` depends on `hono`
- `package-lock.json:1851` — resolved vulnerable `hono` node was `4.12.5`

## Remediation Implemented

- Refreshed the root lockfile to resolve `hono` `4.12.7` from the npm registry.
- Kept the remediation lockfile-only because the existing semver range already
  admits the patched transitive release.
- Added a deterministic root lockfile guard so `hono < 4.12.7` does not return
  silently in future updates.

## Evidence Anchors

- `package-lock.json:1851` — resolved `hono` entry updated to `4.12.7`
- `tests/test_root_npm_dependency_guards.py:1` — deterministic regression guard
- `docs/security/GHSA-v8w9-8mx6-g223-hono.md:1` — canonical remediation record

## Validation

```bash
npm update hono --package-lock-only
npm ci
pytest -q tests/test_root_npm_dependency_guards.py
pre-commit run --all-files
make verify
```

## Notes

- This remediation supersedes the raw Dependabot PR `#1098` with a human-owned
  canonical PR so the repo-specific Phase 2 and merge-readiness contracts can be
  satisfied.
- No runtime API, schema, or application code changes were required.
