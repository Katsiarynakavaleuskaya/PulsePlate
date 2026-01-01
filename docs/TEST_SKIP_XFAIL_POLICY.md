# Test Skip/XFail Policy

## Overview

This document defines the policy for handling skipped and xfail tests in the PulsePlate test suite to maintain CI honesty and prevent technical debt.

## Classification of Skipped Tests

### Type A: "Expected Always" (Permanent Skip)

These are tests that legitimately cannot run in CI due to:
- External API dependencies (USDA, OpenFoodFacts)
- Optional dependencies (matplotlib, cryptography)
- Feature flags (EXPORTS_ENABLED, VIP_MODULE_ENABLED)
- Optional modules/features not available in CI

**Action**: Keep skip with clear reason:
```python
pytest.skip("requires external OFF/USDA API key")
pytest.skip("matplotlib not available")
```

**Examples in codebase**:
- `tests/test_bmi_visualization.py` - matplotlib checks
- `tests/test_secure_config.py` - cryptography checks
- `tests/test_legacy_app_diff_coverage.py` - EXPORTS_ENABLED checks

### Type B: "Expected in CI, but should run locally"

These are tests that:
- Require local datasets/snapshots
- Are integration tests with real DB
- Are slow/heavy tests

**Action**: Use markers (`@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.needs_data`) and exclude from PR runs:
```bash
pytest -m "not integration and not slow and not needs_data"
```

**Examples**:
- Async SQLAlchemy tests (if not configured in CI)
- Large dataset tests
- Integration tests with external services

### Type C: "Should not be skipped - hidden problem"

These are tests skipped due to:
- "Not stable", "flaky", "not finished"
- Real bugs/regressions
- Temporary workarounds

**Action**: 
- Create issue with deadline/criteria for fixing
- Convert to `xfail(strict=True)` temporarily if needed
- Track in project board

**Examples**:
- `tests/test_api.py:35` - "App import failed unexpectedly" (needs investigation)
- `tests/test_repo_policy_guards.py:85` - "TODO: Many legacy tests use sys.modules" (has issue)

## XFail Policy

### When XFail is OK

✅ OK if:
- Clear reason documented
- Has plan for fix (issue/PR)
- Temporary measure, not permanent

### Rule #1: Always use `strict=True`

```python
@pytest.mark.xfail(strict=True, reason="... TODO: ...")
```

This ensures:
- If test starts passing → XPASS becomes FAIL → you notice immediately
- Prevents "forgotten xfail" technical debt

### Current XFail Tests

1. **`test_bmi_visualization_endpoint_with_api_key`**
   - Reason: Test isolation issue in full suite - passes individually
   - TODO: Fix test isolation or use dependency override for API key
   - Status: `strict=True` ✅

2. **`test_no_calculate_all_bmr`**
   - Reason: calculate_all_bmr is not None after reload; patching not supported
   - TODO: Fix module reload/patching or use dependency override
   - Status: `strict=True` ✅

3. **`test_internal_error`**
   - Reason: app.routers.foods has no attribute 'get_foods'
   - TODO: Fix router structure or use proper dependency injection
   - Status: `strict=True` ✅

## Markers

Registered markers in `pyproject.toml`:

- `asyncio`: mark test as using asyncio
- `smoke`: fast smoke tests for critical endpoints
- `slow`: slow tests that should only run in nightly builds
- `heavy`: resource-intensive tests (integration, LLM, large datasets)
- `integration`: integration tests requiring external services
- `demo`: demo tests with verbose output
- `serial`: mark test to run serially (not in parallel)
- `xdist_group(name)`: group tests for xdist scheduling
- `needs_data`: requires local datasets/snapshots not available in CI
- `external`: hits external APIs (should be mocked in CI)
- `optional_dep`: requires optional dependencies (matplotlib, cryptography, etc.)

## CI Policy

### PR Pipeline
```bash
pytest -m "not integration and not slow and not needs_data"
```

### Nightly Pipeline (optional)
```bash
pytest -m "slow or integration"  # If environment supports it
```

## Maintenance

### Regular Review Process

1. Run `pytest -q -ra` to see all skipped/xfail
2. Review skipped tests quarterly:
   - Type A: Verify still valid
   - Type B: Ensure markers are correct
   - Type C: Check if issues are resolved
3. Review xfail tests:
   - Check if TODOs are actionable
   - Verify `strict=True` is set
   - Remove xfail when fixed

### Commands

```bash
# See all skipped/xfail with reasons
pytest -q -ra | grep -E "(SKIPPED|XFAIL|XPASS)"

# Count skipped by reason
pytest -q -ra | grep SKIPPED | sort | uniq -c

# Run only non-skipped tests
pytest -q -m "not skip"
```

## References

- [Pytest Skip/XFail Documentation](https://docs.pytest.org/en/stable/skipping.html)
- [Pytest Markers Documentation](https://docs.pytest.org/en/stable/how-to/mark.html)

