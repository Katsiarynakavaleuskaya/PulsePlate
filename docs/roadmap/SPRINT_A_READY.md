# Sprint A: Ready to Start

## ✅ Prerequisites Complete

- ✅ PR-490B: Merged (BMI visualization group-aware)
- ✅ PR-491: Merged (test reorganization)
- ✅ PR-487: Merged (urllib3 2.6.2 → 2.6.3)
- ✅ Local main updated
- ✅ All tests passing

---

## 🎯 Next PR: PR-492

**Goal:** Verify urllib3 2.6.3 in Docker image and add guard checks.

**Status:** Ready to start

**See:** `docs/roadmap/SPRINT_A_PR_492_PLAN.md` for detailed plan

---

## Quick Verification

### Check Current State

```bash
# Verify requirements have urllib3 2.6.3
grep urllib3 requirements-dev.txt
# Expected: urllib3==2.6.3

# Verify merge commits
git log --oneline -n 5
# Should see PR-487 and PR-491 merge commits

# Run tests
pytest -q
# Should all pass
```

---

## Next Steps

1. **Create branch for PR-492:**
   ```bash
   git checkout -b chore/pr-492-verify-urllib3-docker
   ```

2. **Follow plan in:** `docs/roadmap/SPRINT_A_PR_492_PLAN.md`

3. **Start with Phase 1:** Quick verification (30 min)

---

## Notes

- Local environment may still have urllib3 2.6.2 (needs `pip install -r requirements-lock.txt`)
- Docker image verification is the key goal
- CI guard check is optional but recommended
