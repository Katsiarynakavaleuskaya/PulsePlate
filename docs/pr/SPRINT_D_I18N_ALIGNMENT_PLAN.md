# Sprint D: Backend i18n Alignment Plan

## Summary

**Problem:** BMI visualization contract uses dot-keys (`bmi.underweight`), but backend i18n uses underscore-keys (`bmi_underweight`). Also, `normalize_lang` maps `ru`/`es` to `en`, conflicting with product goals.

**Goal:** Align backend i18n with visualization contract without breaking existing code.

**Type:** Backend refactoring (i18n)  
**Priority:** After Sprint C.1/C.2 (iOS bootstrap first)

---

## 🔍 Problem Analysis

### A) Key Mismatch

**Contract (from PR-492):**
- `bmi.underweight`
- `bmi.normal`
- `bmi.overweight`
- `bmi.obesity`

**Current backend (`core/i18n.py`):**
- `bmi_underweight`
- `bmi_normal`
- `bmi_overweight`
- `bmi_obese_1`, `bmi_obese_2`, `bmi_obese_3`

**Impact:** iOS/Web will receive `ranges[].key = "bmi.underweight"` but won't find translation in `TRANSLATIONS`.

### B) normalize_lang Policy Conflict

**Current behavior:**
- `ru` → `en` (default)
- `es` → `en` (except `mx`)

**Product goal:** RU/ES/EN localization for iOS.

**Impact:** iOS strings will be "dead" if backend always returns EN.

---

## 🎯 Solution Strategy

### Phase 1: Add New Keys (Backward Compatible)

1. **Add dot-keys to `TRANSLATIONS`:**
   - `bmi.underweight` → RU: "Недостаточная масса", EN: "Underweight", ES: "Bajo peso"
   - `bmi.normal` → RU: "Норма", EN: "Normal", ES: "Normal"
   - `bmi.overweight` → RU: "Избыточная масса", EN: "Overweight", ES: "Sobrepeso"
   - `bmi.obesity` → RU: "Ожирение", EN: "Obesity", ES: "Obesidad"

2. **Keep old keys** (`bmi_underweight`, etc.) for backward compatibility.

3. **Translation note:** For visualization scale labels, use short "Normal" (not "Normal weight") to keep UI compact.

### Phase 2: Fix normalize_lang Policy

**New policy:**
- `ru-RU` → `ru`
- `es-ES` → `es` (Spain priority, not Mexico)
- `en-US`, `en-GB` → `en`
- Unknown → `en` (fallback)

**Remove:**
- ❌ `ru` → `en` default
- ❌ `es` → `en` default (except MX)

### Phase 3: Helper for Key Resolution (Optional)

Add helper to resolve keys with fallback:
- Try dot-key first (`bmi.underweight`)
- If not found, try underscore-key (`bmi_underweight`)
- This allows gradual migration without breaking existing code.

---

## 📋 Implementation Plan

### Step 1: Add New Keys to TRANSLATIONS

**File:** `core/i18n.py`

**Add to each language dict:**

```python
TRANSLATIONS = {
    "ru": {
        # ... existing keys ...
        # BMI Visualization (dot-keys for contract)
        "bmi.underweight": "Недостаточная масса",
        "bmi.normal": "Норма",
        "bmi.overweight": "Избыточная масса",
        "bmi.obesity": "Ожирение",
    },
    "en": {
        # ... existing keys ...
        "bmi.underweight": "Underweight",
        "bmi.normal": "Normal",  # Short for scale label
        "bmi.overweight": "Overweight",
        "bmi.obesity": "Obesity",
    },
    "es": {
        # ... existing keys ...
        "bmi.underweight": "Bajo peso",
        "bmi.normal": "Normal",
        "bmi.overweight": "Sobrepeso",
        "bmi.obesity": "Obesidad",
    },
}
```

**Note:** Keep `bmi_normal = "Normal weight"` for general text, use `bmi.normal = "Normal"` for visualization scale.

### Step 2: Fix normalize_lang

**File:** `core/i18n.py`

**Current (problematic):**
```python
LOCALE_SPECIAL_CASES = {
    "ru": {"default": "en"},  # ❌ Always EN
    "es": {"default": "en", "exceptions": {"mx"}},  # ❌ EN except MX
}
```

**New (product-aligned):**
```python
LOCALE_SPECIAL_CASES = {
    # Remove ru/es defaults - let them map to themselves
    # Only keep special cases if needed (e.g., es-MX → es)
}
```

**Update `normalize_lang` logic:**
- `ru-RU`, `ru` → `ru`
- `es-ES`, `es` → `es`
- `es-MX` → `es` (if needed, or keep as `es`)
- Unknown → `en` (fallback)

### Step 3: Add Helper for Key Resolution (Optional)

**File:** `core/i18n.py`

```python
def t_with_fallback(lang: Language, key: str, fallback_key: str | None = None) -> str:
    """
    RU: Перевод с fallback на альтернативный ключ.
    EN: Translation with fallback to alternative key.
    
    Args:
        lang: Language code
        key: Primary key (e.g., "bmi.underweight")
        fallback_key: Alternative key if primary not found (e.g., "bmi_underweight")
    
    Returns:
        Translated string or key if not found
    """
    try:
        return t(lang, key)
    except KeyError:
        if fallback_key:
            try:
                return t(lang, fallback_key)
            except KeyError:
                pass
        # Safe fallback: return key itself
        return key
```

**Usage:** Only if needed for gradual migration. Otherwise, just use new dot-keys directly.

---

## 🧪 Tests

### Test 1: New Keys Exist in All Languages

```python
def test_bmi_visualization_keys_exist_in_all_langs() -> None:
    """RU: Все ключи visualization присутствуют во всех языках."""
    keys = ["bmi.underweight", "bmi.normal", "bmi.overweight", "bmi.obesity"]
    for lang in ["ru", "en", "es"]:
        for key in keys:
            assert key in TRANSLATIONS[lang], f"Missing {key} in {lang}"
            assert TRANSLATIONS[lang][key], f"Empty {key} in {lang}"
```

### Test 2: normalize_lang Maps Correctly

```python
def test_normalize_lang_ru_es_maps_to_self() -> None:
    """RU: ru-RU и es-ES мапятся на себя, не на en."""
    assert normalize_lang("ru-RU") == "ru"
    assert normalize_lang("ru") == "ru"
    assert normalize_lang("es-ES") == "es"
    assert normalize_lang("es") == "es"
    assert normalize_lang("es-MX") == "es"  # Or keep as es
    assert normalize_lang("unknown") == "en"  # Fallback
```

### Test 3: Visualization Keys Map Correctly (Contract Test)

```python
def test_bmi_visualization_keys_map_to_translations() -> None:
    """RU: Ключи из visualization ranges мапятся на переводы без KeyError."""
    from core.bmi.engine import get_bmi_visual_ranges
    
    ranges_data = get_bmi_visual_ranges("general", "adult", 0.0, 60.0)
    assert ranges_data is not None
    
    for _, _, i18n_key in ranges_data:
        # Should not raise KeyError
        for lang in ["ru", "en", "es"]:
            translation = t(lang, i18n_key)
            assert translation, f"Empty translation for {i18n_key} in {lang}"
```

---

## 📝 Commit Strategy

1. **Commit 1:** `feat(i18n): add BMI visualization dot-keys (bmi.underweight, etc.)`
   - Add new keys to all languages
   - Keep old keys for backward compatibility

2. **Commit 2:** `fix(i18n): normalize_lang maps ru/es to themselves, not en`
   - Update `normalize_lang` logic
   - Remove problematic defaults

3. **Commit 3:** `test(i18n): add tests for visualization keys and normalize_lang`
   - Add tests from above

---

## 🔒 Security Notes

- Current `t()` raises `KeyError` with key/lang in message. In production, log safely, return "translation missing" to client.
- Keep i18n changes separate from deps/security PRs.

---

## ✅ Acceptance Criteria

- [ ] All 4 dot-keys exist in RU/EN/ES
- [ ] `normalize_lang("ru-RU") == "ru"`
- [ ] `normalize_lang("es-ES") == "es"`
- [ ] Old keys still work (backward compatibility)
- [ ] Tests pass
- [ ] No KeyError for visualization keys

---

## 📌 Non-Goals

- ❌ Remove old underscore-keys (keep for backward compatibility)
- ❌ Refactor entire i18n system (only alignment)
- ❌ Change other translation keys

---

## 🔗 Related

- Follow-up to PR-492 (BMI visualization contract)
- Enables iOS/Web to use backend translations for visualization ranges
- Part of Sprint D (i18n audit)

---

## ⏰ Timing

**Do this AFTER:**
- ✅ Sprint C.1 (iOS-only keys) — merged
- ✅ Sprint C.2 (iOS BMI bootstrap) — merged

**Reason:** Don't block iOS bootstrap with backend refactoring.

