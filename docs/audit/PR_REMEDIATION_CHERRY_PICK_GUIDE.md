# Cherry-Pick Guide for Remediation PR (Strategy B)

**Purpose:** Step-by-step guide to cherry-pick guard commit from PR #534 into remediation PR.

**Strategy:** Keep `main` green by including guards + fixes in single green PR.

---

## Step 1: Get Guard Commit SHA from PR #534

**Guard commit SHA:** `7b2be9e53fc294874ad20e2e13395ec61ed2c102`

**To verify:**
```bash
# View commits in PR #534
gh pr view 534 --json commits --jq '.commits[] | "\(.oid) - \(.messageHeadline)"'

# Guard commit should be:
# 7b2be9e53fc294874ad20e2e13395ec61ed2c102 - feat(tests): add BMI canonical guard tests (P0)
```

**Commit message:**
```
feat(tests): add BMI canonical guard tests (P0)
```

**This commit includes:**
- `tests/test_bmi_canonical_guard.py` (guard tests)
- `AGENTS.md` (BMI Engine Invariant rule)
- `docs/audit/DECISION_LOG_BMI_UNDEFINED.md`
- `docs/audit/PR_GUARD_POLICY_*.md` (documentation)

---

## Step 2: Create Remediation Branch from Main

```bash
# Ensure you're on latest main
git fetch origin
git checkout main
git pull origin main

# Create remediation branch
git checkout -b fix/bmi-p0-remediation origin/main
```

---

## Step 3: Cherry-Pick Guard Commit

```bash
# Cherry-pick guard commit from PR #534
# -x flag: stop on any conflict (don't continue in semi-conflicted state)
git cherry-pick -x 7b2be9e53fc294874ad20e2e13395ec61ed2c102
```

**If cherry-pick succeeds:** Continue to Step 4.

**If cherry-pick has conflicts:** See Troubleshooting section below.

**If cherry-pick has conflicts:**
- Resolve conflicts (usually in `AGENTS.md` if main has other changes)
- `git add <resolved_files>`
- `git cherry-pick --continue`

**Expected result:**
- Guard tests are now in branch
- Guards will be **red** (expected — violations exist)
- AGENTS.md rule is included

---

## Step 4: Verify Guards Are Red (Expected)

```bash
# Run guard tests (should fail as expected)
pytest tests/test_bmi_canonical_guard.py -v

# Expected output:
# FAILED test_no_legacy_bmi_imports_in_core_bmi
# FAILED test_single_canonical_extras_module
# FAILED test_engine_metadata_accuracy
# FAILED test_no_bmi_calculation_outside_engine
# PASSED test_bmi_result_structure_consistency
```

**If all guards pass immediately:** Something is wrong — guards should fail until remediation.

---

## Step 5: Apply Remediation Patches

Now apply patches from `PR_REMEDIATION_EXACT_PATCHES.md` sequentially.

**After each patch:**
1. Verify specific guard turns green
2. Run pre-commit
3. Commit

**Example sequence:**

```bash
# Patch 1: Remove legacy dependency
# ... apply patch ...
pytest tests/test_bmi_canonical_guard.py::test_no_legacy_bmi_imports_in_core_bmi -v
pre-commit run --all-files
git commit -m "fix(core): remove legacy BMI dependency from risk path (P0)"

# Patch 2: Fix engine metadata
# ... apply patch ...
pytest tests/test_bmi_canonical_guard.py::test_engine_metadata_accuracy -v
pre-commit run --all-files
git commit -m "docs(bmi): mark core/bmi/engine as canonical (remove stub metadata)"

# Patch 3: Consolidate extras
# ... apply patch ...
pytest tests/test_bmi_canonical_guard.py::test_single_canonical_extras_module -v
pre-commit run --all-files
git commit -m "refactor(bmi): consolidate bmi_extras modules into single canonical module (P0)"

# Patch 4: Remove local BMI calculations
# ... apply patches 3 and 4 ...
pytest tests/test_bmi_canonical_guard.py::test_no_bmi_calculation_outside_engine -v
pre-commit run --all-files
git commit -m "fix(bmi): delegate pro bmi route to canonical engine (no local calc)"
```

---

## Step 6: Final Verification (All Guards Green)

```bash
# All guards must pass
pytest tests/test_bmi_canonical_guard.py -v

# Expected output:
# PASSED test_no_legacy_bmi_imports_in_core_bmi
# PASSED test_single_canonical_extras_module
# PASSED test_engine_metadata_accuracy
# PASSED test_no_bmi_calculation_outside_engine
# PASSED test_bmi_result_structure_consistency

# Full test suite
make verify

# Pre-commit (must pass)
pre-commit run --all-files
```

---

## Step 7: Push and Create PR

```bash
# Push branch
git push -u origin fix/bmi-p0-remediation

# Create PR
gh pr create \
  --title "fix(bmi): restore One BMI Engine invariant (P0 remediation)" \
  --body-file docs/audit/PR_REMEDIATION_SKELETON.md \
  --base main
```

**PR should be GREEN** (all guards pass, all tests pass).

---

## Step 8: After Merge — Close PR #534

```bash
# Add comment to PR #534
gh pr comment 534 --body "✅ Superseded by PR-XXX (remediation). Guards are now green in main. Closing as superseded."

# Close PR #534
gh pr close 534
```

**Or manually on GitHub:**
- Add comment: "Superseded by PR-XXX"
- Close PR with reason: "Superseded"

---

## Troubleshooting

### Cherry-pick fails with conflicts

**View conflicting files:**
```bash
git status
```

**If conflicts in `AGENTS.md`:**
- Main may have other changes
- Resolve by keeping both changes (guard rule + other rules)
- Verify: `grep -A 5 "Pre-commit and \"expected red\"" AGENTS.md`
- After resolving: `git add AGENTS.md && git cherry-pick --continue`

**If conflicts in test files:**
- Should not happen if main doesn't have guard tests
- If it does: resolve by keeping guard test version
- After resolving: `git add <files> && git cherry-pick --continue`

**To abort cherry-pick completely:**
```bash
git cherry-pick --abort
```

### Guards pass immediately after cherry-pick

**Possible causes:**
1. Wrong commit SHA (picked wrong commit)
2. Violations already fixed in main (unlikely)
3. Guard tests not running correctly

**Fix:**
- Verify commit SHA: `git log --oneline -1`
- Check guard test file exists: `ls tests/test_bmi_canonical_guard.py`
- Run guards manually: `pytest tests/test_bmi_canonical_guard.py -v`

### Pre-commit fails after cherry-pick

**If pre-commit fails on guard tests:**
- This is expected if guards are red
- **But:** Remediation PR should make guards green before merge
- If guards are still red, apply remediation patches first

**If pre-commit fails on formatting/lint:**
- Fix formatting: `black .` or `ruff check --fix .`
- Re-run: `pre-commit run --all-files`
- Commit fixes

---

## Success Criteria

**Remediation PR is ready when:**

- [x] Guard commit cherry-picked successfully
- [x] All 5 guard tests pass
- [x] `make verify` passes
- [x] Pre-commit passes
- [x] CI is green
- [x] PR description references PR #534 as superseded

---

**Last updated:** 2026-01-15
**Status:** Ready for execution (Strategy B)
