# Dependency Management with pip-tools

This project uses `pip-tools` to manage dependencies with deterministic builds.

## Files

- `requirements.in` - Production dependencies (high-level)
- `requirements-dev.in` - Development dependencies (high-level)
- `requirements-test.in` - Test-only dependencies (high-level)
- `requirements-ci-lite.in` - Lightweight CI/control-plane dependencies (high-level)
- `requirements-docker-runtime.in` - Docker production runtime dependencies (high-level)
- `requirements-rag-vector.in` - Optional vector/ML runtime dependencies (high-level)
- `requirements.txt` - Compiled production dependencies with exact versions (auto-generated)
- `requirements-docker-runtime.txt` - Compiled Docker production runtime dependencies with exact versions (auto-generated)
- `requirements-dev.txt` - Compiled development dependencies with exact versions (auto-generated)
- `requirements-test.txt` - Compiled test-only dependencies with exact versions (auto-generated)
- `requirements-ci-lite.txt` - Compiled lightweight CI/control-plane dependencies (auto-generated)
- `requirements-rag-vector.txt` - Compiled optional vector/ML runtime dependencies (auto-generated)
- `constraints.txt` - Additional version constraints for deterministic CI/CD builds

`requirements-test.txt` keeps `pgvector` only for postgres-vector test coverage; the heavy vector/ML runtime packages remain isolated in `requirements-rag-vector.txt`.
`requirements-docker-runtime.txt` is the backend image contract for production-target Docker builds and excludes CI-only tooling.

## CI Install Profiles

The shared GitHub Actions Python setup action accepts explicit
`requirements-profile` values so CI jobs can install only the surfaces they
need:

- `ci-lite` installs `requirements-ci-lite.txt` for lint, OpenAPI sync,
  diff-coverage, and governance/control-plane jobs.
- `ci-test` installs `requirements-ci-lite.txt` plus `requirements-test.txt`
  for canonical test lanes such as `test-pr`, `test-feature`, and `test-main`.
- `runtime` and `runtime-test` keep app-runtime installs separate from CI
  tooling and are not the default for generic CI feedback.
- `rag-vector` is the explicit optional vector/ML runtime profile and is the
  only canonical profile that carries the heavy ML runtime stack such as
  `sentence-transformers`, `transformers`, and `torch`.

Generic feature/fix feedback must stay on `ci-test` or `ci-lite` unless the job
explicitly proves it needs optional vector/ML runtime behavior. That proof must
be a workflow/risk-profile change backed by deterministic tests, for example
updates to `tests/test_python_supply_chain_controls.py` and
`tests/test_ci_workflow_pr_size_governance_contract.py`, showing why `ci-test`
cannot cover the selected target without the `rag-vector` profile. Postgres
vector test coverage remains in `requirements-test.txt` via `pgvector`; that is
test tooling, not permission to install the optional ML runtime stack in generic
CI lanes.

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
export PULSEPLATE_PYTHON_INDEX_URL="https://packages.example.internal/simple"
# Optional: only when the approved proxy requires an explicit trusted host
export PULSEPLATE_PYTHON_TRUSTED_HOST="packages.example.internal"
python scripts/ci/install_locked_python_requirements.py \
  --python-executable python \
  --constraints-file constraints.txt \
  --install-dev
```

This installer now follows a two-step flow:

1. Download pinned artifacts into a temporary wheelhouse.
2. Install with `--no-index --find-links <wheelhouse>` and then statically scan the target `site-packages` for executable `.pth` hooks via `scripts/ci/check_python_startup_hooks.py` without re-launching the target interpreter.

Canonical contract for shared CI/Docker/bootstrap paths:

- `PULSEPLATE_PYTHON_INDEX_URL` is mandatory and must point to the approved private package proxy.
- `PULSEPLATE_PYTHON_TRUSTED_HOST` is optional and should only be set when the approved proxy requires it.
- GitHub Actions source these values from `secrets` first and fall back to repository `vars`, so an emergency secret override can immediately replace a stale repository-level default without editing every workflow file.
- Public package hosts such as `pypi.org`, `files.pythonhosted.org`, and `test.pypi.org` are rejected by the shared installer.
- Ambient overrides such as `PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` are rejected for canonical installs.
- Time-boxed exceptions must stay exact and manifest-driven. Current example:
  `scripts/ci/emergency_python_wheels.json` currently carries a broader,
  repo-approved fallback set (including `cryptography 46.0.7`, `pillow 12.2.0`,
  and other active bootstrap/runtime wheels) with pinned `sha256` digests until the
  approved proxy catches up.
- Production-target Docker workflows pass `PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt`
  so the backend image stays on the Docker runtime surface instead of `requirements-ci-lite.txt`.

**Note**: The temporary wheelhouse is no longer the final control. The repo now fails closed unless dependency resolution goes through the approved private proxy. Artifact quarantine and promotion review still live outside the repo as infrastructure controls.

## Canonical Clean-Clone Bootstrap For Local Verify

For this repo, the canonical local path is still the Makefile bootstrap:

```bash
export PULSEPLATE_PYTHON_INDEX_URL="https://packages.example.internal/simple"
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

# Update Docker runtime dependencies
pip-compile --allow-unsafe --output-file=requirements-docker-runtime.txt requirements-docker-runtime.in

# Update development dependencies
pip-compile requirements-dev.in --upgrade -o requirements-dev.txt

# Update optional vector/ML runtime dependencies
pip-compile requirements-rag-vector.in --upgrade -o requirements-rag-vector.txt

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
  env:
    PULSEPLATE_PYTHON_INDEX_URL: ${{ secrets.PULSEPLATE_PYTHON_INDEX_URL || vars.PULSEPLATE_PYTHON_INDEX_URL }}
    PULSEPLATE_PYTHON_TRUSTED_HOST: ${{ secrets.PULSEPLATE_PYTHON_TRUSTED_HOST || vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}
  run: |
    python scripts/ci/install_locked_python_requirements.py \
      --python-executable python \
      --constraints-file constraints.txt \
      --install-dev
```

Workflow precedence is `secrets` first and `vars` second for
`PULSEPLATE_PYTHON_INDEX_URL` and `PULSEPLATE_PYTHON_TRUSTED_HOST`. This keeps
the repository variable as a non-authoritative fallback and lets an emergency
secret override immediately replace stale or broken repository-level values.

### Option 2: pip-sync (For Exact Matching)

For stricter environment control matching local development:

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip pip-tools
    pip-sync requirements-dev.txt
```

**Trade-offs**:

- **`install_locked_python_requirements.py`**: downloads wheels first, installs hermetically with `--no-index`, and performs a static startup-hook scan before tests/bootstrap
- **`pip-sync`**: Exact environment matching with local dev, slower (uninstalls extras), requires pip-tools dependency

## Supply-Chain Hardening Rules

- Do not add floating tool installs to CI or composite actions when the repo already has a pinned lock surface.
- Treat executable `.pth` files as startup hooks and fail closed on unknown filenames.
- Route every shared CI/Docker/bootstrap resolution through `PULSEPLATE_PYTHON_INDEX_URL`; do not bypass it with raw public `pip install` commands.
- When a dependency bump or new package is required, review the wheel/sdist contents before promoting the change to shared CI/bootstrap paths.
- Prefer a promoted internal mirror or artifact quarantine lane for long-term CI/Docker isolation. Repo-local wheelhouse builds are a bridge, not the final control.

## Dependabot Configuration

Dependabot is configured to:

- Run monthly (instead of weekly)
- Create max 5 PRs at a time
- Group related dependencies together (production, testing, quality, security)

See `.github/dependabot.yml` for details.
