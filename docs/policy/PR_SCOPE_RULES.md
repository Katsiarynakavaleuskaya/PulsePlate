# PR Scope Rules (Runtime vs Docs Separation)

**Status:** Mandatory
**Last updated:** 2026-01-08 (after PR-494 analysis)
**Applies to:** All contributors, agents, CI reviewers

**CI Enforcement:** Runtime PRs that include planning docs or `docs/pr/*.py` will be blocked.

---

## 1. Core Principle: One Thought = One PR, One Merge = One PR

**Every PR must have a single, clear purpose.** If a PR tries to do multiple unrelated things, it will:
- Bloat to 60+ files (like PR-494)
- Drown in review comments
- Fail CI due to mixed concerns
- Become unreviewable

**Rules:**
- If you find yourself saying "and also..." in the PR description, split it.
- **Do not open the next PR until the current runtime PR is merged** (except hotfix CI by agreement).

---

## 2. Runtime PR Scope (Strict)

### ✅ Allowed in Runtime PR

**Code & Tests:**
- `*.py` files (app/, core/, tests/)
- Test files (`tests/**/*.py`)
- Supporting configs if directly required (e.g., `alembic.ini` changes for new migrations)

**Minimal Docs (only if contract/spec for this runtime change):**
- Maximum 1-2 `.md` files **only** if they define the contract/spec for this exact runtime change
- **Contract/spec md definition:** A document that describes external API/DTO/invariants/edge-cases for this specific change and serves as source of truth for clients (iOS/Web) or as a checklist for contract tests.
- Examples: `REQUEST_NORMALIZATION_SPEC.md` (if it's the spec for the normalization being implemented)
- **Not allowed:** roadmap, handoff, audit, review checklist, "ready" status files (these are planning artifacts, not contracts)

### ❌ Forbidden in Runtime PR

**Planning/Handoff Artifacts:**
- `docs/pr/PR_XXX_READY.md`
- `docs/pr/PR_XXX_ROADMAP.md`
- `docs/pr/PR_XXX_HANDOFF.md`
- `docs/pr/PR_XXX_AUDIT_REPORT.md`
- `docs/pr/PR_XXX_REVIEW_CHECKLIST.md` (unless it's the contract spec itself)

**Python "tests" in docs:**
- `docs/pr/*.py` (tests belong in `tests/`)

**Markdown lint fixes:**
- If a runtime PR includes 1-2 contract/spec `.md` files, markdownlint fixes are allowed **only within those contract/spec files**.
- If CodeRabbit complains about mdlint (MD040/034/036) in **unrelated** `.md` files → **remove the md file**, don't fix lint (it's a scope smell).

**Unrelated cleanup:**
- "While we're here" changes
- Formatting fixes for unrelated files
- Refactoring unrelated code

---

## 3. Docs-Only PR Scope (Strict)

See [`DOCS_ONLY_PR_POLICY.md`](./DOCS_ONLY_PR_POLICY.md) for full details.

**Summary:**
- ✅ Only `.md` files (+ images if needed)
- ❌ No runtime code, CI, infra, or behavior changes

---

## 4. Common Anti-Patterns (Lessons from PR-494)

### Anti-Pattern 1: Mixing Runtime + Planning Docs

**Bad:**
```text
PR-494:
- app/schemas/bmi.py (runtime)
- core/bmi/interpretation_models.py (runtime)
- docs/pr/PR_494_ROADMAP.md (planning)
- docs/pr/PR_494_REVIEW_CHECKLIST.md (planning)
- docs/pr/PR_494_AUDIT_REPORT.md (planning)
→ 60 files, unreviewable
```

**Good:**
```text
PR-495:
- app/schemas/bmi.py (runtime)
- tests/test_bmi_interpretation_validation.py (tests)
→ 2 files, reviewable
```

### Anti-Pattern 2: Schema ↔ Core ↔ Router Contract Mismatch

**Problem:** New response field added without closing the type contract.

**Example from PR-494:**
- `BMIInterpretationV1Schema.target_range` expects: `NumericRangeSchema | Literal["age_appropriate_growth", "prenatal_guidelines"] | None`
- Router passed: `NumericRangeSchema | str | None` (any string, not just literals)

**Rule:** Any new response field must have:
1. **Canonical type in core** (domain model)
2. **Explicit adapter in app** (with literal/enum validation)
3. **Tests that fail on any "leftover string"**

### Anti-Pattern 3: Legacy Typing/Serialization Issues

**Problem:** Helper functions declared as `-> dict[str, Any]` but return `Any`.

**Example:** `legacy_app._normalize_canonical_result` → mypy `warn_return_any` fails.

**Rule:** Legacy helpers must be **total functions**:
- Always return `dict[str, Any]` (never `Any`)
- Use `Mapping` + `cast` if needed
- Handle all edge cases explicitly

---

## 5. PR Size Guidelines

### Small PR (Ideal)
- **1-5 files changed**
- **<200 lines added/modified**
- Single, focused change
- Easy to review in 10-15 minutes

### Medium PR (Acceptable)
- **5-15 files changed**
- **200-500 lines added/modified**
- Related changes (e.g., feature + tests + minimal docs)
- Reviewable in 30-45 minutes
- **Hard gate:** Runtime PR must achieve **100% diff-coverage** on touched lines (CI enforced)

### Large PR (Warning Sign)
- **15-30 files changed**
- **500-1000 lines added/modified**
- **Action:** Review scope, consider splitting

### Bloat PR (Must Split)
- **30+ files changed**
- **1000+ lines added/modified**
- **Action:** **STOP** and split immediately

---

## 6. Enforcement Checklist (Before Opening PR)

**CI Guard:** The scope guard runs automatically in CI. See [`../../scripts/ci/pr_scope_guard.sh`](../../scripts/ci/pr_scope_guard.sh) for implementation.

Run this before opening any PR:

```bash
# 1. Check file count
git diff --name-only origin/main...HEAD | wc -l

# 2. Check for mixed concerns (runtime + docs)
git diff --name-only origin/main...HEAD | grep -E "\.md$" | wc -l
git diff --name-only origin/main...HEAD | grep -E "\.py$" | wc -l

# 3. Check for forbidden patterns (machine-checkable)
# Runtime PR must not contain planning docs
git diff --name-only origin/main...HEAD \
  | rg '^docs/pr/.*_(ROADMAP|HANDOFF|AUDIT|READY|SCOPE|SUMMARY|PLAN|PATCH|NOTES)\.md$' \
  && echo "BLOCK: planning docs in runtime PR" && exit 1 || true

# 4. Check for python files in docs/pr (forbidden always)
git diff --name-only origin/main...HEAD | rg '^docs/pr/.*\.py$' \
  && echo "BLOCK: python files under docs/pr" && exit 1 || true

# 5. Check diff size
git diff --stat origin/main...HEAD

# 6. Check diff-coverage (runtime PRs only)
# CI will enforce 100% diff-coverage on touched lines
```

**Red flags:**
- File count > 30 → **STOP, split PR**
- Both `.md` and `.py` files + `.md` count > 2 → **Review scope**
- Planning docs (`ROADMAP`, `HANDOFF`, etc.) in runtime PR → **Remove them**
- Diff-coverage < 100% on touched lines → **Add tests or reduce scope**

---

## 7. When CodeRabbit Complains About Markdown Lint

**If it's a runtime PR with contract/spec md:**
- Markdownlint fixes are allowed **only within the contract/spec md files** (they are part of the PR scope).

**If it's a runtime PR with unrelated md:**
- **Don't fix mdlint** (MD040/034/036) in unrelated files
- **Remove the unrelated md file** from the PR (or move it to a separate docs PR)

**Rationale:** Markdown lint in unrelated md files is a symptom of scope bloat, not a real issue to fix.

---

## 8. Contract Validation Rule

**For any new API response field:**

1. **Define canonical type in core:**
   ```python
   # core/bmi/interpretation_models.py
   QualitativeTarget = Literal["age_appropriate_growth", "prenatal_guidelines"]
   ```

2. **Create explicit adapter in app:**
   ```python
   # app/schemas/bmi.py
   TargetRangeSchema = NumericRangeSchema | QualitativeTarget | None
   ```

3. **Validate in router (fail on invalid strings):**
   ```python
   # app/routers/bmi.py
   if isinstance(target_range, str) and target_range not in ["age_appropriate_growth", "prenatal_guidelines"]:
       raise ValueError(f"Invalid target_range: {target_range}")
   ```

4. **Test edge cases:**
   ```python
   # tests/test_bmi_interpretation_validation.py
   def test_invalid_target_range_string_raises_error():
       # Should fail if router passes "random_string"
   ```

---

## 9. Relationship to Other Policies

- **Docs-only PRs:** See [`DOCS_ONLY_PR_POLICY.md`](./DOCS_ONLY_PR_POLICY.md)
- **Engineering lessons:** See [`../ENGINEERING_LESSONS.md`](../ENGINEERING_LESSONS.md)
- **Agent instructions:** See root [`AGENTS.md`](../../AGENTS.md)

---

## 10. Rationale

This policy exists because:
- **PR-494 failed** due to scope bloat (60 files, mixed concerns)
- **Review became impossible** (planning docs + runtime code)
- **CI failed** due to mixed concerns (mypy, mdlint, etc.)
- **Recovery required** splitting into 6 smaller PRs (PR-495, PR-496, etc.)

**This is not a stylistic guideline — it's an engineering safety rule.**

---

## 11. Quick Reference

| PR Type | Allowed Files | Max Files | Max Lines | Diff-Coverage |
|---------|--------------|-----------|-----------|---------------|
| Runtime | `.py` (app/core/tests) + 1-2 contract `.md` | 15 (target: Small/Medium) | 500 | 100% (hard gate) |
| Docs-only | `.md` only | 30 | 1000 | N/A |
| Mixed | ❌ **Forbidden** | - | - | - |

**If your PR doesn't fit these categories, split it.**
