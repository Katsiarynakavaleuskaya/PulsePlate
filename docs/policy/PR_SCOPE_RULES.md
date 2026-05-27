# PR Scope Rules (Runtime vs Docs Separation)

**Status:** Mandatory
**Last updated:** 2026-05-27 (tiered PR-scope policy for governance/design/frontend MVP lanes)
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

### Micro PR

- **≤5 files changed**
- No split justification required
- Examples: typo, single guard fix, small test repair

### Standard Governance / Design PR

- **≤20 files changed**
- Requires normal `Scope`, `Out of scope`, and `Tests` sections
- Requires `Split Justification` only when **>15 files**
- Same-PR closeout/mapping overhead is allowed when directly tied to the PR

### Frontend Vertical MVP PR

- **≤30 files changed**
- Requires explicit `Operator approval: approved` and `Frontend vertical MVP approval: approved` in the PR body
- Requires `Split Justification`
- Must remain one vertical user flow
- Must not mix frontend UI with backend/API/AI runtime unless `Frontend/backend mix approval: approved` or an emergency exception is documented

### Privileged CI / Security / Workflow PR

- Target **≤10 files changed**
- Hard cap **≤15 files changed** unless `Operator approval: approved` plus `Privileged scope exception: approved` is documented
- Requires security review and bug-hunter pass
- Cannot mix with frontend product implementation unless `Frontend/backend mix approval: approved` or an emergency exception is documented

The file-count guard enforces the privileged lane cap and mixed-scope boundary. The security review and bug-hunter proof are enforced by coordinator-owned PR lifecycle review, fixed mapping, and merge-readiness governance rather than by the file-count helper alone.

### Oversized PR

- **>30 files changed** fails closed
- Must split unless `Operator approval: approved` plus `Emergency exception: approved` is documented

---

## 6. Enforcement Checklist (Before Opening PR)

**CI Guards:** The scope guard job runs automatically in CI. [`../../scripts/ci/pr_scope_guard.sh`](../../scripts/ci/pr_scope_guard.sh) enforces forbidden `docs/pr` patterns; [`../../scripts/ci/check_pr_size_governance.py`](../../scripts/ci/check_pr_size_governance.py) enforces tiered file-count and approval policy.

Run this before opening any PR:

```bash
# 1. Check file count
git diff --name-only origin/main...HEAD | wc -l

# 2. Check for mixed concerns (runtime + docs)
git diff --name-only origin/main...HEAD | grep -E "\.md$" | wc -l
git diff --name-only origin/main...HEAD | grep -E "\.py$" | wc -l

# 3. Check for forbidden patterns (machine-checkable)
# Runtime PR must not contain planning docs (aligned with Section 2)
git diff --name-only origin/main...HEAD \
  | rg '^docs/pr/PR_[0-9]+_(READY|ROADMAP|HANDOFF|AUDIT_REPORT|REVIEW_CHECKLIST)\.md$' \
  && echo "BLOCK: planning docs in runtime PR" && exit 1 || true

# 4. Check for Python files in docs/pr (forbidden always)
git diff --name-only origin/main...HEAD | rg '^docs/pr/.*\.py$' \
  && echo "BLOCK: Python files under docs/pr" && exit 1 || true

# 5. Check diff size
git diff --stat origin/main...HEAD

# 6. Check diff-coverage (runtime PRs only)
# CI will enforce 100% diff-coverage on touched lines
```

**Red flags:**
- File count > 30 without an emergency/operator exception → **STOP, split PR**
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

| PR Type | Max Files | Required Proof | Enforcement |
|---------|-----------|----------------|-------------|
| Micro | ≤5 | No split justification; governance/security docs still need `Scope`, `Out of scope`, `Tests` | `check_pr_size_governance.py` |
| Standard governance/design | ≤20 | `Scope`, `Out of scope`, `Tests`; `Split Justification` if >15 files | `check_pr_size_governance.py` |
| Frontend vertical MVP | ≤30 | `Operator approval: approved`, `Frontend vertical MVP approval: approved`, `Split Justification`; add `Frontend/backend mix approval: approved` when frontend mixes with backend/API/AI runtime | `check_pr_size_governance.py` |
| Privileged CI/security/workflow | target ≤10, hard cap ≤15 | `Privileged scope exception: approved` if >15 files; role review proof via PR lifecycle | `check_pr_size_governance.py` + review governance |
| Oversized | >30 | Split, unless `Emergency exception: approved` with operator approval | `check_pr_size_governance.py` |

**If your PR doesn't fit these categories, split it or get an explicit operator-approved exception before opening review.**
