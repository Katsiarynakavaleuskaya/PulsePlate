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
# Install production dependencies with version constraints
pip install -r requirements.txt -c constraints.txt

# Install development dependencies with version constraints
pip install -r requirements-dev.txt -c constraints.txt
```

**Note**: `pip install` adds packages but doesn't remove extras, which may lead to environment drift over time. For fully reproducible environments, prefer `pip-sync`.

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

`make verify` includes a non-mutating `verify-env` preflight so incomplete
clean-clone environments fail fast before the longer lint/typecheck/test gates.

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

### Option 1: Standard pip (Current Implementation)

GitHub Actions workflows use standard `pip install` for broad compatibility:

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt -c constraints.txt
    pip install -r requirements-dev.txt -c constraints.txt
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

- **`pip install -r ... -c constraints.txt`**: Faster (no uninstall), compatible with any pip version, but may accumulate packages over time
- **`pip-sync`**: Exact environment matching with local dev, slower (uninstalls extras), requires pip-tools dependency

## Dependabot Configuration

Dependabot is configured to:

- Run monthly (instead of weekly)
- Create max 5 PRs at a time
- Group related dependencies together (production, testing, quality, security)

See `.github/dependabot.yml` for details.
