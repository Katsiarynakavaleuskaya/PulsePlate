# Dependency Security Guard - CVE Triage Workflow

## Overview

The dependency security guard prevents vulnerable dependency versions from entering the codebase. It enforces:

1. **Minimum version floors** - Packages must be at or above specified safe versions
2. **Blocked packages** - Specific packages that must not appear anywhere
3. **Blocked version ranges** - Specific vulnerable versions that must not be pinned

The guard runs as part of `make verify` and validates all 5 requirement surfaces.

## Schema Location

**Source of Truth:** `tests/fixtures/dependency_security_schema.json`

```json
{
  "min_versions": {
    "cryptography": "46.0.5"
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

**Important:** Packages in `min_versions` must exist in ALL 5 requirement surfaces:
- `requirements.in`
- `requirements.txt`
- `requirements-dev.txt`
- `requirements-lock.txt`
- `constraints.txt`

Dev-only dependencies (like `marshmallow`) cannot currently be tracked in `min_versions` because they don't exist in runtime surfaces. This is a known limitation.

### 3. Update Requirement Surfaces

1. Bump version in `requirements.in` or `requirements-dev.in`
2. Regenerate locks:
   ```bash
   pip-compile --allow-unsafe requirements.in -o requirements.txt
   pip-compile --allow-unsafe requirements-dev.in -o requirements-dev.txt
   pip-compile --allow-unsafe requirements.in requirements-dev.in -o requirements-lock.txt
   ```
3. Update `constraints.txt` if needed

### 4. Verify Guard

```bash
# Run guard tests only
pytest -q tests/test_dependency_security_guard.py

# Full verification (includes guard)
make verify
```

### 5. Document in PR

- Link to CVE doc in PR description
- Update `docs/roadmap/BACKLOG_LEDGER.md` if applicable
- Include evidence across all tracked surfaces:
  `rg -n "^<package>" requirements.in requirements.txt requirements-dev.txt requirements-lock.txt constraints.txt`

## Examples

### Example 1: Minimum Version Floor (cryptography CVE)

**Scenario:** CVE-2026-26007 fixed in cryptography 46.0.5

**Schema update:**
```json
{
  "min_versions": {
    "cryptography": "46.0.5"
  }
}
```

**Requirement updates:**
- `requirements.in`: `cryptography>=46.0.5,<47.0.0`
- `requirements-dev.in`: `cryptography>=46.0.5`
- `constraints.txt`: `cryptography>=46.0.5`
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
4. **All surfaces:** `min_versions` packages must exist in all 5 surfaces

## CI Integration

- Guard runs in `make test-fast` -> `make verify`
- PR cannot merge if guard fails
- Deterministic: no network calls, no external state

## Validated Surfaces

| Surface | Type | Purpose |
|---------|------|---------|
| `requirements.in` | Constraint (>=) | Runtime deps source |
| `requirements.txt` | Pinned (==) | Runtime deps lock |
| `requirements-dev.txt` | Pinned (==) | Dev deps lock |
| `requirements-lock.txt` | Pinned (==) | Full lock |
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

## Future Enhancements

- Per-surface package targeting (for dev-only deps like `marshmallow`)
- Pre-commit hook integration
- Aggregate error reporting (show all violations, not fail-fast)
