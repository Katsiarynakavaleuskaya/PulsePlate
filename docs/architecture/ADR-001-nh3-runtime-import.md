# ADR-001: Runtime Import for Optional nh3 Dependency

**Status:** Accepted
**Date:** 2025-12-16
**Context:** Premium plate endpoint sanitization

## Decision

Use runtime import (lazy import) for optional `nh3` dependency instead of module-level cached import.

## Problem

Module-level import caching caused pytest-xdist worker failures:

```python
# ❌ BROKEN: Module-level cached import
try:
    import nh3
    _nh3 = nh3
except ModuleNotFoundError:
    _nh3 = None

def _require_nh3():
    if _nh3 is None:  # Always None in xdist workers!
        raise RuntimeError("nh3 required")
    return _nh3
```

**Issue:** In pytest-xdist parallel workers:
1. Module loads before `nh3` is installed
2. `_nh3 = None` cached permanently in module global state
3. Even after `nh3` installation, cached `None` persists
4. All premium plate tests fail with "nh3 required" despite being installed

## Solution

Runtime import on every call to `_require_nh3()`:

```python
# ✅ CORRECT: Runtime import (no caching)
def _require_nh3() -> _NH3Protocol:
    try:
        import nh3  # Fresh import every time
        return cast(_NH3Protocol, nh3)
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "Optional dependency 'nh3' is required for plate data sanitization. "
            "Install it with: python -m pip install nh3"
        ) from e
```

## Why This Works

- **No module-level cache:** Import happens at runtime, not at module load
- **pytest-xdist safe:** Each call gets fresh import attempt
- **Hot-reload safe:** Code changes to nh3 reflected immediately
- **No performance penalty:** Python's `sys.modules` cache handles efficiency

## Consequences

**Positive:**
- ✅ Works with pytest-xdist parallel execution
- ✅ Clear error messages when nh3 missing
- ✅ No import-time side effects
- ✅ Hot-reload compatible (development/testing)

**Neutral:**
- Runtime import pattern instead of top-level import
- Type Protocol used for type safety instead of ModuleType

**Trade-offs:**
- Slightly less conventional than top-level imports
- Error raised at call-time, not import-time (acceptable for optional dependencies)

## Exit criteria (when this ADR can be retired)

This runtime-import pattern is intended to remain until one of the following becomes true:

- **nh3 becomes a mandatory dependency** for all supported deployments (no “optional” mode).
  Then we can reconsider moving to normal module-level import, provided it stays deterministic in CI/xdist.
- **The sanitization feature is removed or replaced** with a non-`nh3` implementation that is import-safe.

Until then, prefer **runtime import without module-level caching** for this optional dependency.

## Follow-ups

- If API semantics need improvement, follow the existing TODO:
  - Convert runtime `RuntimeError` mapping to a clearer HTTP status (e.g., 424/503) with structured JSON error response.

## Implementation

**Location:** `core/data_sanitizer.py`

**Version:** nh3 >= 0.3.2 (marked optional in requirements.in)

**Error Handling:** RuntimeError converted to HTTP 500 in current implementation.
**TODO (Future PR):** Convert to HTTP 424 (Failed Dependency) or 503 (Service Unavailable) with structured JSON error response for better API semantics.

## References

- PR #356: CodeRabbit Post-Merge Polish
- Commit: `03480fe0` (runtime import fix)
- Related: pytest-xdist module caching behavior
- Related: Pydantic field validators and import timing
