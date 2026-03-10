# Tooling Surface Policy

## Purpose

Keep developer tooling, CI actions, and workspace recommendations pinned and reviewable.

## Hard Rules

- GitHub Actions workflow steps must pin external actions to full commit SHAs.
  Evidence anchors:
  - `.github/workflows/pr-tests.yml:23`
  - `.github/workflows/codeql.yml:62`
- Tracked `package.json` manifests must not define `preinstall`, `install`, or `postinstall`.
  Evidence anchors:
  - `frontend/package.json:6`
  - `scripts/ci/guard_npm_install_scripts.py:1`
- VS Code recommendations must stay inside the reviewed allowlist.
  Evidence anchors:
  - `.vscode/extensions.json:1`
  - `docs/security/vscode_extensions_allowlist.txt:1`

## Canonical Guards

- `scripts/ci/guard_actions_pin.py`
- `scripts/ci/guard_npm_install_scripts.py`
- `scripts/ci/guard_vscode_extensions.py`

## CI Defaults

- default workflow permissions should stay least-privilege (`contents: read` unless stricter access is justified)
- SBOM generation remains enabled
- provenance/cosign verification is deferred until the documented build workaround is removed
