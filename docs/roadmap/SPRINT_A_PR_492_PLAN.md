# Sprint A: PR-492 Plan — Verify urllib3 2.6.3 in Docker Image

## Goal

Ensure that Docker image actually uses urllib3 2.6.3 after PR-487 merge, and add guard checks to prevent dependency drift.

---

## Problem

After merging PR-487 (urllib3 2.6.2 → 2.6.3), we need to:
1. Verify that Docker image contains the updated version
2. Prevent future dependency version mismatches between requirements and Docker image

---

## Tasks

### Task 1: Verify urllib3 Version in Docker Image

**Steps:**
1. Build Docker image after PR-487 merge
2. Check urllib3 version inside container:
   ```bash
   docker run <image> python -c "import urllib3; print(urllib3.__version__)"
   ```
3. Verify it's 2.6.3 (not 2.6.2)

**Expected Result:**
- Docker image contains urllib3 2.6.3 ✅

---

### Task 2: Add Dockerfile Dependency Check

**Option A: Add to Dockerfile (explicit check)**

```dockerfile
# Verify critical dependencies match requirements-lock.txt
RUN python -c "import urllib3; assert urllib3.__version__ == '2.6.3', f'Expected urllib3 2.6.3, got {urllib3.__version__}'"
```

**Option B: Add to CI (separate check step)**

```yaml
- name: Verify dependencies in image
  run: |
    docker build -t test-image .
    docker run test-image python -c "import urllib3; assert urllib3.__version__ == '2.6.3'"
```

**Recommendation:** Option B (CI check) — doesn't bloat Dockerfile, easier to maintain.

---

### Task 3: (Optional) Add CI Guard for Dependency Consistency

**Goal:** Prevent dependency version mismatches between:
- `requirements-lock.txt`
- Docker image
- Runtime environment

**Approach:**

1. **Extract versions from lock file:**
   ```python
   # scripts/verify_docker_deps.py
   import re
   from pathlib import Path
   
   def get_urllib3_version_from_lock():
       lock_file = Path("requirements-lock.txt")
       content = lock_file.read_text()
       match = re.search(r"urllib3==(\d+\.\d+\.\d+)", content)
       return match.group(1) if match else None
   ```

2. **Check Docker image:**
   ```python
   import subprocess
   
   def check_docker_image_version(expected_version):
       result = subprocess.run(
           ["docker", "run", "--rm", "test-image", 
            "python", "-c", f"import urllib3; print(urllib3.__version__)"],
           capture_output=True, text=True
       )
       actual_version = result.stdout.strip()
       assert actual_version == expected_version, \
           f"Expected {expected_version}, got {actual_version}"
   ```

3. **Add to CI:**
   ```yaml
   - name: Verify Docker dependencies match lock file
     run: |
       python scripts/verify_docker_deps.py
   ```

**Recommendation:** Start with Task 2 (simple check), add Task 3 if needed.

---

## Implementation Plan

### Phase 1: Verification (Quick)

1. Merge PR-487 (if not already merged)
2. Build Docker image
3. Verify urllib3 version
4. Document result

**Time:** ~30 minutes

### Phase 2: Guard Check (If needed)

1. Add CI check for urllib3 version
2. Test that it catches mismatches
3. Document in CI workflow

**Time:** ~1-2 hours

### Phase 3: (Optional) General Dependency Guard

1. Create `scripts/verify_docker_deps.py`
2. Add to CI workflow
3. Test with multiple dependencies

**Time:** ~2-3 hours

---

## Acceptance Criteria

- [ ] Docker image contains urllib3 2.6.3 after PR-487 merge
- [ ] CI check verifies dependency versions (at minimum urllib3)
- [ ] CI fails if Docker image has wrong version
- [ ] Documentation updated (if needed)

---

## Files to Modify

### Required

- `.github/workflows/ci.yml` (or similar) — add Docker dependency check

### Optional

- `scripts/verify_docker_deps.py` — general dependency verification script
- `Dockerfile` — explicit version check (not recommended)

---

## Testing

### Manual Test

```bash
# After PR-487 merge
docker build -t test-image .
docker run test-image python -c "import urllib3; print(urllib3.__version__)"
# Expected: 2.6.3
```

### CI Test

```bash
# CI should run:
docker build -t test-image .
docker run test-image python -c "import urllib3; assert urllib3.__version__ == '2.6.3'"
# Should pass if correct, fail if wrong
```

---

## Related

- PR-487: Dependabot urllib3 2.6.2 → 2.6.3
- Security: CVE fix in urllib3 2.6.3

---

## Notes

- **Start simple:** Just verify urllib3 for now
- **Expand later:** If needed, add general dependency guard
- **Don't over-engineer:** Simple CI check is better than complex script if it solves the problem

