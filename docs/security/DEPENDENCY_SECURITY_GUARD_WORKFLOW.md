# Dependency Security Guard - CVE Triage Workflow

## Overview

The dependency security guard prevents vulnerable dependency versions from entering the codebase. It enforces:

1. **Minimum version floors** - Packages must be at or above specified safe versions
2. **Blocked packages** - Specific packages that must not appear anywhere
3. **Blocked version ranges** - Specific vulnerable versions that must not be pinned

The guard runs as part of the focused dependency-security test bundle and validates
the canonical shared requirement surfaces listed by
`tests/test_dependency_security_guard.py::REQUIREMENT_SURFACES`.

## Schema Location

**Source of Truth:** `tests/fixtures/dependency_security_schema.json`

```json
{
  "min_versions": {
    "click": "8.3.3",
    "cryptography": "48.0.1",
    "pillow": "12.3.0"
  },
  "blocked_packages": [],
  "blocked_versions": {}
}
```

## When to Update the Guard

Update the schema when:

- GitHub Dependabot alerts for Python dependencies
- Trivy code scanning reports application dependency CVEs
- Manual CVE triage identifies vulnerable package versions
- Security audit requires blocking specific packages

## Workflow Steps

### 1. Triage CVE

1. Verify CVE affects application dependencies (not distro/OS packages)
2. Determine fixed version from advisory or upstream
3. Create CVE doc: `docs/security/CVE-YYYY-NNNNN-<package>.md`

### 2. Update Schema

Choose the appropriate schema section:

| Scenario | Schema Field | Example |
|----------|-------------|---------|
| Set minimum safe version | `min_versions` | `"pkg": "2.0.0"` |
| Ban package entirely | `blocked_packages` | `["unsafe-pkg"]` |
| Block specific versions | `blocked_versions` | `{"pkg": [">=1.0,<1.5"]}` |

**Important:** Packages in `min_versions` must exist in all tracked requirement surfaces:
- `requirements.in`
- `requirements-docker-runtime.in`
- `requirements-ci-lite.in`
- `requirements-dev.in`
- `requirements.txt`
- `requirements-docker-runtime.txt`
- `requirements-dev.txt`
- `requirements-lock.txt`
- `requirements-ci-lite.txt`
- `constraints.txt`

Dev-only dependencies (like `marshmallow`) cannot currently be tracked in `min_versions` because they don't exist in runtime surfaces. This is a known limitation.
Optional manifests such as `requirements-rag-vector.in` / `requirements-rag-vector.txt`
must be covered by explicit contract/audit checks, but they are not part of the
`min_versions` all-surfaces requirement until the guard supports per-surface
targeting.

### 2a. Preflight source availability before install

Before full dependency install in CI, run fail-fast availability preflight through the same
approved proxy path used by canonical install:

- `scripts/ci/install_locked_python_requirements.py --preflight-only`
- Uses `PULSEPLATE_PYTHON_INDEX_URL` (+ optional `PULSEPLATE_PYTHON_TRUSTED_HOST`)
- Checks floor versions from `min_versions`
- Allows only exact emergency fallback artifacts from `scripts/ci/emergency_python_wheels.json`

This separates **security floor policy** from **source availability** and fails early when
the proxy is stale.

### 3. Update Requirement Surfaces

1. Bump version in `requirements.in` or `requirements-dev.in`
2. Regenerate every affected canonical shared lock through the approved private
   proxy. Preserve the existing output file as the resolver seed and never emit
   the index URL into a tracked lock:
   ```bash
   pip-compile --allow-unsafe --no-emit-index-url \
     --output-file=requirements.txt requirements.in
   pip-compile --allow-unsafe --no-emit-index-url \
     --output-file=requirements-docker-runtime.txt requirements-docker-runtime.in
   pip-compile --allow-unsafe --no-emit-index-url \
     --output-file=requirements-ci-lite.txt requirements-ci-lite.in
   pip-compile --allow-unsafe --constraint=requirements.txt --no-emit-index-url \
     --output-file=requirements-dev.txt requirements-dev.in
   pip-compile --allow-unsafe --no-emit-index-url \
     --output-file=requirements-lock.txt requirements-dev.in requirements.in
   ```
3. Regenerate an optional lock only when that profile already owns the affected
   package. For example:
   ```bash
   pip-compile --allow-unsafe --no-emit-index-url \
     --output-file=requirements-rag-vector.txt requirements-rag-vector.in
   pip-compile --allow-unsafe --no-emit-index-url \
     --output-file=requirements-rag-vector-cpu.txt requirements-rag-vector-cpu.in
   ```
   Do not pull optional data, eval, or vector dependencies into shared runtime
   profiles merely to make the versions uniform.
4. Update `constraints.txt` manually when the security floor is part of the
   shared resolver contract; `constraints.txt` is not a compiled lock.

### 4. Verify Guard

```bash
# Run guard tests only
pytest -q tests/test_dependency_security_guard.py

# Required local narrow bundle; full-suite parity comes from current-head CI
make validate-changed
pre-commit run --all-files
```

### 5. Document in PR

- Link to CVE doc in PR description
- Update `docs/roadmap/BACKLOG_LEDGER.md` if applicable
- Include evidence across all tracked surfaces:
  `rg -n "^<package>" requirements.in requirements-docker-runtime.in requirements-ci-lite.in requirements-dev.in requirements.txt requirements-docker-runtime.txt requirements-dev.txt requirements-lock.txt requirements-ci-lite.txt constraints.txt`

## Examples

### Example 1: Minimum Version Floors (Click, Pillow, and cryptography)

**Scenario:** current scanner findings require Click 8.3.3, cryptography 48.0.1,
and Pillow 12.3.0.

**Schema update:**
```json
{
  "min_versions": {
    "click": "8.3.3",
    "cryptography": "48.0.1",
    "pillow": "12.3.0"
  }
}
```

**Requirement updates:**
- `requirements.in`: `click>=8.3.3,<9.0.0`, `cryptography>=48.0.1,<49.0.0`,
  and `pillow>=12.3.0,<13.0.0`
- `requirements-dev.in`: `click>=8.3.3,<9.0.0`,
  `cryptography>=48.0.1,<49.0.0`, and `pillow>=12.3.0,<13.0.0`
- `constraints.txt`: `click==8.3.3`, `cryptography>=48.0.1`, and
  `pillow==12.3.0`
- Regenerate locks

### Example 2: Blocked Package

**Scenario:** Package `unsafe-lib` has no safe version, must be removed

**Schema update:**
```json
{
  "blocked_packages": ["unsafe-lib"]
}
```

**Remediation:**
- Remove from `requirements*.in` (and deps that pull it)
- Regenerate locks
- Guard will fail if any surface still contains it

### Example 3: Blocked Version Range

**Scenario:** Package `some-pkg` versions 2.0.0-2.0.5 are vulnerable

**Schema update:**
```json
{
  "blocked_versions": {
    "some-pkg": [">=2.0.0,<2.0.6"]
  }
}
```

**Note:** Blocked versions are only checked on pinned (`==`) surfaces, not constraint-style surfaces.

## Schema Maintenance Rules

1. **Sorting:** All keys and lists must be sorted alphabetically (case-insensitive) for clean diffs
2. **No comments:** JSON doesn't support comments; use CVE docs for rationale
3. **Case-insensitive:** Package names are matched case-insensitively
4. **All surfaces:** `min_versions` packages must exist in all 10 surfaces
   declared by `tests/test_dependency_security_guard.py:21-32`

## CI Integration

- Guard runs in `make test-fast`; current-head CI supplies the full-suite parity
  signal required for merge readiness
- PR cannot merge if guard fails
- Deterministic for policy checks: no network calls and no external state in the guard itself; the optional CI preflight (`scripts/ci/install_locked_python_requirements.py --preflight-only`) performs network reads against `PULSEPLATE_PYTHON_INDEX_URL` and may use `scripts/ci/emergency_python_wheels.json` for verified emergency fallbacks

## Validated Surfaces

| Surface | Type | Purpose |
|---------|------|---------|
| `requirements.in` | Constraint (>=) | Runtime deps source |
| `requirements-docker-runtime.in` | Constraint (>=) | Docker runtime source |
| `requirements-ci-lite.in` | Constraint (>=) | Lightweight CI source |
| `requirements-dev.in` | Constraint (>=) | Development source |
| `requirements.txt` | Pinned (==) | Runtime deps lock |
| `requirements-docker-runtime.txt` | Pinned (==) | Docker runtime lock |
| `requirements-dev.txt` | Pinned (==) | Dev deps lock |
| `requirements-lock.txt` | Pinned (==) | Full lock |
| `requirements-ci-lite.txt` | Pinned (==) | Lightweight CI lock |
| `constraints.txt` | Constraint (>=) | Flexible ranges |

## How to Fix Failures

| Failure Type | Fix |
|--------------|-----|
| Min version floor violation | Bump package in requirements, regenerate locks |
| Blocked package violation | Remove package from dependencies, regenerate locks |
| Blocked version violation | Pin to safe version outside blocked range, regenerate locks |

## References

- Schema file: `tests/fixtures/dependency_security_schema.json`
- Test file: `tests/test_dependency_security_guard.py`
- Guard enforcement: `tests/test_dependency_security_guard.py:176` (min_versions test)
- Blocked packages test: `tests/test_dependency_security_guard.py:278` (blocked_packages enforcement)
- Blocked versions test: `tests/test_dependency_security_guard.py:297` (blocked_versions enforcement)
- AGENTS policy: `AGENTS.md:1535` (Dependency floor / security guard section)
- CVE docs: `docs/security/CVE-*.md`
- Click/Pillow hotfix: `docs/security/PYSEC_2026_CLICK_PILLOW_HOTFIX.md`

## Future Enhancements

- Per-surface package targeting (for dev-only deps like `marshmallow`)
- Pre-commit hook integration
- Aggregate error reporting (show all violations, not fail-fast)
