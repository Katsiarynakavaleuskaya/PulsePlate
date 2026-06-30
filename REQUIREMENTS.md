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
surface is registered, compiled lockfiles still carry their pip-compile
provenance, local/manual surfaces stay out of shared install routing, and
security/dependency-submission coverage remains documented.

## Regeneration

Use the commands in `docs/DEPENDENCY_MANAGEMENT.md` for lockfile regeneration.
Do not regenerate lockfiles as part of dependency-surface documentation or
validator-only PRs.
