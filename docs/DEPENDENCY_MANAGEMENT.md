# Dependency Management with pip-tools

This project uses `pip-tools` to manage dependencies with deterministic builds.

## Files

- `requirements.in` - Production dependencies (high-level)
- `requirements-dev.in` - Development dependencies (high-level)
- `requirements.txt` - Compiled production dependencies with exact versions (auto-generated)
- `requirements-dev.txt` - Compiled development dependencies with exact versions (auto-generated)
- `constraints.txt` - Additional version constraints for deterministic CI/CD builds

### About constraints.txt

`constraints.txt` serves as an **additional layer of version control** for CI/CD environments:

- **Purpose**: Enforces specific versions for transitive dependencies that may not be pinned in `requirements.txt`
- **Use Case**: Ensures CI/CD builds use identical package versions even when `pip install` is used instead of `pip-sync`
- **Content**: Manually curated version pins for critical transitive dependencies or security patches
- **Updates**: Review and update when security vulnerabilities are discovered or when a transitive dependency introduces breaking changes
- **Example**: If `pydantic` depends on `typing-extensions`, but the version range is too broad, `constraints.txt` can pin it to a specific tested version

**Note**: When using `pip-sync` (recommended for local development), `constraints.txt` is not needed since `requirements.txt` already contains all pinned versions.

## Installation

### Local Development (Recommended: pip-sync)

`pip-sync` ensures exact matching - it installs packages from requirements files and removes any extras not listed, guaranteeing a clean, reproducible environment.

```bash
# Install pip-tools
pip install pip-tools

# Install production dependencies
pip-sync requirements.txt

# Install development dependencies (includes production deps)
pip-sync requirements-dev.txt
```

### CI/CD or Standard pip Environments

If `pip-tools` is not available or you need standard pip compatibility, use constraints files for deterministic builds:

```bash
# Install pinned dependencies through a local wheelhouse
python scripts/ci/install_locked_python_requirements.py \
  --python-executable python \
  --constraints-file constraints.txt \
  --install-dev
```

This installer now follows a two-step flow:

1. Download pinned artifacts into a temporary wheelhouse.
2. Install with `--no-index --find-links <wheelhouse>` and then run the executable `.pth` guard from `scripts/ci/check_python_startup_hooks.py`.

**Note**: This is hermetic for the install phase, but it is not a substitute for an internal mirror/quarantine service. The repo still needs a promoted artifact source for full supply-chain isolation.

## Canonical Clean-Clone Bootstrap For Local Verify

For this repo, the canonical local path is still the Makefile bootstrap:

```bash
make venv
make verify
```

If an existing `.venv` looks stale or `make verify` fails early on a missing
locked dependency such as `opentelemetry-*`, refresh the environment with:

```bash
make venv-sync
make verify
```

`make verify` includes a fail-fast `verify-env` preflight so incomplete
clean-clone environments fail before the longer lint/typecheck/test gates. Run
`make verify` from repo root and do not rely on an externally activated
interpreter: `verify-env` requires the repo `.venv` interpreter itself. The
verify-critical gates now run in interpreter-module mode via the repo `.venv`
(for example `$(VENV_PYTHON) -m flake8`, `-m mypy`, `-m pytest`, `-m
coverage`, and `-m diff_cover.diff_cover_tool` for `diff-cover`). Stale
`.venv/bin/*` wrapper entrypoints are no longer the trust anchor for local
merge evidence. Local bootstrap also sets `PIP_REQUIRE_VIRTUALENV=1` and uses
`scripts/ci/install_locked_python_requirements.py --require-virtualenv`, so the
repo bootstrap path refuses to install packages through a non-virtualenv
interpreter.

## Updating Dependencies

### Update all dependencies to latest compatible versions

```bash
# Update production dependencies
pip-compile requirements.in --upgrade -o requirements.txt

# Update development dependencies
pip-compile requirements-dev.in --upgrade -o requirements-dev.txt

# Install updated dependencies
pip-sync requirements-dev.txt
```

### Update a specific dependency

```bash
# Update only fastapi
pip-compile requirements.in --upgrade-package fastapi -o requirements.txt
pip-sync requirements.txt
```

### Add a new dependency

```bash
# Add to requirements.in or requirements-dev.in
echo "new-package>=1.0.0" >> requirements.in

# Recompile
pip-compile requirements.in -o requirements.txt
pip-sync requirements.txt
```

## CI/CD Integration

### Option 1: Locked wheelhouse installer (Current Implementation)

GitHub Actions workflows should use the shared installer instead of ad hoc
`pip install` blocks:

```yaml
- name: Install dependencies
  run: |
    python scripts/ci/install_locked_python_requirements.py \
      --python-executable python \
      --constraints-file constraints.txt \
      --install-dev
```

### Option 2: pip-sync (For Exact Matching)

For stricter environment control matching local development:

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip pip-tools
    pip-sync requirements-dev.txt
```

**Trade-offs**:

- **`install_locked_python_requirements.py`**: downloads wheels first, installs hermetically with `--no-index`, and runs the startup-hook guard before tests/bootstrap
- **`pip-sync`**: Exact environment matching with local dev, slower (uninstalls extras), requires pip-tools dependency

## Supply-Chain Hardening Rules

- Do not add floating tool installs to CI or composite actions when the repo already has a pinned lock surface.
- Treat executable `.pth` files as startup hooks and fail closed on unknown filenames.
- When a dependency bump or new package is required, review the wheel/sdist contents before promoting the change to shared CI/bootstrap paths.
- Prefer a promoted internal wheelhouse or mirror for long-term CI/Docker isolation. Repo-local wheelhouse builds are a bridge, not the final control.

## Dependabot Configuration

Dependabot is configured to:

- Run monthly (instead of weekly)
- Create max 5 PRs at a time
- Group related dependencies together (production, testing, quality, security)

See `.github/dependabot.yml` for details.
