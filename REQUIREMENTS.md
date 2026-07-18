# Requirements Management Guide

This is the quick-start guide. The canonical dependency-surface contract is
`docs/contracts/PYTHON_DEPENDENCY_SURFACES.md`; operational regeneration and
security details live in `docs/DEPENDENCY_MANAGEMENT.md`.

Executable validation lives in `scripts/ci/check_python_dependency_surfaces.py`.
`verify_requirements.py` is a compatibility wrapper for that validator.

## Shared Install Profiles

Use the locked installer for shared runtime and CI installs:

```bash
python scripts/ci/install_locked_python_requirements.py \
  --requirements-profile runtime \
  --requirements-file requirements.txt \
  --constraints-file constraints.txt
```

Supported shared profiles are:

- `runtime`
- `runtime-dev`
- `runtime-test`
- `ci-test`
- `ci-lite`
- `rag-vector`

`requirements-rag-vector.txt` is the optional vector runtime profile. It carries
the opt-in FastEmbed/ONNX RAG vector stack and is installed only when a job or
runtime explicitly selects the `rag-vector` profile.

`requirements-test.txt` keeps pytest/coverage tooling plus `pgvector` for
postgres-vector contract tests. It does not pull the optional FastEmbed/ONNX
vector runtime stack. It also owns `httpx2` as the Starlette TestClient
backend for backend test lanes; runtime, Docker runtime, and CI-lite profiles
must not install `httpx2`.

The dependency ownership audit in
`scripts/ci/check_python_dependency_surfaces.py` is the canonical authority for
the first audited subset: `pyarrow`, `pandas`, `httpx2`, `reportlab`,
`matplotlib`, `numpy`, and `aiosqlite`. `pyarrow` is data/eval-only unless a
future PR documents canonical runtime owner evidence; runtime, Docker runtime,
CI-lite, and `requirements-lock.txt` must not install it. Legacy-only usage is
`legacy_compat_transitional` evidence, not production dependency ownership.
`aiosqlite` is documented as SQLite async fallback/local-dev/test ownership via
`core/db.py`, not as production Postgres authority. Direct `numpy` runtime
authority should be removed only when compiled locks keep `numpy` transitively
through `matplotlib` without unrelated resolver churn.

Local/manual profiles (`requirements-data.txt`, `requirements-evals.txt`, and
`requirements-rag-vector-cpu.txt`) are not shared GitHub Actions
`requirements-profile` values.

## Noncanonical Aggregate Files

`requirements-lock.txt` is a dependency-graph reconciliation aggregate, not a
shared install authority.

`requirements-all.txt` is a legacy flexible local convenience file, not a
compiled lockfile and not a security floor source.

## Verification

```bash
python verify_requirements.py
python scripts/ci/check_python_dependency_surfaces.py
```

The validator checks that every root `requirements*.in` / `requirements*.txt`
surface is registered, compiled lockfiles carry their governed Make/profile
provenance, local/manual surfaces stay out of shared install routing, and
security/dependency-submission coverage remains documented.

## Regeneration

Export the approved private proxy and compile only the profiles owned by the
change:

```bash
export PULSEPLATE_PYTHON_INDEX_URL="https://packages.pulseplate.app/root/pulseplate/+simple/"
LOCK_PROFILES="test dev aggregate" \
  UPGRADE_PACKAGES="coverage==7.15.1 faker==40.31.0" \
  make requirements-locks
```

`LOCK_PROFILES` is required. `UPGRADE_PACKAGES` is optional and accepts only
exact existing `package==version` targets. The compiler seeds existing locks,
downloads the exact desired artifacts through a temporary private-proxy HOME,
destroys that credentialed HOME, statically validates wheel metadata, then
compiles from profile-narrow wheelhouses with indexes disabled. It rejects
unrelated graph movement and rolls back a multi-lock update if any replacement
fails. Runtime must be compiled in a separate first pass before profiles
constrained by `requirements.txt`. `GRAPH_CHANGE_PACKAGES` is intentionally
unavailable until a versioned artifact-admission contract exists. See
`docs/DEPENDENCY_MANAGEMENT.md` for profile procedures. Do not regenerate
lockfiles in documentation-only or validator-only PRs.
