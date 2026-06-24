# Dependency Management with pip-tools

This project uses `pip-tools` to manage dependencies with deterministic builds.

## Files

- `requirements.in` - Production dependencies (high-level)
- `requirements-dev.in` - Development dependencies (high-level)
- `requirements-test.in` - Test-only dependencies (high-level)
- `requirements-ci-lite.in` - Lightweight CI/control-plane dependencies (high-level)
- `requirements-docker-runtime.in` - Docker production runtime dependencies (high-level)
- `requirements-rag-vector.in` - Optional vector/ML runtime dependencies (high-level)
- `requirements-rag-vector-cpu.in` - Optional vector/ML runtime dependencies without CUDA (local-only, high-level)
- `requirements-data.in` - Offline data-build dependencies (local/manual, high-level)
- `requirements-evals.in` - Offline eval dependencies (local/manual, high-level)
- `requirements.txt` - Compiled production dependencies with exact versions (auto-generated)
- `requirements-docker-runtime.txt` - Compiled Docker production runtime dependencies with exact versions (auto-generated)
- `requirements-dev.txt` - Compiled development dependencies with exact versions (auto-generated)
- `requirements-test.txt` - Compiled test-only dependencies with exact versions (auto-generated)
- `requirements-ci-lite.txt` - Compiled lightweight CI/control-plane dependencies (auto-generated)
- `requirements-rag-vector.txt` - Compiled optional vector/ML runtime dependencies (auto-generated)
- `requirements-rag-vector-cpu.txt` - Compiled optional vector/ML runtime dependencies without CUDA (auto-generated, local-only)
- `requirements-data.txt` - Compiled offline data-build dependencies with exact versions (auto-generated, local/manual)
- `requirements-evals.txt` - Compiled offline eval dependencies with exact versions (auto-generated, local/manual)
- `constraints.txt` - Additional version constraints for deterministic CI/CD builds

`requirements-test.txt` keeps `pgvector` only for postgres-vector test coverage; the heavy vector/ML runtime packages remain isolated in `requirements-rag-vector.txt`.
`requirements-docker-runtime.txt` is the backend image contract for production-target Docker builds and excludes CI-only tooling.
`requirements-data.txt` and `requirements-evals.txt` are local/manual offline
profiles only. They are not shared GitHub Actions `requirements-profile` values
and must not be installed by runtime, Docker, or generic CI lanes.

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

## Local Manual Eval/Data Profiles

`requirements-data.in` owns offline data-build dependencies for snapshot
builders such as `scripts/build_food_db.py` and `scripts/build_recipe_db.py`.
The compiled `requirements-data.txt` profile includes `pandas` plus explicit
Parquet writer support through `pyarrow`, without changing the existing
runtime, Docker, or CI-lite dependency ownership for `pyarrow`.

`requirements-evals.in` owns the tracked offline eval dependency surface for
the local RAGAS companion runner. RAGAS native execution is disabled while
`GHSA-95ww-475f-pr4f` (RAGAS) and `GHSA-w8v5-vhqr-4h9v` (DiskCache) have no
patched dependency path. The compiled `requirements-evals.txt` profile is
therefore intentionally empty of `ragas`, `datasets`, and `diskcache` pins while
the runner remains importable, report-only, and fail-closed when native RAGAS
dependencies are unavailable.

Regenerate these local/manual profiles through the approved local package-proxy
environment:

```bash
.venv/bin/python -m piptools compile --allow-unsafe --no-emit-index-url --output-file=requirements-data.txt requirements-data.in
.venv/bin/python -m piptools compile --allow-unsafe --no-emit-index-url --output-file=requirements-evals.txt requirements-evals.in
```

These profiles are offline support surfaces. They do not change OpenAPI,
provider behavior, RAG runtime behavior, semantic-cache policy, FoodDB runtime
cutover, or legacy route ownership.

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
export PULSEPLATE_PYTHON_INDEX_URL="https://packages.pulseplate.app/root/pulseplate/+simple/"
# Optional: only when the approved proxy requires an explicit trusted host.
# Keep unset when TLS verification succeeds.
export PULSEPLATE_PYTHON_TRUSTED_HOST=""
python scripts/ci/install_locked_python_requirements.py \
  --python-executable python \
  --constraints-file constraints.txt \
  --install-dev
```

This installer now follows a two-step flow:

1. Download pinned artifacts into a temporary wheelhouse.
2. Install with `--no-index --find-links <wheelhouse>` and then statically scan the target `site-packages` for executable `.pth` hooks via `scripts/ci/check_python_startup_hooks.py` without re-launching the target interpreter.

### Local CPU profile (без CUDA, для разработчиков)

`rag-vector-cpu` is a **local/developer-only** profile for the same ML stack
without CUDA bindings.  It is derived from `requirements-rag-vector-cpu.txt` and
is intentionally excluded from canonical CI lanes and the shared
`requirements-profile` action values.

The `.in` file adds `--extra-index-url https://download.pytorch.org/whl/cpu` so
that `pip-compile` can prefer CPU-only PyTorch wheels.  Note that
`--extra-index-url` adds a secondary index rather than replacing the default one,
so the compiled `.txt` lockfile is the actual deterministic contract.  Without the
extra index, `torch==2.11.0` from the default PyPI index may resolve to
CUDA-enabled builds on Linux.

If you need vector/ML runtime tooling on a machine without CUDA support, use the local CPU lockfile:

```bash
pip-sync requirements-rag-vector-cpu.txt
```

### Security coverage registry for optional/manual dependency profiles

Optional/manual dependency profiles are supply-chain surfaces even when they are
local-only or excluded from default runtime installs. The current security
coverage registry is:

- `requirements-data.in`
- `requirements-data.txt`
- `requirements-evals.in`
- `requirements-evals.txt`
- `requirements-rag-vector.in`
- `requirements-rag-vector.txt`
- `requirements-rag-vector-cpu.in`
- `requirements-rag-vector-cpu.txt`

Every file in this registry must be covered consistently by Python dependency
submission path filters and CI risk-profile routing. Every compiled lockfile in
this registry must also be covered by the shared Safety audit helper and the
pip-audit helper. The supply-chain guard in
`tests/test_python_supply_chain_controls.py` fails if the local/manual eval/data
profiles drift from those security surfaces. This registry does not make
`requirements-data.txt` or `requirements-evals.txt` shared install profiles;
they remain local/manual offline profiles and stay out of runtime, Docker, and
generic CI installs.

Canonical contract for shared CI/Docker/bootstrap paths:

- `PULSEPLATE_PYTHON_INDEX_URL` is mandatory and must point to the approved private package proxy simple-index root. For devpi this is the credential-free URL `https://packages.pulseplate.app/root/pulseplate/+simple/`.
- GitHub Actions authenticated installs must keep the index URL credential-free and use rotated non-root CI read credentials through `.netrc`. The composite `python-setup` action creates that temporary `.netrc` only when both `DEVPI_CI_USER` and `DEVPI_CI_PASSWORD` secrets are present, then removes it with an `always()` cleanup step.
- Root credentials are forbidden for CI. The devpi root password is an operator break-glass/admin credential only and must be rotated out of band if exposed.
- Repository variables must stay credential-free. They may hold only non-secret diagnostic package-proxy values; never store Basic Auth URLs, upload credentials, or root credentials in repository `vars`.
- `PULSEPLATE_PYTHON_TRUSTED_HOST` is optional and should only be set when the approved proxy requires it. Keep it unset for the `packages.pulseplate.app` devpi host while normal TLS verification succeeds.
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
export PULSEPLATE_PYTHON_INDEX_URL="https://packages.pulseplate.app/root/pulseplate/+simple/"
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
verify-critical gates now run in interpreter-module mode via `DEV_PYTHON`
(for example `$(DEV_PYTHON) -m flake8`, `-m mypy`, `-m pytest`, `-m
coverage`, and `-m diff_cover.diff_cover_tool` for `diff-cover`), which
resolves to `.venv/bin/python` when present or `python3` in containers. Stale
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
pip-compile requirements-rag-vector-cpu.in --upgrade -o requirements-rag-vector-cpu.txt

# Recompile local/manual data and eval profiles
pip-compile --allow-unsafe --no-emit-index-url --output-file=requirements-data.txt requirements-data.in
pip-compile --allow-unsafe --no-emit-index-url --output-file=requirements-evals.txt requirements-evals.in

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
`PULSEPLATE_PYTHON_INDEX_URL` and `PULSEPLATE_PYTHON_TRUSTED_HOST` only for
protected contexts, but `PULSEPLATE_PYTHON_INDEX_URL` itself must remain
credential-free. Authenticated devpi reads use `DEVPI_CI_USER` and
`DEVPI_CI_PASSWORD` secrets via a temporary `.netrc`. Repository variables are
allowed only for credential-free diagnostic values used by untrusted
pull-request diagnostics.

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

- Run weekly
- Create max 10 PRs at a time
- Group related dependencies together (production, testing, quality, security)

See `.github/dependabot.yml` for details.

Security-alert remediation must use a human-owned branch when raw Dependabot
branches include unrelated lock drift or when GitHub's dependency graph
attributes an alert to a profile that current repo manifests do not reproduce.
For example, `GHSA-6v7p-g79w-8964` for `msgpack` is remediated through the
dev/full-lock surfaces that carry the actual `msgpack` pin while the
`requirements-ci-lite.txt` alert is rechecked as scanner attribution unless a
repo-owned `ci-lite` dependency path is proven.
