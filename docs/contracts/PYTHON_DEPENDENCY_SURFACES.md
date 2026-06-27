# Python Dependency Surfaces

**Status:** Canonical dependency-surface contract for Python requirements.

## Source Of Truth

Executable policy lives in `scripts/ci/check_python_dependency_surfaces.py`.
This document is the human mirror for owners, install authority, and security
coverage. `docs/DEPENDENCY_MANAGEMENT.md` remains the operational runbook, and
`REQUIREMENTS.md` is a quick-start guide that must defer to this contract.

Run the contract check with:

```bash
python verify_requirements.py
python scripts/ci/check_python_dependency_surfaces.py
```

## Canonical Surfaces

| Surface | Source | Lock | Owner | Install Authority | Security Coverage |
|---|---|---|---|---|---|
| runtime | `requirements.in` | `requirements.txt` | Backend runtime | `runtime`, `runtime-dev`, `runtime-test`, and `rag-vector` profiles | `scripts/ci_pip_audit.sh`, pre-push pip-audit, dependency submission |
| docker-runtime | `requirements-docker-runtime.in` | `requirements-docker-runtime.txt` | Docker production image | Dockerfile and production image workflows | `scripts/ci_pip_audit.sh`, dependency submission |
| ci-lite | `requirements-ci-lite.in` | `requirements-ci-lite.txt` | CI control-plane | `ci-lite` and `ci-test` profiles | dependency submission, CI install preflight |
| test | `requirements-test.in` | `requirements-test.txt` | Backend test lanes | `runtime-test` and `ci-test` profiles | dependency submission, CI install preflight |
| dev | `requirements-dev.in` | `requirements-dev.txt` | Local development tooling | `runtime-dev` profile | dependency submission, CI install preflight |
| rag-vector | `requirements-rag-vector.in` | `requirements-rag-vector.txt` | Optional vector runtime | `rag-vector` profile | `scripts/ci_pip_audit.sh`, dependency submission |
| rag-vector-cpu | `requirements-rag-vector-cpu.in` | `requirements-rag-vector-cpu.txt` | Local optional vector runtime | Manual local pip-sync only | `scripts/ci_pip_audit.sh`, dependency submission |
| data | `requirements-data.in` | `requirements-data.txt` | Offline data builders | Manual local pip-sync only | `scripts/ci_pip_audit.sh`, dependency submission |
| evals | `requirements-evals.in` | `requirements-evals.txt` | Offline eval companion | Manual local pip-sync only | `scripts/ci_pip_audit.sh`, dependency submission |

## Noncanonical Aggregate Install Surfaces

`requirements-lock.txt` is a compiled aggregate used for dependency graph
reconciliation and scanner attribution. It is not a shared install profile and
must not replace the runtime, dev, test, CI, Docker, vector, data, or eval
lockfiles.

`requirements-all.txt` is a legacy flexible local convenience file. It is not a
compiled lockfile, not a CI/Docker/runtime authority, and not a security floor
source.

## Shared Install Profiles

Shared GitHub Actions install profiles are limited to:

- `runtime`
- `runtime-dev`
- `runtime-test`
- `ci-test`
- `ci-lite`
- `rag-vector`

`requirements-data.txt`, `requirements-evals.txt`, and
`requirements-rag-vector-cpu.txt` must remain out of shared profile routing.
They are local/manual surfaces only, even though they are audited and submitted
for dependency graph visibility.

## Validation Rules

The validator fails when:

- a root `requirements*.in` or `requirements*.txt` file is missing from the
  executable registry;
- a compiled lockfile lacks its pip-compile header, output-file evidence, or
  expected source file reference;
- a compiled lockfile contains a non-exact requirement entry;
- local/manual surfaces leak into shared `requirements-profile` routing;
- required pip-audit or dependency-submission coverage is missing; or
- this contract stops naming a registered surface.

PRs that change Python dependency ownership, install routing, or security
coverage must update both this document and
`scripts/ci/check_python_dependency_surfaces.py`.
