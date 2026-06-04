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

## Status Update

This historical remediation path was later superseded by removing the external
`@goplus/agentguard` runtime dependency from the root npm graph. The current
runtime scanner remains local at `tools/agentguard/scan_text.mjs`, so the old
`@goplus/agentguard -> glob -> minimatch -> brace-expansion` chain is no
longer part of the live root runtime graph.

## Root Cause

At the time of alert `#73`, the root npm graph brought in `brace-expansion`
transitively through the external AgentGuard runtime path:

- `package.json:29` — root direct dependency on `@goplus/agentguard`
- `package-lock.json` — `@goplus/agentguard` depends on `glob`
- `package-lock.json` — `glob` depends on `minimatch`
- `package-lock.json` — resolved vulnerable `brace-expansion` node was `2.0.2`

That historical runtime path no longer exists in the current remediation lane,
because the external `@goplus/agentguard` dependency was removed from the root
graph and replaced by a local deterministic Node scanner.

## Remediation Implemented

- Historical remediation for alert `#73` used npm dependency updates and
  overrides to hold the `glob -> minimatch -> brace-expansion` chain at a safe
  floor.
- The current security lane supersedes that package-manager-only approach by
  removing the external `@goplus/agentguard` runtime path entirely.
- The live runtime scanner now stays local at `tools/agentguard/scan_text.mjs`,
  while the root lockfile no longer carries the old `brace-expansion` path.
- Deterministic root guards now enforce graph removal rather than the older
  override-based runtime shape.

## Evidence Anchors

- `docs/security/GHSA-f886-m6hf-6m8v-brace-expansion.md:15` — status update tying the old alert to the newer graph-removal remediation
- `tools/agentguard/scan_text.mjs:158` — live runtime scanner stays local and no longer loads the external AgentGuard npm runtime
- `tests/test_root_npm_dependency_guards.py:59` — root manifest guard enforces that `@goplus/agentguard` stays out of the runtime dependency graph
- `tests/test_root_npm_dependency_guards.py:89` — carrier-scoped lockfile guard enforces that the removed `@goplus/agentguard/.../brace-expansion` runtime path stays absent

## Validation

```bash
npx -y -p node@24.16.0 -c 'npm install --package-lock-only'
npx -y -p node@24.16.0 -c 'npm ci'
npx -y -p node@24.16.0 -c 'npm ls brace-expansion minimatch glob @goplus/agentguard'
npx -y -p node@24.16.0 -c 'npm audit --package-lock-only --omit=dev'
printf '{"text":"How can I build a steady breakfast habit?","filename":"payload.py"}' | npx -y -p node@24.16.0 node tools/agentguard/scan_text.mjs
pytest -q tests/test_root_npm_dependency_guards.py
pytest -q tests/test_agent_input_guard.py -k goplus
pre-commit run --all-files
make verify
```

## Notes

- This is a runtime transitive dependency on a live security path
  (`tools/agentguard/scan_text.mjs` and the Python bridge around it), not dead
  tooling.
- The older package-manager-only fix path is preserved here as historical
  context, but the current runtime protection comes from removing the external
  dependency chain altogether.
