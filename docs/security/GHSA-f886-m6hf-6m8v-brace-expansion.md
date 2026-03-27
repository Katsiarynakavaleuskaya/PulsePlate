# GHSA-f886-m6hf-6m8v — brace-expansion (transitive via @goplus/agentguard) — Dependabot alert #73 remediation

## Summary

- **GHSA**: GHSA-f886-m6hf-6m8v
- **CVE**: CVE-2026-33750
- **Package**: `brace-expansion`
- **Alert type**: GitHub Dependabot alert `#73`
- **Scope**: transitive runtime dependency in the root npm graph

Dependabot reported a resource-consumption issue in `brace-expansion` where a
zero-step range such as `{1..2..0}` can hang the process and exhaust memory.
The first patched version is `5.0.5`.

## Root Cause

The root npm graph brings in `brace-expansion` transitively:

- `package.json:29` — root direct dependency on `@goplus/agentguard`
- `package-lock.json` — `@goplus/agentguard` depends on `glob`
- `package-lock.json` — `glob` depends on `minimatch`
- `package-lock.json` — resolved vulnerable `brace-expansion` node was `2.0.2`

The initial lockfile-only attempt failed runtime smoke because `minimatch@9`
expects the old `brace-expansion` default export shape. The final remediation
therefore refreshes the direct `@goplus/agentguard` dependency and the
`glob -> minimatch -> brace-expansion` chain together so the transitive graph is
internally consistent while still keeping the change on the npm metadata
surface.

## Remediation Implemented

- Refreshed the root direct dependency on `@goplus/agentguard` to `^1.0.12`.
- Added root npm `overrides` entries for `glob`, `minimatch`, and
  `brace-expansion` so the entire transitive chain resolves to a compatible,
  patched set.
- Refreshed the root lockfile under the repo-canonical Node `22.22.1` runtime.
- Kept the remediation scoped to package-manager metadata only; no Python or
  bridge runtime code paths were modified.
- Added deterministic root lockfile guards so `brace-expansion < 5.0.5` does
  not silently return in future updates.

## Evidence Anchors

- `package.json` — direct dependency and override set for the patched graph
- `package-lock.json` — resolved `glob` / `minimatch` / `brace-expansion` chain updated
- `tests/test_root_npm_dependency_guards.py` — deterministic regression guard
- `docs/security/GHSA-f886-m6hf-6m8v-brace-expansion.md:1` — canonical remediation record

## Validation

```bash
npx -y -p node@22.22.1 -c 'npm install --package-lock-only'
npx -y -p node@22.22.1 -c 'npm ci'
npx -y -p node@22.22.1 -c 'npm ls brace-expansion minimatch glob @goplus/agentguard'
printf '{"text":"How can I build a steady breakfast habit?","filename":"payload.py"}' | npx -y -p node@22.22.1 node tools/agentguard/scan_text.mjs
pytest -q tests/test_root_npm_dependency_guards.py
pytest -q tests/test_agent_input_guard.py -k goplus
pre-commit run --all-files
make verify
```

## Notes

- This is a runtime transitive dependency on a live security path
  (`tools/agentguard/scan_text.mjs` and the Python bridge around it), not dead
  tooling.
- The first lockfile-only override failed live smoke with
  `(0 , brace_expansion_1.default) is not a function`; this broader dependency
  refresh is the smallest package-manager-only shape that preserves runtime
  behavior.
