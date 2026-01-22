# Merge Conflict Safety Setup

**Date:** 2026-01-22
**Purpose:** Prevent pushing code with unresolved merge conflicts

---

## Three-Level Protection

### Level 1: Process Rule (AGENTS.md)

**Location:** `AGENTS.md` section "Merge Conflict Safety (Hard Rule)"

**What it does:**
- Documents mandatory checks before push
- Defines STOP condition (not warning)
- Guides agent behavior

**Enforcement:** Manual review + agent compliance

---

### Level 2: Pre-Push Hook (Technical Guard)

**Location:** `.githooks/pre-push`

**What it does:**
- Blocks `git push` if unmerged paths detected
- Blocks `git push` if conflict markers found
- Blocks `git push` if merge/rebase in progress
- Provides clear error messages

**Setup:**
```bash
# Hook is already in .githooks/pre-push
# Enable it:
git config core.hooksPath .githooks

# Verify:
git config --get core.hooksPath
# Should output: .githooks
```

**Test:**
```bash
# Should pass (no conflicts):
.githooks/pre-push

# Should output: "✅ No merge conflicts detected. Push allowed."
```

---

### Level 3: CI Guard (Last Line of Defense)

**Location:**
- `.github/workflows/ci.yml` (PR Scope Guard job)
- `.pre-commit-config.yaml` (enhanced merge conflict check)

**What it does:**
- CI step fails PR if conflict markers detected
- Pre-commit hook blocks commits with conflicts
- Pre-push hook blocks pushes with conflicts

**Enforcement:** Automatic (CI + pre-commit framework)

---

## Verification

### Local Setup

```bash
# 1. Enable git hooks
git config core.hooksPath .githooks

# 2. Test pre-push hook
.githooks/pre-push

# 3. Test pre-commit hook
pre-commit run check-merge-conflict-enhanced --all-files
```

### CI Verification

CI will automatically run merge conflict guard in PR Scope Guard job.

**Expected behavior:**
- ✅ PR with no conflicts: CI passes
- ❌ PR with conflict markers: CI fails with clear error

---

## How It Works

### Pre-Push Hook Flow

1. **Check unmerged paths:** `git ls-files -u`
   - If non-empty → block push

2. **Check conflict markers:** `git grep '<<<<<<< HEAD\|=======\|>>>>>>>'`
   - If found → block push

3. **Check merge/rebase state:** `.git/MERGE_HEAD`, `.git/REBASE_HEAD`, `.git/CHERRY_PICK_HEAD`
   - If exists → block push

### CI Guard Flow

1. **PR Scope Guard job runs early** (before tests)
2. **Checks for conflict markers** in all committed files
3. **Checks for unmerged paths** in git index
4. **Fails PR** if conflicts detected

### Pre-Commit Hook Flow

1. **Runs on `git commit`** (before commit is created)
2. **Checks for conflict markers** in staged files
3. **Checks for unmerged paths** in git index
4. **Blocks commit** if conflicts detected

---

## Troubleshooting

### "Push blocked: unresolved merge conflicts"

**Solution:**
1. Resolve conflicts in files listed
2. Run: `git add <resolved-files>`
3. Run: `git commit` (or `git rebase --continue` / `git merge --continue`)
4. Verify: `git status` shows clean working tree
5. Retry push

### "Push blocked: conflict markers found"

**Solution:**
1. Find files with markers: `git grep -n '<<<<<<< HEAD\|=======\|>>>>>>>'`
2. Edit files and remove markers
3. Run: `git add <files>`
4. Retry push

### "Push blocked: merge/rebase in progress"

**Solution:**
- **If conflicts resolved:** `git merge --continue` or `git rebase --continue`
- **If want to cancel:** `git merge --abort` or `git rebase --abort`

---

## Rationale

**Why three levels?**

1. **Level 1 (Process):** Guides agent behavior, prevents mistakes at source
2. **Level 2 (Technical):** Blocks push even if agent makes mistake
3. **Level 3 (CI):** Last defense before merge (catches anything that slipped through)

**Defense in depth:** Multiple layers ensure conflicts never reach `main`.

---

## References

- **AGENTS.md:** "Merge Conflict Safety (Hard Rule)" section
- **Pre-push hook:** `.githooks/pre-push`
- **CI guard:** `.github/workflows/ci.yml` (PR Scope Guard job)
- **Pre-commit hook:** `.pre-commit-config.yaml` (check-merge-conflict-enhanced)

---

**Last updated:** 2026-01-22
