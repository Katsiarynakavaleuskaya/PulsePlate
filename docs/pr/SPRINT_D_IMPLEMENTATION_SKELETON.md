# Sprint D: Implementation Skeleton (Ready-to-Use)

## 🎯 Purpose

This document provides **exact code changes** for Sprint D i18n alignment. Copy-paste ready.

**Status:** Planning document (not implementation)
**When to use:** After Sprint C.1/C.2 are merged

---

## 📋 Branch & Setup

```bash
# 1. Start from main
git checkout main
git pull --ff-only

# 2. Create branch
git checkout -b feat/pr-d-i18n-alignment

# 3. Ready to implement
```

---

## 🔧 Commit 1: Add Dot-Keys to TRANSLATIONS

### File: `core/i18n.py`

### Change 1: Add keys to Russian (`"ru"` dict)

**Location:** After line 18 (after `"bmi_obese_3"`)

**Add:**
```python
        "bmi_obese_3": "Ожирение III степени",
        # BMI Visualization (dot-keys for contract)
        "bmi.underweight": "Недостаточная масса",
        "bmi.normal": "Норма",
        "bmi.overweight": "Избыточная масса",
        "bmi.obesity": "Ожирение",
        # Activity Levels
```

### Change 2: Add keys to English (`"en"` dict)

**Location:** After line 115 (after `"bmi_obese_3"`)

**Add:**
```python
        "bmi_obese_3": "Obese Class III",
        # BMI Visualization (dot-keys for contract)
        "bmi.underweight": "Underweight",
        "bmi.normal": "Normal",  # Short for scale label (not "Normal weight")
        "bmi.overweight": "Overweight",
        "bmi.obesity": "Obesity",
        # Activity Levels
```

**Note:** Keep `"bmi_normal": "Normal weight"` for general text, use `"bmi.normal": "Normal"` for visualization scale.

### Change 3: Add keys to Spanish (`"es"` dict)

**Location:** After line 210 (after `"bmi_obese_3"`)

**Add:**
```python
        "bmi_obese_3": "Obesidad Clase III",
        # BMI Visualization (dot-keys for contract)
        "bmi.underweight": "Bajo peso",
        "bmi.normal": "Normal",
        "bmi.overweight": "Sobrepeso",
        "bmi.obesity": "Obesidad",
        # Activity Levels
```

### Commit Command

```bash
git add core/i18n.py
git commit -m "feat(i18n): add BMI visualization dot-keys (bmi.underweight, etc.)"
```

---

## 🔧 Commit 2: Fix normalize_lang Policy

### File: `core/i18n.py`

### Change 1: Update LOCALE_SPECIAL_CASES

**Location:** Lines 311-327

**Replace:**
```python
LOCALE_SPECIAL_CASES: dict[str, dict[str, Any]] = {
    # English: Always maps to English (no exceptions needed)
    "en": {
        "default": "en",
        "exceptions": set(),  # All English regions → English
    },
    # Russian: Business requirement - all regions fallback to English
    "ru": {
        "default": "en",
        "exceptions": set(),  # No Russian regions map to Russian
    },
    # Spanish: Market-selective - only Mexico gets Spanish, rest get English
    "es": {
        "default": "en",
        "exceptions": {"mx"},  # Only Mexico gets Spanish
    },
}
```

**With:**
```python
LOCALE_SPECIAL_CASES: dict[str, dict[str, Any]] = {
    # English: Always maps to English (no exceptions needed)
    "en": {
        "default": "en",
        "exceptions": set(),  # All English regions → English
    },
    # Russian: Product goal - RU/ES/EN localization for iOS
    # ru-RU and ru → ru (not en)
    "ru": {
        "default": "ru",  # Changed: ru regions → ru (not en)
        "exceptions": set(),  # All Russian regions → Russian
    },
    # Spanish: Product goal - Spain priority (not Mexico-only)
    # es-ES and es → es (not en)
    "es": {
        "default": "es",  # Changed: es regions → es (not en)
        "exceptions": set(),  # All Spanish regions → Spanish
    },
}
```

### Change 2: Update LANG_ALIASES

**Location:** Lines 344-371

**Replace:**
```python
    # Russian markets (selective support)
    "ru-ru": "en",  # Regional Russian → English (business requirement)
    # Spanish markets (selective support)
    "es-mx": "es",  # Mexico → Spanish (primary market)
    "es-es": "en",  # Spain → English (secondary market)
    "es-ar": "en",  # Argentina → English (secondary market)
```

**With:**
```python
    # Russian markets (product goal: RU/ES/EN localization)
    "ru-ru": "ru",  # Regional Russian → Russian (not en)
    # Spanish markets (product goal: Spain priority)
    "es-mx": "es",  # Mexico → Spanish
    "es-es": "es",  # Spain → Spanish (changed: not en)
    "es-ar": "es",  # Argentina → Spanish (changed: not en)
```

### Change 3: Update normalize_lang Docstring Examples

**Location:** Lines 436-441

**Replace:**
```python
    Examples:
        >>> normalize_lang("en-US")    # → "en" (en default)
        >>> normalize_lang("es-MX")    # → "es" (mx in es exceptions)
        >>> normalize_lang("es-ES")    # → "en" (es default, ES not in exceptions)
        >>> normalize_lang("ru-RU")    # → "en" (ru default, no exceptions)
        >>> normalize_lang("français") # → "en" (unsupported)
```

**With:**
```python
    Examples:
        >>> normalize_lang("en-US")    # → "en" (en default)
        >>> normalize_lang("es-MX")    # → "es" (es default)
        >>> normalize_lang("es-ES")    # → "es" (es default, changed: not en)
        >>> normalize_lang("ru-RU")    # → "ru" (ru default, changed: not en)
        >>> normalize_lang("français") # → "en" (unsupported)
```

### Commit Command

```bash
git add core/i18n.py
git commit -m "fix(i18n): normalize_lang maps ru/es to themselves, not en"
```

---

## 🔧 Commit 3: Add Tests

### File: `tests/test_i18n_bmi_visualization.py` (new file)

**Create new file:**

```python
"""
Tests for BMI visualization i18n keys and normalize_lang policy.

RU: Тесты для ключей i18n visualization и политики normalize_lang.
EN: Tests for BMI visualization i18n keys and normalize_lang policy.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app import app
from core.i18n import TRANSLATIONS, normalize_lang, t


def _post_bmi(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    """
    RU: POST helper для BMI calculate endpoint.
    EN: POST helper for BMI calculate endpoint.
    """
    resp = client.post("/api/v1/bmi/calculate", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    return resp.json()


def _valid_payload(**overrides: Any) -> dict[str, Any]:
    """
    RU: Валидный payload для BMICalculateRequest (гарантирует adult group с visualization).
    EN: Valid payload for BMICalculateRequest (guarantees adult group with visualization).

    Defaults ensure adult group (age=25, not pregnant, not athlete).
    """
    base: dict[str, Any] = {
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "age": 25,  # Adult (not teen, not elderly)
        "gender": "male",
        "pregnant": "no",  # Not pregnant
        "athlete": "no",  # Not athlete (baseline adult)
        "lang": "en",
    }
    base.update(overrides)
    return base


class TestBMIVisualizationKeys:
    """
    RU: Тесты на наличие ключей visualization во всех языках.
    EN: Tests for visualization keys existence in all languages.
    """

    def test_bmi_visualization_keys_exist_in_all_langs(self) -> None:
        """
        RU: Все ключи visualization присутствуют во всех языках.
        EN: All visualization keys exist in all languages.
        """
        keys = ["bmi.underweight", "bmi.normal", "bmi.overweight", "bmi.obesity"]
        for lang in ["ru", "en", "es"]:
            for key in keys:
                assert key in TRANSLATIONS[lang], f"Missing {key} in {lang}"
                assert TRANSLATIONS[lang][key], f"Empty {key} in {lang}"

    def test_bmi_visualization_keys_map_to_translations_via_api_adult(self) -> None:
        """
        RU: Ключи из visualization ranges (adult group, через API) мапятся на переводы без KeyError.
        EN: Visualization range keys (adult group, via API) map to translations without KeyError.

        Contract-first approach: uses actual API endpoint to get ranges,
        then verifies i18n keys are translatable. Tests adult baseline group.
        """
        client = TestClient(app)

        # Adult group (baseline, has visualization)
        payload = _valid_payload(age=25, athlete="no")
        data = _post_bmi(client, payload)
        visualization = data.get("visualization")

        # Contract: adult group must have visualization
        assert visualization is not None, "Adult group must have visualization"
        ranges = visualization.get("ranges", [])

        # Extract all i18n keys from ranges (only check keys, not numbers)
        i18n_keys = [r["key"] for r in ranges if "key" in r]

        # Verify all keys are exactly the 4 expected keys
        expected_keys = {"bmi.underweight", "bmi.normal", "bmi.overweight", "bmi.obesity"}
        assert set(i18n_keys) == expected_keys, f"Expected {expected_keys}, got {set(i18n_keys)}"

        # Verify all keys are translatable in all languages
        for key in i18n_keys:
            for lang in ["ru", "en", "es"]:
                translation = t(lang, key)
                assert translation, f"Empty translation for {key} in {lang}"
                # Verify it's not just the key itself (actual translation)
                assert translation != key, f"Translation missing for {key} in {lang}"

    def test_bmi_visualization_keys_map_to_translations_via_api_athlete(self) -> None:
        """
        RU: Ключи из visualization ranges (athlete group, через API) мапятся на переводы.
        EN: Visualization range keys (athlete group, via API) map to translations.

        Tests athlete group (normal upper bound differs from adult).
        """
        client = TestClient(app)

        # Athlete group (has visualization, different thresholds)
        payload = _valid_payload(age=25, athlete="yes")
        data = _post_bmi(client, payload)
        visualization = data.get("visualization")

        # Contract: athlete group must have visualization
        assert visualization is not None, "Athlete group must have visualization"
        ranges = visualization.get("ranges", [])

        # Extract i18n keys (only check keys, not numbers)
        i18n_keys = [r["key"] for r in ranges if "key" in r]

        # Verify all keys are translatable
        expected_keys = {"bmi.underweight", "bmi.normal", "bmi.overweight", "bmi.obesity"}
        assert set(i18n_keys) == expected_keys, f"Expected {expected_keys}, got {set(i18n_keys)}"

        for key in i18n_keys:
            for lang in ["ru", "en", "es"]:
                translation = t(lang, key)
                assert translation, f"Empty translation for {key} in {lang}"
                assert translation != key, f"Translation missing for {key} in {lang}"

    def test_bmi_visualization_keys_map_to_translations_via_api_elderly(self) -> None:
        """
        RU: Ключи из visualization ranges (elderly group, через API) мапятся на переводы.
        EN: Visualization range keys (elderly group, via API) map to translations.

        Tests elderly group (different underweight/normal thresholds).
        """
        client = TestClient(app)

        # Elderly group (age >= 60, has visualization, different thresholds)
        payload = _valid_payload(age=75, athlete="no")
        data = _post_bmi(client, payload)
        visualization = data.get("visualization")

        # Contract: elderly group must have visualization
        assert visualization is not None, "Elderly group must have visualization"
        ranges = visualization.get("ranges", [])

        # Extract i18n keys (only check keys, not numbers)
        i18n_keys = [r["key"] for r in ranges if "key" in r]

        # Verify all keys are translatable
        expected_keys = {"bmi.underweight", "bmi.normal", "bmi.overweight", "bmi.obesity"}
        assert set(i18n_keys) == expected_keys, f"Expected {expected_keys}, got {set(i18n_keys)}"

        for key in i18n_keys:
            for lang in ["ru", "en", "es"]:
                translation = t(lang, key)
                assert translation, f"Empty translation for {key} in {lang}"
                assert translation != key, f"Translation missing for {key} in {lang}"


class TestNormalizeLangPolicy:
    """
    RU: Тесты на политику normalize_lang (ru/es мапятся на себя).
    EN: Tests for normalize_lang policy (ru/es map to themselves).
    """

    def test_normalize_lang_ru_maps_to_ru(self) -> None:
        """
        RU: ru-RU и ru мапятся на ru, не на en (разные регистры и разделители).
        EN: ru-RU and ru map to ru, not en (different cases and separators).
        """
        # Standard formats
        assert normalize_lang("ru-RU") == "ru"
        assert normalize_lang("ru") == "ru"
        # Lowercase variant
        assert normalize_lang("ru-ru") == "ru"
        # Underscore separator (normalized to dash)
        assert normalize_lang("ru_RU") == "ru"
        assert normalize_lang("ru_ru") == "ru"
        # Mixed case
        assert normalize_lang("RU-ru") == "ru"
        assert normalize_lang("RU-RU") == "ru"

    def test_normalize_lang_es_maps_to_es(self) -> None:
        """
        RU: es-ES, es-MX, es-AR и es мапятся на es, не на en (разные регистры и разделители).
        EN: es-ES, es-MX, es-AR and es map to es, not en (different cases and separators).
        """
        # Standard formats
        assert normalize_lang("es-ES") == "es"  # Changed: was "en"
        assert normalize_lang("es-MX") == "es"
        assert normalize_lang("es-AR") == "es"  # Changed: was "en"
        assert normalize_lang("es") == "es"
        # Lowercase variants
        assert normalize_lang("es-es") == "es"
        assert normalize_lang("es-mx") == "es"
        # Underscore separator (normalized to dash)
        assert normalize_lang("es_ES") == "es"
        assert normalize_lang("es_es") == "es"
        # Mixed case
        assert normalize_lang("ES-es") == "es"
        assert normalize_lang("ES-ES") == "es"

    def test_normalize_lang_en_maps_to_en(self) -> None:
        """
        RU: en-US, en-GB и en мапятся на en.
        EN: en-US, en-GB and en map to en.
        """
        assert normalize_lang("en-US") == "en"
        assert normalize_lang("en-GB") == "en"
        assert normalize_lang("en") == "en"

    def test_normalize_lang_unknown_fallback_to_en(self) -> None:
        """
        RU: Неизвестные языки мапятся на en (fallback).
        EN: Unknown languages map to en (fallback).
        """
        assert normalize_lang("fr") == "en"
        assert normalize_lang("de-DE") == "en"
        assert normalize_lang("français") == "en"
        assert normalize_lang(None) == "en"
        assert normalize_lang("") == "en"
```

### Commit Command

```bash
git add tests/test_i18n_bmi_visualization.py
git commit -m "test(i18n): add tests for visualization keys and normalize_lang"
```

---

## ✅ Verification Checklist

After all 3 commits:

```bash
# 1. Run new tests
pytest -q tests/test_i18n_bmi_visualization.py

# 2. Run all tests (ensure no regressions)
pytest -q

# 3. Check coverage (use project's make command)
make cov-check

# 4. Lint (use project's make command)
make lint

# 5. Format check (if applicable)
make fmt-check  # or black --check
```

**Note:** Use project's `make` commands (not direct `mypy`/`ruff`) to match CI.

---

## 📝 PR Description (Copy-Paste Ready)

```markdown
## Summary

Align backend i18n with BMI visualization contract and fix normalize_lang policy.

**Type:** Backend refactoring (i18n)
**Follow-up to:** PR-492 (BMI visualization contract)

---

## What Changed

### Added

- BMI visualization dot-keys to `TRANSLATIONS` (RU/EN/ES):
  - `bmi.underweight`
  - `bmi.normal` (short for scale label)
  - `bmi.overweight`
  - `bmi.obesity`
- Tests for visualization keys and normalize_lang policy

### Changed

- `normalize_lang` policy:
  - `ru-RU` → `ru` (was: `en`)
  - `es-ES` → `es` (was: `en`)
  - `es-AR` → `es` (was: `en`)
- `LOCALE_SPECIAL_CASES`: `ru`/`es` defaults changed from `en` to themselves

### Kept (Backward Compatible)

- Old underscore-keys (`bmi_underweight`, etc.) still work
- No breaking changes

---

## Why This Change

1. **Key mismatch:** Contract uses `bmi.underweight` (dots), backend had `bmi_underweight` (underscores)
2. **normalize_lang conflict:** `ru`/`es` mapped to `en`, conflicting with product goal (RU/ES/EN iOS localization)

---

## Testing

- ✅ New keys exist in all languages
- ✅ `normalize_lang("ru-RU") == "ru"` (was `en`)
- ✅ `normalize_lang("es-ES") == "es"` (was `en`)
- ✅ Visualization keys map to translations without KeyError
- ✅ All existing tests pass (no regressions)

---

## Related

- Follow-up to PR-492 (BMI visualization contract)
- Enables iOS/Web to use backend translations for visualization ranges
- Part of Sprint D (i18n audit)

---

## Non-Goals

- ❌ Remove old underscore-keys (kept for backward compatibility)
- ❌ Refactor entire i18n system (only alignment)
```

---

## 🚀 Push & PR

```bash
# Push branch
git push -u origin feat/pr-d-i18n-alignment

# Open PR on GitHub
# Title: "feat(i18n): align backend i18n with BMI visualization contract"
# Labels: i18n, backend, refactoring
# Merge strategy: Squash and merge
```

---

## 📌 Notes

- **Backward compatible:** Old keys (`bmi_underweight`) still work
- **No breaking changes:** Existing code continues to work
- **Product-aligned:** `normalize_lang` now supports RU/ES/EN markets
- **Test coverage:** All new keys and policy changes are tested
- **Contract-first tests:** Tests use actual API endpoint (not internal functions)

---

## ⚠️ Important Notes

### 1. Test Uses API Endpoint (Contract-First)

All visualization key tests use the actual `/api/v1/bmi/calculate` endpoint instead of calling `get_bmi_visual_ranges` directly. This is more robust because:
- It matches what clients (iOS/Web) actually use
- It doesn't depend on internal function signatures
- It's truly contract-first

**Tests cover 3 groups:**
- `test_bmi_visualization_keys_map_to_translations_via_api_adult` — baseline adult group
- `test_bmi_visualization_keys_map_to_translations_via_api_athlete` — athlete group (different thresholds)
- `test_bmi_visualization_keys_map_to_translations_via_api_elderly` — elderly group (different thresholds)

**Payload guarantees (via `_valid_payload` helper):**
- `age=25` (adult, not teen/elderly) — ensures visualization is not null
- `pregnant="no"` (not pregnant) — avoids category=None group
- `athlete="no"` (baseline adult) or `athlete="yes"` (athlete) or `age=75` (elderly)
- Valid weight/height for normal BMI range

### 2. Tests Only Check Keys, Not Numbers

Sprint D is about i18n alignment, not BMI math. Tests verify:
- `ranges[].key` exists and is one of 4 expected keys: `{"bmi.underweight", "bmi.normal", "bmi.overweight", "bmi.obesity"}`
- `t(lang, key)` doesn't raise KeyError
- `t(lang, key)` returns non-empty translation
- Translation is not just the key itself (actual translation exists)

**Numbers (thresholds) are already tested in PR-492 contract tests.** This keeps Sprint D focused on i18n.

### 3. App Import Path (CI-Safe)

**Canonical import:** `from app import app`

This matches existing integration tests (e.g., `tests/test_bmi_contract_visualization.py`, `tests/test_bmi_visualization_spec.py`). The `app` package uses PEP 562 forwarding to `legacy_app.app`, so this import is safe and consistent with project conventions.

### 4. LANG_ALIASES vs LOCALE_SPECIAL_CASES

**Important:** `LANG_ALIASES` (Step 1) always wins over `LOCALE_SPECIAL_CASES` (Step 2).

If someone later changes `LANG_ALIASES["es-es"] = "en"`, it will override `LOCALE_SPECIAL_CASES` policy. Keep this in mind for future changes.

**Current fix:** Both are updated to be consistent, but `LANG_ALIASES` takes precedence.

### 5. normalize_lang Tests Cover Edge Cases

Tests verify:
- Different cases: `"ru-RU"`, `"ru-ru"`, `"RU-RU"`, `"RU-ru"`
- Different separators: `"ru-RU"`, `"ru_RU"` (underscore normalized to dash)
- Base languages: `"ru"`, `"es"`, `"en"`
- Unknown languages fallback to `"en"`

This ensures robust language normalization regardless of input format (handles user input variations).

### 6. No Unused Imports

The test file uses:
- `from app import app` — FastAPI app instance
- `from fastapi.testclient import TestClient` — test client
- `from core.i18n import TRANSLATIONS, normalize_lang, t` — i18n functions
- `from typing import Any` — type hints

No `pytest` import needed (not using fixtures or marks in this file).

---

**Ready to implement!** Copy-paste the changes above in order (Commit 1 → Commit 2 → Commit 3).
