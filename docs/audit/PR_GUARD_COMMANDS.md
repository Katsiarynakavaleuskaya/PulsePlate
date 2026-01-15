# Commands for Guard Policy PR

**Branch:** `feat/bmi-canonical-guards`
**Status:** Draft PR (Expected CI Red)

---

## 🚀 Commands (Copy-Paste Ready)

```bash
# 1. Create branch
git checkout -b feat/bmi-canonical-guards

# 2. Stage files
git add tests/test_bmi_canonical_guard.py
git add docs/audit/PR_GUARD_POLICY_SKELETON.md
git add docs/audit/PR_GUARD_POLICY_LOCAL_TEST_RESULTS.md
git add docs/audit/PR_GUARD_POLICY_GITHUB_DESCRIPTION.md
git add AGENTS.md
git add docs/audit/DECISION_LOG_BMI_UNDEFINED.md

# 3. Run pre-commit (mandatory)
pre-commit run --all-files

# 4. Check status
git status

# 5. Commit
git commit -m "feat(tests): add BMI canonical guard tests (P0)

Add guard tests to enforce invariant:
'One BMI Engine must be the sole calculation path.'

Expected status: CI RED until backend remediation lands.
DO NOT MERGE this PR until guards pass.

See: docs/audit/PR_GUARD_POLICY_SKELETON.md
See: docs/audit/PR_GUARD_POLICY_LOCAL_TEST_RESULTS.md"

# 6. Push
git push -u origin feat/bmi-canonical-guards
```

---

## 📋 PR Checklist

After pushing:

- [ ] Open Draft PR on GitHub
- [ ] Use title: `feat(tests): add BMI canonical guard tests (P0)`
- [ ] Mark as **Draft**
- [ ] Copy description from `docs/audit/PR_GUARD_POLICY_GITHUB_DESCRIPTION.md`
- [ ] Add label: `P0` (if exists)
- [ ] Add label: `tests` (if exists)
- [ ] Add comment: "Expected CI red — this is by design. See PR description."

---

## ✅ Verification

After PR is open:

- [ ] CI runs guard tests
- [ ] CI fails (expected — 4 failures)
- [ ] PR remains Draft
- [ ] No merge attempts

---

**Last updated:** 2026-01-15
