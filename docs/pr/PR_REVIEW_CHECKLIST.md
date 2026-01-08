# PR Review Checklist (Quick Scope Analysis)

**Purpose:** 2-minute check to detect if a PR is starting to bloat/drift (like PR-494).

**When to use:** Before opening PR, during review, or when PR grows unexpectedly.

---

## 1. File Count Check (30 seconds)

```bash
git diff --name-only origin/main...HEAD | wc -l
```

**Interpretation:**
- ✅ **1-15 files:** Good scope
- ⚠️ **15-30 files:** Review scope (might be OK if all related)
- 🛑 **30+ files:** **STOP** — PR is bloated, must split

---

## 2. Mixed Concerns Check (30 seconds)

```bash
# Count runtime files
git diff --name-only origin/main...HEAD | grep -E "\.py$" | wc -l

# Count docs files
git diff --name-only origin/main...HEAD | grep -E "\.md$" | wc -l

# Check for planning artifacts
git diff --name-only origin/main...HEAD | grep -E "docs/pr/.*_(ROADMAP|HANDOFF|AUDIT|READY|REVIEW_CHECKLIST)" || echo "OK"
```

**Interpretation:**
- ✅ **Runtime PR:** `.py` files + 0-2 contract `.md` files
- ⚠️ **Runtime PR with planning docs:** Remove planning docs (ROADMAP, HANDOFF, etc.)
- 🛑 **Mixed PR:** Runtime + planning docs → **Split into separate PRs**

---

## 3. Diff Size Check (30 seconds)

```bash
git diff --stat origin/main...HEAD
```

**Interpretation:**
- ✅ **<500 lines:** Good scope
- ⚠️ **500-1000 lines:** Review scope (might be OK if focused)
- 🛑 **1000+ lines:** **STOP** — PR is too large, must split

---

## 4. Scope Drift Check (30 seconds)

**Questions:**
1. **Does PR description say "and also..."?** → Split
2. **Are there unrelated "cleanup" commits?** → Remove them
3. **Are there "while we're here" changes?** → Remove them
4. **Are there markdown lint fixes in runtime PR?** → If in contract/spec md, OK; if in unrelated md, remove file

---

## 5. Contract Validation Check (Runtime PRs only)

**For new API response fields:**

```bash
# Check if new field has:
# 1. Canonical type in core
rg -n "QualitativeTarget|TargetRange" core/

# 2. Explicit adapter in app
rg -n "TargetRangeSchema" app/schemas/

# 3. Router validation
rg -n "target_range.*str" app/routers/

# 4. Edge case tests
rg -n "invalid.*target_range|target_range.*invalid" tests/
```

**Interpretation:**
- ✅ **All 4 present:** Good contract validation
- ⚠️ **Missing 1-2:** Add missing pieces before merge
- 🛑 **Missing 3-4:** **STOP** — contract not closed, will cause runtime bugs

---

## 6. Legacy Typing Check (If touching legacy code)

```bash
# Check for functions declared as -> dict[str, Any] but returning Any
rg -n "-> dict\[str, Any\]" legacy_app.py
rg -n "return.*Any" legacy_app.py
```

**Interpretation:**
- ✅ **All returns are dict:** Good
- ⚠️ **Some returns are Any:** Fix with Mapping + cast
- 🛑 **Mypy fails on warn_return_any:** **STOP** — fix typing before merge

---

## 7. CodeRabbit Markdown Lint Check

**If CodeRabbit complains about mdlint (MD040/034/036) in runtime PR:**

- ❌ **Don't fix mdlint**
- ✅ **Remove the md file** from PR (or move to separate docs PR)

**Rationale:** Markdown lint in runtime PRs = symptom of scope bloat.

---

## 8. Quick Decision Tree

```
Is file count > 30?
├─ YES → 🛑 STOP, split PR
└─ NO → Continue

Is there runtime code + planning docs?
├─ YES → 🛑 Remove planning docs, split if needed
└─ NO → Continue

Is diff > 1000 lines?
├─ YES → ⚠️ Review scope, consider splitting
└─ NO → Continue

Does PR description say "and also..."?
├─ YES → 🛑 Split PR
└─ NO → ✅ Good scope
```

---

## 9. Red Flags Summary

**Immediate STOP signals:**
- 🛑 File count > 30
- 🛑 Runtime PR contains planning docs (ROADMAP, HANDOFF, AUDIT, READY)
- 🛑 PR description says "and also..."
- 🛑 Contract validation missing (new API field without core type + adapter + tests)
- 🛑 Legacy typing issues (mypy warn_return_any fails)

**Warning signs (review scope):**
- ⚠️ File count 15-30
- ⚠️ Diff 500-1000 lines
- ⚠️ Unrelated cleanup commits
- ⚠️ Markdown lint fixes in unrelated md (contract/spec md fixes are OK)
- ⚠️ Diff-coverage < 100% on touched lines

---

## 10. Recovery Actions

**If PR is bloated:**

1. **Archive current branch:**
   ```bash
   git checkout -b archive/pr-XXX-snapshot
   git push -u origin archive/pr-XXX-snapshot
   ```

2. **Start fresh from main:**
   ```bash
   git checkout main
   git pull
   git checkout -b feat/pr-YYY-focused-scope
   ```

3. **Cherry-pick only relevant files:**
   ```bash
   git checkout archive/pr-XXX-snapshot -- path/to/relevant/file.py
   ```

4. **Commit and push:**
   ```bash
   git add path/to/relevant/file.py
   git commit -m "feat(scope): focused change only"
   git push -u origin feat/pr-YYY-focused-scope
   ```

---

## 11. Reference

- **PR Scope Rules:** [`../policy/PR_SCOPE_RULES.md`](../policy/PR_SCOPE_RULES.md)
- **Docs-only Policy:** [`../policy/DOCS_ONLY_PR_POLICY.md`](../policy/DOCS_ONLY_PR_POLICY.md)
- **Engineering Lessons:** [`../ENGINEERING_LESSONS.md`](../ENGINEERING_LESSONS.md)

---

**Remember:** One thought = one PR. If you're unsure, split it.
