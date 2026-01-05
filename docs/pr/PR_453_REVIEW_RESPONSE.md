# PR-453 Review Response

## ✅ Addressed Review Comments

### 1. `waist_risk` Type Safety

**Changed:** `waist_risk: dict[str, Any] | None` → `waist_risk: WaistRiskResultSchema | None`

**Rationale:**
- Structure of `WaistRiskResult` is stable and domain-fixed
- Pydantic schema provides strict typing without coupling to domain dataclass
- Domain layer (`core/bmi/risk.py`) remains unchanged (dataclass)
- API layer gets proper validation and OpenAPI documentation

**Implementation:**
- Added `WaistRiskResultSchema` as separate API schema
- Endpoint will serialize domain dataclass → Pydantic schema (in PR-454)
- JSON output remains identical, but contract is now type-safe

---

### 2. `category=None` Description Clarification

**Changed:** Description now explicitly references `age_band` values instead of age ranges

**Rationale:**
- Synchronizes with `age_band` field semantics
- Avoids confusion between age ranges and age bands
- Medical disclaimer is clearer: applies to specific age bands, not just "<12 years"

**New description:**
> "None for users in 'pregnant', 'too_young', 'child' or 'teen' age bands - not an error, medical disclaimer."

---

### 3. Negative Test for `age_band`

**Added:** `test_invalid_age_band_raises_validation_error()`

**Rationale:**
- Strengthens `Literal` type contract enforcement
- Defensive testing for invalid enum values
- Ensures Pydantic validation works as expected

---

### 4. `notes` Default Factory Test

**Enhanced:** `test_notes_default_factory()` now checks for independent instances

**Rationale:**
- Verifies `default_factory=list` creates separate lists per instance
- Prevents shared mutable default bug
- Textbook best practice for Pydantic `default_factory`

**Test now verifies:**
- Two instances have independent empty lists
- Mutating one instance doesn't affect the other

---

### 5. Markdown Formatting

**Fixed:** `PR_453_COMMIT_3_SCHEMAS.md`
- Added language tag to fenced code block (`text`)
- Changed bold heading to proper markdown heading

---

### 6. Canonical Handoff Document

**Added:** `docs/BMI_CANONICAL_HANDOFF.md`

**Purpose:**
- Single source of truth for BMI canonical track
- Documents invariants and roadmap
- Reference for future PRs and agents

---

## ❌ Intentionally Not Changed

### `gender` and `group` as `Literal`/`Enum`

**Decision:** Keep as `str` at API layer

**Rationale:**
1. **`group`** is domain output, not user input
   - Produced by `auto_group()` in engine
   - Enum would create API coupling to domain logic
   - Future groups (rehab, post_partum, metabolic) would require API changes

2. **`gender`** normalization belongs in engine/adapter
   - Accepts various string formats (normalized in engine)
   - Enum would restrict client flexibility unnecessarily

3. **Contract is already protected:**
   - Engine is single source of truth
   - Golden tests will catch divergences
   - Type safety achieved through engine validation

**Response to bot:**
> We intentionally keep `group` as a free string, as it is produced by the domain engine and may evolve. Enumerating it at the API layer would create unnecessary coupling and future-breaking changes. The contract is protected by the engine (single source of truth) and golden tests.

---

## Summary

All actionable review comments have been addressed:
- ✅ Type safety improved (`WaistRiskResultSchema`)
- ✅ Documentation clarified (`category=None`)
- ✅ Test coverage strengthened (negative cases, default factory)
- ✅ Markdown formatting fixed
- ✅ Canonical reference document added

**Test count:** 27 tests (up from 26), all passing ✅
