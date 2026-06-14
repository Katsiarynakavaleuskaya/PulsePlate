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
  - `scripts/ci/guard_vscode_extensions.py:1`
  - external allowlist paths are forbidden; the reviewed allowlist must stay inside the repo

## Canonical Guards

- `scripts/ci/guard_actions_pin.py`
- `scripts/ci/guard_npm_install_scripts.py`
- `scripts/ci/guard_vscode_extensions.py`

## CI Defaults

- default workflow permissions should stay least-privilege (`contents: read` unless stricter access is justified)
- SBOM generation remains enabled
- pushed-image Docker BuildKit lanes that receive private package-index inputs
  through BuildKit secret envs must emit `provenance: mode=min` and `sbom: true`
- `build.yml` publish must scan the loaded production image before GHCR push,
  then publish the same scanned tags and create GitHub-signed provenance/SBOM
  attestations against the pushed digest
- jobs that create GitHub-signed provenance/SBOM attestations must grant `attestations: write`
- CD and publish jobs must verify provenance and SPDX SBOM attestations by exact
  digest before deploy or release-control-plane digest publication using
  `scripts/ci/check_docker_provenance_attestation.py`
