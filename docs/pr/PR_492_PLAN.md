# PR-492 Plan: BMI Visualization Contract Documentation + Tests

## Summary

**Type:** Documentation + Contract Tests
**Branch:** `docs/pr-492-bmi-visualization-contract`
**Goal:** Document BMI visualization contract for iOS/Web + add contract tests to prevent regressions.

---

## 🎯 Why This PR

1. **iOS/Web developers need documented contract** to implement visualization
2. **Contract tests prevent regressions** when backend changes
3. **Examples speed up client development** (copy-paste ready JSON)
4. **Low risk, high value** (docs + tests, no production changes)

---

## 📋 Files Changed

### New Files (2)

1. **`docs/bmi/visualization.md`**
   - Contract explanation
   - JSON examples for different groups
   - `visualization: null` cases
   - Fallback behavior

2. **`tests/test_bmi_contract_visualization.py`**
   - Contract structure validation
   - Group-specific range validation
   - `visualization: null` cases
   - Range monotonicity checks

### No Production Code Changes

- ❌ No changes to `app/schemas/bmi.py`
- ❌ No changes to `app/services/bmi_visualization.py`
- ❌ No changes to `app/routers/bmi.py`
- ❌ No changes to `core/bmi/engine.py`

**Pure documentation + contract tests only.**

---

## 📝 Documentation Structure

### `docs/bmi/visualization.md`

```markdown
# BMI Visualization Contract

## Overview

The `/api/v1/bmi/calculate` endpoint returns an optional `visualization` field
containing a JSON spec for rendering a BMI scale visualization.

## Field: `visualization`

- **Type:** `BMIScaleV1Spec | None`
- **When `null`:** Groups with `category=None` (too_young, child, teen, pregnant)
- **Fallback:** If builder fails, endpoint returns `200` with `visualization: null`

## Structure: `BMIScaleV1Spec`

```json
{
  "kind": "bmi_scale_v1",
  "bmi": 23.4,
  "min": 0.0,
  "max": 60.0,
  "ranges": [
    {"key": "bmi.underweight", "from": 0, "to": 18.5},
    {"key": "bmi.normal", "from": 18.5, "to": 25.0},
    {"key": "bmi.overweight", "from": 25.0, "to": 30.0},
    {"key": "bmi.obesity", "from": 30.0, "to": 60.0}
  ],
  "marker": {"value": 23.4}
}
```

## Group-Specific Ranges

### Adult (General)
- Normal: 18.5 → 25.0

### Athlete
- Normal: 18.5 → 27.0 (extends to 27.0)

### Elderly
- Underweight: 0 → 17.5 (lower threshold)
- Normal: 17.5 → 26.0 (extends to 26.0)

### Child/Teen/Too Young/Pregnant
- `visualization: null` (no visualization shown)

## Examples

[4 JSON examples: adult, athlete, elderly, null case]
```

---

## 🧪 Contract Tests Structure

### `tests/test_bmi_contract_visualization.py`

```python
"""
Contract tests for BMI visualization field.

These tests verify the API contract structure, not the BMI calculation logic.
"""

import pytest
from fastapi.testclient import TestClient

from app import app


class TestBMIVisualizationContract:
    """Contract tests for visualization field structure."""

    def test_visualization_structure_for_adult(self):
        """Test visualization structure for adult general group."""
        client = TestClient(app)
        resp = client.post(
            "/api/v1/bmi/calculate",
            json={
                "weight_kg": 70.0,
                "height_cm": 175.0,
                "age": 30,
                "gender": "male",
                "lang": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        # Contract: visualization exists for adult
        assert "visualization" in data
        assert data["visualization"] is not None

        viz = data["visualization"]
        assert viz["kind"] == "bmi_scale_v1"
        assert "bmi" in viz
        assert "min" in viz
        assert "max" in viz
        assert "ranges" in viz
        assert "marker" in viz

        # Contract: ranges structure
        ranges = viz["ranges"]
        assert len(ranges) == 4
        assert all("key" in r and "from" in r and "to" in r for r in ranges)

        # Contract: ranges monotonic (no gaps)
        assert ranges[0]["from"] == viz["min"]
        assert ranges[-1]["to"] == viz["max"]
        for i in range(len(ranges) - 1):
            assert ranges[i]["to"] == ranges[i + 1]["from"]

    def test_visualization_null_for_child(self):
        """Test visualization is null for child group."""
        client = TestClient(app)
        resp = client.post(
            "/api/v1/bmi/calculate",
            json={
                "weight_kg": 40.0,
                "height_cm": 140.0,
                "age": 12,  # child age
                "gender": "male",
                "lang": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        # Contract: visualization is null for category=None groups
        assert "visualization" in data
        assert data["visualization"] is None

    def test_athlete_normal_range_extends_to_27(self):
        """Test athlete group has extended normal range (to 27.0)."""
        client = TestClient(app)
        resp = client.post(
            "/api/v1/bmi/calculate",
            json={
                "weight_kg": 85.0,
                "height_cm": 180.0,
                "age": 25,
                "gender": "male",
                "athlete": True,
                "lang": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        # Contract: athlete normal range extends to 27.0
        assert data["visualization"] is not None
        ranges = data["visualization"]["ranges"]
        normal_range = next(r for r in ranges if r["key"] == "bmi.normal")
        assert normal_range["to"] == 27.0

    def test_elderly_underweight_threshold_17_5(self):
        """Test elderly group has lower underweight threshold (17.5)."""
        client = TestClient(app)
        resp = client.post(
            "/api/v1/bmi/calculate",
            json={
                "weight_kg": 60.0,
                "height_cm": 180.0,
                "age": 75,  # elderly age
                "gender": "male",
                "lang": "en",
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        # Contract: elderly underweight threshold is 17.5
        assert data["visualization"] is not None
        ranges = data["visualization"]["ranges"]
        underweight_range = next(r for r in ranges if r["key"] == "bmi.underweight")
        assert underweight_range["to"] == 17.5
```

---

## ✅ Commit Plan

### Commit 1: Documentation
```
docs(bmi): add BMI visualization contract documentation

- Add docs/bmi/visualization.md with contract explanation
- Include JSON examples for adult/athlete/elderly/null cases
- Document group-specific range differences
- Explain fallback behavior
```

### Commit 2: Contract Tests
```
test(bmi): add contract tests for visualization field

- Add tests/test_bmi_contract_visualization.py
- Test visualization structure for different groups
- Test visualization: null cases
- Test group-specific range differences (athlete vs adult)
- Test range monotonicity (no gaps)
```

---

## 🧪 Testing

```bash
# Run contract tests
pytest -q tests/test_bmi_contract_visualization.py

# Run all tests
pytest -q

# Verify no production code changes
git diff main -- app/ core/
```

---

## 📄 PR Description

```markdown
## Summary

Document BMI visualization contract and add contract tests to prevent regressions.

**Type:** Documentation + Contract Tests
**No production code changes.**

---

## What Changed

### Added

- `docs/bmi/visualization.md` — Contract documentation with JSON examples
- `tests/test_bmi_contract_visualization.py` — Contract validation tests

### Changed

- None (pure documentation + tests)

---

## Why This Change

1. **iOS/Web developers need documented contract** to implement visualization
2. **Contract tests prevent regressions** when backend changes
3. **Examples speed up client development** (copy-paste ready JSON)
4. **Low risk, high value** (docs + tests, no production changes)

---

## Contract Details

- `visualization: BMIScaleV1Spec | None` field in `/api/v1/bmi/calculate` response
- `null` for groups with `category=None` (too_young, child, teen, pregnant)
- Group-specific ranges:
  - Adult: normal 18.5 → 25.0
  - Athlete: normal 18.5 → 27.0
  - Elderly: underweight 0 → 17.5, normal 17.5 → 26.0
- Fallback: endpoint returns `200` with `visualization: null` if builder fails

---

## Testing

- ✅ Contract tests pass
- ✅ All existing tests pass
- ✅ No production code changes

---

## Related

- Follow-up to PR-490B (BMI visualization group-aware)
- Enables Sprint C.2 (iOS BMI bootstrap)
```

---

## ✅ Checklist

- [ ] Create branch `docs/pr-492-bmi-visualization-contract`
- [ ] Create `docs/bmi/visualization.md` with contract + examples
- [ ] Create `tests/test_bmi_contract_visualization.py` with contract tests
- [ ] Run `pytest -q tests/test_bmi_contract_visualization.py`
- [ ] Run `pytest -q` (all tests)
- [ ] Verify no production code changes
- [ ] Commit 1: Documentation
- [ ] Commit 2: Contract tests
- [ ] Push and open PR

---

## 🔒 Safety: Parallel Work with Sprint C.1

**No conflicts expected:**

- Sprint B: `docs/bmi/visualization.md` (new file) + `tests/test_bmi_contract_visualization.py` (new file)
- Sprint C.1: `ios/PulsePlate/*/Localizable.strings` (iOS files) + possibly `core/i18n/keys.py` (new file)

**Files don't overlap** → safe to work in parallel.
