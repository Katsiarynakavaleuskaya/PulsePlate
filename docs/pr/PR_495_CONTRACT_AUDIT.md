# PR-495 Contract Audit: Schema ↔ Engine Gender Token Parity

**Date:** 2026-01-08
**Status:** Critical Gap Identified
**Action Required:** Fix exact token mismatch before merge

---

## Executive Summary

**Contract is NOT fully closed.** Engine recognizes `"w"` as female exact token, but schema does not. This violates the documented requirement "MUST stay in sync" and creates semantic drift risk.

---

## 1. Current State Analysis (Code Evidence)

### 1.1 Schema Exact Tokens

```python
# app/schemas/bmi.py:119-120
_MALE_EXACT: Final[set[str]] = {"male", "m", "man", "м"}
_FEMALE_EXACT: Final[set[str]] = {"female", "f", "woman", "ж"}
```

**Schema female exact tokens:** `{"female", "f", "woman", "ж"}` (4 tokens)

### 1.2 Engine Exact Tokens

```python
# core/bmi/engine.py:76
female_exact = {"female", "f", "woman", "w", "ж"}
```

**Engine female exact tokens:** `{"female", "f", "woman", "w", "ж"}` (5 tokens)

### 1.3 Mismatch Evidence

```python
# Proof: engine has "w", schema does not
schema_female = {"female", "f", "woman", "ж"}
engine_female = {"female", "f", "woman", "w", "ж"}

assert "w" in engine_female  # True
assert "w" in schema_female  # False ❌ MISMATCH
```

**Missing token:** `"w"` is recognized by engine but not by schema.

---

## 2. Impact Analysis

### 2.1 Behavioral Impact

**Scenario:** `gender="w"`, `pregnant=True`

**Schema behavior:**
```python
# app/schemas/bmi.py:150-162
def _is_female_gender_token(gender: str | None) -> bool:
    g = _normalize_ws_lower(gender)  # "w"
    if not g:
        return False
    return (g in _FEMALE_EXACT) or any(...)  # "w" not in {"female", "f", "woman", "ж"} → False
    # Returns False (not recognized as female)
```

**Engine behavior:**
```python
# core/bmi/engine.py:76-78
female_exact = {"female", "f", "woman", "w", "ж"}
if g in female_exact:  # "w" in female_exact → True
    return "female"
```

**Result:**
- Schema: `_is_female_gender_token("w")` → `False` (not female)
- Engine: `_normalize_gender("w")` → `"female"`

**Invariant check:**
```python
# app/schemas/bmi.py:281
if _is_male_gender_token(self.gender) and pregnant_bool:
    raise ValueError("Pregnancy is only applicable to females")
```

Since `_is_female_gender_token("w")` returns `False` and `_is_male_gender_token("w")` also returns `False` (not in `_MALE_EXACT`), the invariant check **passes** (no error raised).

**Downstream:**
- Router passes `gender="w"` to engine
- Engine normalizes to `"female"`
- Request succeeds with `group="pregnant"`

**Conclusion:** Request is **allowed** (schema doesn't block), but this is **semantic drift** — schema and engine disagree on token interpretation.

### 2.2 Contract Violation

**Documented requirement:**
```python
# app/schemas/bmi.py:114-117
# IMPORTANT: _MALE_EXACT and _FEMALE_EXACT MUST stay in sync with
# core/bmi/engine._normalize_gender() exact token sets.
```

**Current state:** Sets are **NOT in sync** (engine has `"w"`, schema does not).

**Comment is false:** The comment claims sync, but code proves otherwise.

---

## 3. Test Coverage Gaps

### 3.1 One-Way Parity Test

**Current test:**
```python
# tests/test_bmi_interpretation_validation.py:373-413
def test_schema_engine_exact_tokens_parity(self) -> None:
    # Test: all schema male tokens must be recognized as male by engine
    for token in schema_male_tokens:
        assert _normalize_gender(token) == "male"

    # Test: all schema female tokens must be recognized as female by engine
    for token in schema_female_tokens:
        assert _normalize_gender(token) == "female"
```

**Coverage:** Schema → Engine (one direction only)

**Missing:** Engine → Schema parity check

**Gap:** Test does not verify that engine exact tokens are **all** recognized by schema.

### 3.2 Incomplete 422 Coverage

**Current test:**
```python
# tests/test_bmi_interpretation_validation.py:354-371
def test_schema_engine_contract_parity_man_pregnant_blocks(self, client: TestClient):
    payload = {"gender": "man", "pregnant": True, ...}
    resp = client.post("/api/v1/bmi/calculate", json=payload)
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
```

**Coverage:** Only `"man"` is tested

**Missing:** Tests for `"m"`, `"м"`, `"male"` (other `_MALE_EXACT` tokens)

**Gap:** Not all male exact tokens are verified to trigger 422.

---

## 4. Root Cause Analysis

### 4.1 Why "w" Exists in Engine

**Historical context:**
- Engine was fixed in PR-495 to recognize `"woman"` and `"w"` as female
- Schema was updated to recognize `"woman"` but `"w"` was **missed**

**Evidence:**
```python
# core/bmi/engine.py:76 (after PR-495 fix)
female_exact = {"female", "f", "woman", "w", "ж"}  # "w" added

# app/schemas/bmi.py:120 (after PR-495 fix)
_FEMALE_EXACT: Final[set[str]] = {"female", "f", "woman", "ж"}  # "w" missing
```

**Conclusion:** Incomplete synchronization during PR-495 implementation.

### 4.2 Why Tests Didn't Catch It

**Test limitation:**
```python
# Current test only checks: schema tokens → engine recognition
# Does NOT check: engine tokens → schema recognition
```

**Missing assertion:**
```python
# Should exist but doesn't:
engine_female_tokens = {"female", "f", "woman", "w", "ж"}  # extracted from engine
schema_female_tokens = _FEMALE_EXACT  # {"female", "f", "woman", "ж"}
assert engine_female_tokens == schema_female_tokens  # Would fail: "w" missing
```

---

## 5. Recommended Fix (Minimal, Canonical)

### 5.1 Add "w" to Schema (Option A - Recommended)

**Change:**
```python
# app/schemas/bmi.py:120
_FEMALE_EXACT: Final[set[str]] = {"female", "f", "woman", "w", "ж"}
```

**Rationale:**
- Matches engine exactly
- Preserves backward compatibility (engine already accepts "w")
- Minimal change (1 token added)

### 5.2 Strengthen Parity Test (Bidirectional)

**Add to test:**
```python
def test_schema_engine_exact_tokens_parity(self) -> None:
    # ... existing one-way checks ...

    # NEW: Bidirectional parity check
    # Extract engine exact tokens (via reverse lookup or explicit set)
    # For now, use explicit contract spec
    CONTRACT_FEMALE_EXACT = {"female", "f", "woman", "w", "ж"}
    CONTRACT_MALE_EXACT = {"male", "m", "man", "м"}

    assert _FEMALE_EXACT == CONTRACT_FEMALE_EXACT, (
        f"Schema _FEMALE_EXACT must match contract. "
        f"Expected: {CONTRACT_FEMALE_EXACT}, Got: {_FEMALE_EXACT}"
    )

    # Verify engine recognizes all contract tokens
    for token in CONTRACT_FEMALE_EXACT:
        assert _normalize_gender(token) == "female"
```

### 5.3 Parameterize 422 Tests

**Add:**
```python
@pytest.mark.parametrize("male_token", ["male", "m", "man", "м"])
def test_all_male_exact_tokens_block_pregnant(self, client: TestClient, male_token: str):
    payload = {
        "weight_kg": 70.0, "height_cm": 175.0, "age": 30,
        "gender": male_token, "pregnant": True, "lang": "en",
    }
    resp = client.post("/api/v1/bmi/calculate", json=payload)
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
```

---

## 6. Risk Assessment

### 6.1 Current Risk Level: **Medium**

**Why not Critical:**
- Schema doesn't **block** valid requests (allows "w" + pregnant)
- Engine correctly processes "w" as female
- No runtime errors occur

**Why Medium:**
- Semantic drift (schema and engine disagree)
- Comment is false ("MUST stay in sync" violated)
- Future changes may amplify the mismatch

### 6.2 If Not Fixed

**Potential issues:**
1. **Future refactoring:** Developer sees comment "MUST stay in sync", assumes sets match, makes change based on schema only → breaks engine
2. **Test false confidence:** Parity test passes (one-way), but contract is not fully closed
3. **Documentation drift:** Comment becomes increasingly false over time

---

## 7. Action Items

1. ✅ **Add `"w"` to `_FEMALE_EXACT`** (1 line change)
2. ✅ **Strengthen parity test** (bidirectional check)
3. ✅ **Parameterize 422 tests** (cover all `_MALE_EXACT` tokens)
4. ✅ **Verify:** Run `test_schema_engine_exact_tokens_parity` → should pass
5. ✅ **Verify:** Run parameterized 422 tests → all should pass

**Estimated effort:** 15 minutes
**Risk:** Low (additive change only)
**Impact:** Closes contract gap completely

---

## 8. Force Push Issue (Separate Concern)

**Problem:** Used `git push --force-with-lease` during PR split attempt.

**Why this is wrong:**
- Force push rewrites remote history
- If PR is already open, force push breaks review context
- Other developers may have based work on old commits
- Violates collaborative workflow

**Correct approach:**
- Use regular `git push` for new commits
- If history needs cleanup, coordinate with team first
- For PR splits, create new branches from clean state

**Status:** Need to restore original PR branches and redo split cleanly.
