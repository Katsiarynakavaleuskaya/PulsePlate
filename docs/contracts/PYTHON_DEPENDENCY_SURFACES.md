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

| Surface | Compile profile | Source | Lock | Owner | Install Authority | Security Coverage |
|---|---|---|---|---|---|---|
| runtime | `runtime` | `requirements.in` | `requirements.txt` | Backend runtime | `runtime`, `runtime-dev`, `runtime-test`, and `rag-vector` profiles | `scripts/ci_pip_audit.sh`, pre-push pip-audit, dependency submission |
| docker-runtime | `docker-runtime` | `requirements-docker-runtime.in` | `requirements-docker-runtime.txt` | Docker production image | Dockerfile and production image workflows | `scripts/ci_pip_audit.sh`, dependency submission |
| ci-lite | `ci-lite` | `requirements-ci-lite.in` | `requirements-ci-lite.txt` | CI control-plane | `ci-lite` and `ci-test` profiles | dependency submission, CI install preflight |
| test | `test` | `requirements-test.in` | `requirements-test.txt` | Backend test lanes | `runtime-test` and `ci-test` profiles | dependency submission, CI install preflight |
| dev | `dev` | `requirements-dev.in` | `requirements-dev.txt` | Local development tooling | `runtime-dev` profile | dependency submission, CI install preflight |
| rag-vector | `rag-vector` | `requirements-rag-vector.in` | `requirements-rag-vector.txt` | Optional vector runtime | `rag-vector` profile | `scripts/ci_pip_audit.sh`, dependency submission |
| rag-vector-cpu | `rag-vector-cpu` | `requirements-rag-vector-cpu.in` | `requirements-rag-vector-cpu.txt` | Local optional vector runtime | Manual local locked-installer sync only | `scripts/ci_pip_audit.sh`, dependency submission |
| data | `data` | `requirements-data.in` | `requirements-data.txt` | Offline data builders | Manual local locked-installer sync only | `scripts/ci_pip_audit.sh`, dependency submission |
| evals | `evals` | `requirements-evals.in` | `requirements-evals.txt` | Offline eval companion | Manual local locked-installer sync only | `scripts/ci_pip_audit.sh`, dependency submission |

## Noncanonical Aggregate Install Surfaces

`requirements-lock.txt` is a compiled aggregate used for dependency graph
reconciliation and scanner attribution. It is not a shared install profile and
must not replace the runtime, dev, test, CI, Docker, vector, data, or eval
lockfiles. Its governed compile profile is `aggregate`.

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

`httpx2` is the Starlette TestClient backend dependency. It belongs to the dev,
test, and dev-full-lock surfaces only; it must stay out of runtime, Docker
runtime, and CI-lite surfaces.

## Dependency Ownership Audit

`scripts/ci/check_python_dependency_surfaces.py` runs the first-pass dependency
ownership audit by default. The first enforced subset is intentionally narrow:
`pyarrow`, `pandas`, `httpx2`, `reportlab`, `matplotlib`, `numpy`, and
`aiosqlite`.

Findings use stable severity tiers:

| Severity | Meaning | Default behavior |
|---|---|---|
| `error` | Confirmed policy violation | Fails the validator |
| `warning` | Suspicious but not safe to remove in this PR | Report only |
| `info` | Documented owner or transitional debt | Report only |

Stable reason codes include `runtime_direct_no_canonical_owner`,
`legacy_only_runtime_authority_forbidden`,
`data_eval_dependency_in_runtime`, `test_dev_dependency_in_runtime`,
`canonical_runtime_owner_documented`, `legacy_compat_transitional`, and
`transitive_only_direct_runtime_candidate`,
`sqlite_async_fallback_owner_documented`, and
`db_fallback_test_split_pending`.

Import evidence uses exact top-level import names plus explicit aliases for
known distribution/import-name splits such as `pydantic-core` /
`pydantic_core`. It must not blindly replace underscores with hyphens for every
module name.

Legacy usage is evidence of transitional compatibility pressure, not runtime
ownership. A production dependency must have canonical runtime ownership outside
`legacy_app.py` or be explicitly documented as a temporary
`legacy_compat_transitional` dependency with an extraction/removal path. Root
`bmi_visualization.py`, legacy BMI compatibility shims, and
`app/services/bmi_compat.py` cannot by themselves promote a package to
canonical runtime ownership.

| Package | First-pass rule |
|---|---|
| `pyarrow` | Error if present in runtime, Docker runtime, CI-lite, or aggregate lock surfaces without canonical runtime owner evidence. Keep data/eval ownership separate. |
| `pandas` | Error if present in runtime, Docker runtime, or CI-lite surfaces. Data/eval only. |
| `httpx2` | Error if present in runtime, Docker runtime, or CI-lite surfaces. Dev/test only. |
| `reportlab` | Allowed as canonical runtime for export/PDF owners. |
| `matplotlib` | Warning as `legacy_compat_transitional` unless a canonical BMI owner is documented. Do not remove in this PR. |
| `numpy` | Warning as `transitive_only_direct_runtime_candidate` when directly declared without direct canonical runtime imports. It may remain transitive through `matplotlib`; direct runtime authority should be removed only when lock regeneration stays narrow and deterministic. |
| `aiosqlite` | Info as `sqlite_async_fallback_owner_documented` when `core/db.py` documents SQLite async URL derivation/fallback ownership. Keep scoped to local/dev/test SQLite fallback support, not production Postgres authority. |

`pyarrow` belongs to `requirements-data.in` / `requirements-data.txt` for
offline Parquet-capable data builders unless a future PR documents canonical
runtime owner evidence. Runtime, Docker runtime, CI-lite, and
`requirements-lock.txt` must not carry `pyarrow` as a production/control-plane
authority.

The locked installer may elide an equal minimum floor, such as
`package>=1.2.3`, only when the same selected requirement surface already pins
`package==1.2.3` without markers. Lower or stricter security floors must remain
in the effective constraints file so unsafe exact pins fail closed.

## Validation Rules

The validator fails when:

- a root `requirements*.in` or `requirements*.txt` file is missing from the
  executable registry;
- a compiled lockfile lacks its exact governed Make/profile/source header;
- an active lock workflow document teaches a direct resolver command or unsafe-package mode;
- a compiled lockfile contains a non-exact requirement entry;
- a compiled lockfile omits a normalized direct package from the union of its registry-owned
  `compile_sources`;
- local/manual surfaces leak into shared `requirements-profile` routing;
- required pip-audit or dependency-submission coverage is missing; or
- the first audited ownership subset violates its severity-tier policy; or
- this contract stops naming a registered surface.

PRs that change Python dependency ownership, install routing, or security
coverage must update both this document and
`scripts/ci/check_python_dependency_surfaces.py`.
