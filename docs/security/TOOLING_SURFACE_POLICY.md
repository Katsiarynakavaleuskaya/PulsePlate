# Tooling Surface Policy

## Purpose

Keep developer tooling, CI actions, and workspace recommendations pinned and reviewable.

## Hard Rules

- Recognized GitHub action references must use family-specific immutable pins
  on these bounded surfaces:
  - active `.github/workflows/**/*.yml` and `.github/workflows/**/*.yaml` files
  - exact `.github/actions/**/action.yml` and `.github/actions/**/action.yaml`
    composite metadata filenames
  - current workflow evidence: `.github/workflows/codeql.yml:72`
  - current composite evidence: `.github/actions/python-setup/action.yml:52`
- The guard deliberately retains a literal-line `uses:` recognizer. It handles
  the established unquoted single-line form with an optional list marker and
  trailing comment; it is not a general YAML, container, symlink, plugin, or
  generated-runtime parser. Arbitrary YAML filenames under `.github/actions/`
  are outside this bounded scan, and the guard makes no completeness claim for
  other executable carriers or YAML-semantic forms.
- Native container action metadata using `runs: using: docker` with a
  `runs.image: docker://...` field is a distinct, context-dependent carrier.
  The current literal `uses:` guard does not parse or cover it; a separately
  admitted closed recognizer is tracked at
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-native-docker-action-image-pin-guard`.
- Recognized references are classified exactly once in this order:
  - local `./` references are repo-local and do not require an external pin
  - `docker://` references must end in an exact lowercase
    `sha256:<64-lowercase-hex>` digest; a tag may precede the digest, but a tag
    alone is mutable and forbidden
  - other external references must satisfy the exact lowercase 40-hex commit
    SHA predicate
- Docker acceptance proves only that the recognized lexical token has the
  required digest selector shape. It does not validate the complete Docker/OCI
  reference grammar, fetch or verify the image, or establish trust, signature,
  provenance, SBOM, vulnerability, or platform-compatibility claims.
- Executable evidence for this classifier and its Docker boundary lives at
  `scripts/ci/guard_actions_pin.py:11` and
  `tests/test_tooling_surface_guards.py:181`; the native `runs.image`
  negative-control boundary is explicit at
  `tests/test_tooling_surface_guards.py:269`.
- On `pull_request`, `jobs.pr_scope_guard` executes the bounded guard against
  the live checkout as the first validation command after `set -euo pipefail`
  and before `scripts/ci/pr_scope_guard.sh` in the step immediately after
  Checkout. Evidence: `.github/workflows/ci.yml:113`
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
