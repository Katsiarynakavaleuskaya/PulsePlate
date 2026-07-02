# Dependency Management with pip-tools

This project uses `pip-tools` to manage dependencies with deterministic builds.

Canonical dependency-surface ownership lives in
`docs/contracts/PYTHON_DEPENDENCY_SURFACES.md`. The executable contract check is
`scripts/ci/check_python_dependency_surfaces.py`; `verify_requirements.py`
remains as a legacy compatibility wrapper for that validator and is not a
separate ownership authority.

## Files

- `requirements.in` - Production dependencies (high-level)
- `requirements-dev.in` - Development dependencies (high-level)
- `requirements-test.in` - Test-only dependencies (high-level)
- `requirements-ci-lite.in` - Lightweight CI/control-plane dependencies (high-level)
- `requirements-docker-runtime.in` - Docker production runtime dependencies (high-level)
- `requirements-rag-vector.in` - Optional vector runtime dependencies (high-level)
- `requirements-rag-vector-cpu.in` - Optional vector runtime dependencies (local-only, high-level)
- `requirements-data.in` - Offline data-build dependencies (local/manual, high-level)
- `requirements-evals.in` - Offline eval dependencies (local/manual, high-level)
- `requirements.txt` - Compiled production dependencies with exact versions (auto-generated)
- `requirements-docker-runtime.txt` - Compiled Docker production runtime dependencies with exact versions (auto-generated)
- `requirements-dev.txt` - Compiled development dependencies with exact versions (auto-generated)
- `requirements-test.txt` - Compiled test-only dependencies with exact versions (auto-generated)
- `requirements-ci-lite.txt` - Compiled lightweight CI/control-plane dependencies (auto-generated)
- `requirements-rag-vector.txt` - Compiled optional vector runtime dependencies (auto-generated)
- `requirements-rag-vector-cpu.txt` - Compiled optional vector runtime dependencies (auto-generated, local-only)
- `requirements-data.txt` - Compiled offline data-build dependencies with exact versions (auto-generated, local/manual)
- `requirements-evals.txt` - Compiled offline eval dependencies with exact versions (auto-generated, local/manual)
- `constraints.txt` - Additional version constraints for deterministic CI/CD builds

`requirements-test.txt` keeps `pgvector` only for postgres-vector test coverage; the FastEmbed/ONNX runtime packages remain isolated in the optional vector runtime profiles (`requirements-rag-vector.txt` and `requirements-rag-vector-cpu.txt`).
`requirements-test.txt` also owns `httpx2` as the Starlette TestClient backend
for backend test lanes. Runtime, Docker runtime, and CI-lite profiles must not
install `httpx2`.
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
- `rag-vector` is the explicit optional vector runtime profile and is the only
  canonical profile that carries the local FastEmbed/ONNX embedding backend.

`requirements-all.txt` and `requirements-lock.txt` are noncanonical aggregate
install surfaces. `requirements-lock.txt` exists for dependency graph
reconciliation and scanner attribution; `requirements-all.txt` is a legacy
flexible local convenience file. Neither file is a shared CI/Docker/runtime
install authority.

Generic feature/fix feedback must stay on `ci-test` or `ci-lite` unless the job
explicitly proves it needs optional vector runtime behavior. That proof must
be a workflow/risk-profile change backed by deterministic tests, for example
updates to `tests/test_python_supply_chain_controls.py` and
`tests/test_ci_workflow_pr_size_governance_contract.py`, showing why `ci-test`
cannot cover the selected target without the `rag-vector` profile. Postgres
vector test coverage remains in `requirements-test.txt` via `pgvector`; that is
test tooling, not permission to install the optional vector runtime stack in generic
CI lanes.

## Local Manual Eval/Data Profiles

`requirements-data.in` owns offline data-build dependencies for snapshot
builders such as `scripts/build_food_db.py` and `scripts/build_recipe_db.py`.
The compiled `requirements-data.txt` profile includes `pandas` plus explicit
Parquet writer support through `pyarrow`. Runtime, Docker runtime, CI-lite, and
`requirements-lock.txt` must not install or legitimize `pyarrow` unless a future
PR documents canonical app/core/provider runtime owner evidence in
`docs/contracts/PYTHON_DEPENDENCY_SURFACES.md`.

The dependency ownership audit currently enforces only the first audited subset:
`pyarrow`, `pandas`, `httpx2`, `reportlab`, `matplotlib`, `numpy`, and
`aiosqlite`. Legacy usage is evidence of transitional compatibility pressure,
not runtime ownership. `legacy_app.py`, root `bmi_visualization.py`, and legacy
BMI compatibility shims can produce `legacy_compat_transitional` evidence only;
they cannot by themselves make a dependency canonical runtime authority.
`aiosqlite` remains in runtime, Docker runtime, and CI-lite surfaces because
`core/db.py` derives `sqlite+aiosqlite` URLs for SQLite async fallback/local-dev
and test support. That documented owner does not make SQLite or `aiosqlite` a
production database authority; production/staging Postgres policy is unchanged.
`numpy` direct runtime authority remains warning-only unless a PR can remove the
direct input line while keeping `numpy` as a deterministic transitive pin
through `matplotlib` without unrelated lock churn.

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
- **Use Case**: Ensures CI/CD builds use identical package versions when standard pip-compatible installs need an explicit constraints layer
- **Content**: Manually curated version pins for critical transitive dependencies or security patches
- **Updates**: Review and update when security vulnerabilities are discovered or when a transitive dependency introduces breaking changes
- **Example**: If `pydantic` depends on `typing-extensions`, but the version range is too broad, `constraints.txt` can pin it to a specific tested version

**Note**: The canonical local refresh path is `make venv-sync`, which uses the
locked installer path. `constraints.txt` is still for shared pip-compatible
install contexts; it is not a substitute for the compiled lock surfaces.

## Installation

### Local Development (Recommended: make venv-sync)

`make venv-sync` refreshes the repo `.venv` through the locked installer path
and the approved private package proxy. Use it after lockfile changes or when a
local environment has stale wrappers or missing pins.

```bash
export PULSEPLATE_PYTHON_INDEX_URL="https://packages.pulseplate.app/root/pulseplate/+simple/"
make venv-sync
```

Direct `pip-sync` remains a manual/debugging tool only; do not present it as the
canonical local refresh path in repo workflows.

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

`rag-vector-cpu` is a **local/developer-only** sibling profile for the same
FastEmbed/ONNX runtime. It is derived from `requirements-rag-vector-cpu.txt` and
is intentionally excluded from canonical CI lanes and the shared
`requirements-profile` action values. It does not add a secondary package index.

If you need vector runtime tooling on a local machine, use the local CPU lockfile:

```bash
.venv/bin/python scripts/ci/install_locked_python_requirements.py \
  --requirements-file requirements-rag-vector-cpu.txt \
  --require-virtualenv
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
this registry must also be covered by the shared pip-audit helper. The
supply-chain guard in
`tests/test_python_supply_chain_controls.py` fails if the local/manual eval/data
profiles drift from those security surfaces. This registry does not make
`requirements-data.txt` or `requirements-evals.txt` shared install profiles;
they remain local/manual offline profiles and stay out of runtime, Docker, and
generic CI installs.

Canonical contract for shared CI/Docker/bootstrap paths:

- `PULSEPLATE_PYTHON_INDEX_URL` is mandatory and must point to the approved private package proxy simple-index root. For devpi this is the credential-free URL `https://packages.pulseplate.app/root/pulseplate/+simple/`.
- GitHub Actions authenticated installs must keep the index URL credential-free and use rotated non-root CI read credentials through `.netrc`. The composite `python-setup` action creates that temporary `.netrc` only when both `DEVPI_CI_USER` and `DEVPI_CI_PASSWORD` secrets are present, then removes it with an `always()` cleanup step.
- The early proxy health gate uses repository `vars` only for pull-request and
  non-main branch diagnostics. On `main` pushes, it may create a temporary
  `.netrc` from non-root `DEVPI_CI_USER` / `DEVPI_CI_PASSWORD` secrets before
  probing project pages, so the gate exercises the same authenticated read
  boundary without embedding credentials in the URL.
- Root credentials are forbidden for CI. The devpi root password is an operator break-glass/admin credential only and must be rotated out of band if exposed.
- Repository variables must stay credential-free. They may hold only non-secret diagnostic package-proxy values; never store Basic Auth URLs, upload credentials, or root credentials in repository `vars`.
- `PULSEPLATE_PYTHON_TRUSTED_HOST` is optional and should only be set when the approved proxy requires it. Keep it unset for the `packages.pulseplate.app` devpi host while normal TLS verification succeeds.
- Public package hosts such as `pypi.org`, `files.pythonhosted.org`, and `test.pypi.org` are rejected by the shared installer.
- Ambient overrides such as `PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` are rejected for canonical installs.
- Time-boxed exceptions must stay exact and manifest-driven. The emergency
  wheel path is currently retired: `scripts/ci/emergency_python_wheels.json`
  remains as an empty compatibility marker so rollback code paths and CI/Docker
  references do not churn in the same PR. Reintroducing entries requires
  security sign-off, exact package/version/filename metadata, pinned `sha256`,
  expiry, package-scoped mirror evidence, and a removal plan.
- The installer may use an exact manifest wheel after pip reports both an exact
  resolver miss and either a package-scoped retry/timeout against that approved
  simple project path or a package-scoped approved-proxy health-probe timeout.
  Plain resolver misses without package-scoped proxy evidence remain
  proxy-health gated; generic proxy outages remain fail-closed.
- Production-target Docker workflows pass `PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt`
  so the backend image stays on the Docker runtime surface instead of `requirements-ci-lite.txt`.

**Note**: The temporary wheelhouse is no longer the final control. The repo now fails closed unless dependency resolution goes through the approved private proxy. Artifact quarantine and promotion review still live outside the repo as infrastructure controls.

### Private proxy health and mirror parity gate

`scripts/ci/check_private_python_proxy_health.py` is the cheap, stdlib-only
health gate for the approved private proxy. It runs before dependency-heavy CI
jobs that call `.github/actions/python-setup`, because that composite action
itself depends on the proxy being healthy.

The gate checks the same contract that pip consumes:

- `PULSEPLATE_PYTHON_INDEX_URL` must be a credential-free HTTPS simple-index
  root for `packages.pulseplate.app`.
- Public PyPI/TestPyPI/pythonhosted hosts and inline Basic Auth URLs are
  rejected.
- The probe uses canonical project pages such as
  `https://packages.pulseplate.app/root/pulseplate/+simple/aiosqlite/`, not the
  host root, marketing apex, or a second appended `/simple`.
- Representative project pages must be non-empty Simple API pages and include
  exact locked artifacts from the configured requirements files. The CI gate
  includes `requirements.txt`, `requirements-ci-lite.txt`, and
  `requirements-test.txt` because `ci-test` jobs install both CI-lite and
  test-only pinned surfaces.
- `origin_unhealthy` / timeout / HTTP 521/522 means operator recovery for
  Cloudflare/DigitalOcean/devpi, not a repo lockfile or Starlette/httpx fix.
- `mirror_lag_exact_pin_missing` means the origin is reachable but the mirror is
  missing an exact locked artifact; emergency wheels remain a time-boxed bridge
  only for listed exact pins.
- `auth_or_access_denied` means the project page requires credentials or the
  CI `.netrc` principal lacks read access; rotate/fix non-root devpi CI
  credentials instead of embedding credentials in the URL.
- `project_page_not_found` means the package is not present at the canonical
  devpi project page; verify the normalized project name and mirror sync.
- `redirect_not_allowed` means the proxy path drifted or is redirecting away
  from the approved simple root; fix DNS/devpi routing rather than following
  the redirect.
- `http_error` covers non-2xx HTTP responses outside the explicit origin/auth
  classes; inspect edge/origin logs for the packages hostname.
- `empty_project_page` / `simple_page_malformed` means the project page is
  reachable but not a usable Simple API project page; inspect devpi project-page
  generation and mirror state.
- `simple_page_truncated` means the page exceeded the bounded read before the
  exact pin was observed; choose a smaller representative package for the fast
  gate or investigate oversized mirror pages.

`scripts/ci/check_emergency_wheel_mirror_parity.py` is the companion all-entry
manifest parity gate. It is narrower than dependency installation and broader
than the representative health probe: for each active emergency manifest
artifact, it validates the metadata and then checks the approved private
project page for that exact wheel filename across the configured Python target
tags. It fails closed for missing filenames, incompatible wheels, invalid
hashes, wrong artifact hosts, unhealthy project pages, or active expired
entries. When the manifest is the retired empty marker, it succeeds with
`retired=true` and does not fetch project pages.
- `missing_exact_pin_in_requirements` means the probe list and requirements
  files disagree; update the checker inputs instead of treating it as an origin
  outage.

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
pip-compile --allow-unsafe --no-emit-index-url --output-file=requirements-docker-runtime.txt requirements-docker-runtime.in

# Update development dependencies
pip-compile --allow-unsafe --no-emit-index-url requirements-dev.in --upgrade -o requirements-dev.txt
pip-compile --allow-unsafe --no-emit-index-url --output-file=requirements-test.txt requirements-test.in
pip-compile --allow-unsafe --no-emit-index-url --output-file=requirements-ci-lite.txt requirements-ci-lite.in

# Update optional vector runtime dependencies
pip-compile --allow-unsafe --no-emit-index-url requirements-rag-vector.in --upgrade -o requirements-rag-vector.txt
pip-compile --allow-unsafe --no-emit-index-url requirements-rag-vector-cpu.in --upgrade -o requirements-rag-vector-cpu.txt

# Recompile local/manual data and eval profiles
pip-compile --allow-unsafe --no-emit-index-url --output-file=requirements-data.txt requirements-data.in
pip-compile --allow-unsafe --no-emit-index-url --output-file=requirements-evals.txt requirements-evals.in

# Refresh local dependencies through the locked installer path
make venv-sync
```

### Update a specific dependency

```bash
# Update only fastapi
pip-compile requirements.in --upgrade-package fastapi -o requirements.txt
make venv-sync
```

### Add a new dependency

```bash
# Add to requirements.in or requirements-dev.in
echo "new-package>=1.0.0" >> requirements.in

# Recompile
pip-compile requirements.in -o requirements.txt
make venv-sync
```

## CI/CD Integration

### Option 1: Locked wheelhouse installer (Current Implementation)

GitHub Actions workflows should use the shared installer instead of ad hoc
`pip install` blocks:

```yaml
- name: Install dependencies
  env:
    PULSEPLATE_PYTHON_INDEX_URL: ${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}
    PULSEPLATE_PYTHON_TRUSTED_HOST: ${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}
  run: |
    python scripts/ci/install_locked_python_requirements.py \
      --python-executable python \
      --constraints-file constraints.txt \
      --install-dev
```

Workflow-level and pull-request diagnostic package-index values must come from
repository `vars` only because those jobs can execute untrusted pull-request
code. Protected push/main contexts may resolve `PULSEPLATE_PYTHON_INDEX_URL` and
`PULSEPLATE_PYTHON_TRUSTED_HOST` from `secrets` first and `vars` second inside a
guarded protected-only resolver step, but `PULSEPLATE_PYTHON_INDEX_URL` itself
must remain credential-free. Authenticated devpi reads use `DEVPI_CI_USER` and
`DEVPI_CI_PASSWORD` secrets via a temporary `.netrc`. Repository variables are
allowed only for non-secret values.

### Option 2: pip-sync (Manual Debugging Only)

For manual debugging outside the canonical shared installer path:

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip pip-tools
    pip-sync requirements-dev.txt
```

**Trade-offs**:

- **`install_locked_python_requirements.py`**: downloads wheels first, installs hermetically with `--no-index`, and performs a static startup-hook scan before tests/bootstrap
- **`pip-sync`**: Manual/debug exact matching, slower (uninstalls extras), requires pip-tools dependency

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
