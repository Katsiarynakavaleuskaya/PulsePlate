# Fix Plan: Current Blockers in Main

**Date:** 2026-01-16
**Status:** Active Fix Plan
**Purpose:** Fix two critical blockers preventing clean main branch

---

## 🔴 Blocker A: Trivy Code Scanning - glibc CVE-2026-0861 (CRITICAL)

### Problem

Trivy detects CVE-2026-0861 in glibc (memalign family) in Docker image. This is **not your code** — it's a vulnerability in system library `libc6/libc-bin` from Debian base image.

**Critical fact:** In Debian security tracker, this CVE is marked as **(unfixed)** for bookworm (Debian 12). Fixed version is not available yet.

**References:**
- [Debian Security Tracker](https://security-tracker.debian.org/tracker/CVE-2026-0861)
- [Glibc Patch Thread](https://patchwork.sourceware.org/project/glibc/patch/20260114205849.2814817-1-siddhesh%40sourceware.org/)

### Strategy

#### Step 1: Document and Temporarily Suppress (PR-SEC)

**Goal:** Acknowledge unfixed upstream, add temporary suppression with expiry, monitor for fix.

**Actions:**

1. **Create security note document:**
   ```
   docs/security/CVE-2026-0861-glibc.md
   ```

2. **Add Trivy ignore with expiry:**
   ```yaml
   # .trivyignore or trivy.yaml
   # CVE-2026-0861: glibc memalign alignment overflow
   # Status: UNFIXED upstream in Debian bookworm
   # Suppression expires: 2026-03-01 (or when fixed version available)
   # Monitor: https://security-tracker.debian.org/tracker/CVE-2026-0861
   # Remove suppression when: Debian releases security update with fixed glibc
   CVE-2026-0861
   ```

3. **Update workflow to document suppression:**
   ```yaml
   # .github/workflows/security-scan.yml (or similar)
   - name: Run Trivy vulnerability scanner
     uses: aquasecurity/trivy-action@master
     with:
       scan-type: 'fs'
       ignore-unfixed: false
       exit-code: 1
       # Suppressed CVEs documented in .trivyignore
   ```

#### Step 2: Update Base Image (Hygiene)

**Goal:** Use latest base image digest + security updates at build time.

**Actions:**

1. **Update Dockerfile:**
   ```dockerfile
   # Use latest Debian bookworm with security updates
   FROM debian:bookworm-slim@sha256:<latest-digest>

   # Update packages at build time
   RUN apt-get update && \
       apt-get upgrade -y && \
       apt-get clean && \
       rm -rf /var/lib/apt/lists/*
   ```

2. **Pin digest for reproducibility:**
   - Use `@sha256:` digest instead of tag
   - Update digest when security updates are available

#### Step 3: Monitor for Fix

**Goal:** Remove suppression when Debian releases fixed version.

**Actions:**

1. **Set up monitoring:**
   - Check Debian security tracker weekly
   - Set calendar reminder for suppression expiry date
   - When fixed version appears: remove suppression, update base image

2. **Automated check (optional):**
   ```bash
   # scripts/check-cve-2026-0861.sh
   # Check if CVE-2026-0861 is fixed in Debian
   curl -s "https://security-tracker.debian.org/tracker/CVE-2026-0861" | grep -q "fixed" && echo "CVE fixed!" || echo "Still unfixed"
   ```

### Security Notes (Realistic)

**Exploitability:**
- Depends on ability to "feed" too large alignment to memalign-family functions
- In typical Python/FastAPI stack, this is usually not direct user-input
- However, it's a system library → triage/acceptance must be documented

**Risk Assessment:**
- **Severity:** CRITICAL (per CVE classification)
- **Exploitability:** Medium (requires specific conditions)
- **Impact:** System-level (not application-level)
- **Mitigation:** Temporary suppression with expiry + monitoring

**Acceptance Criteria:**
- ✅ Suppression documented with expiry date
- ✅ Security note created
- ✅ Monitoring process established
- ✅ Base image updated to latest (hygiene)
- ✅ Suppression removal process documented

---

## 🔴 Blocker B: CD-Test #252 - `ghcr.io` denied

### Problem

CD-Test workflow fails with:
```
Error response from daemon: Get "https://ghcr.io/v2/": denied: denied
```

**Root cause:** Authentication/permissions issue when pulling from GitHub Container Registry.

### Fix Checklist

#### ✅ Step 1: Verify Workflow Permissions

**Current state:** Already fixed in PR #536 (uses `github.repository_owner`)

**Verify:**
```yaml
# .github/workflows/cd-test.yml
permissions:
  contents: read
  packages: read  # ← Must be present
  id-token: write
```

#### ✅ Step 2: Verify Docker Login

**Current state:** Already fixed in PR #536

**Verify:**
```yaml
- name: Test Docker image pull
  run: |
    set -euo pipefail
    echo "🐳 Testing Docker image pull..."
    if [ -z "${{ secrets.GHCR_READ_TOKEN }}" ]; then
      echo "❌ GHCR_READ_TOKEN is not set"
      exit 1
    fi
    echo "${{ secrets.GHCR_READ_TOKEN }}" | docker login ghcr.io -u ${{ github.repository_owner }} --password-stdin
    echo "✅ Docker login successful"
    docker pull ghcr.io/${{ steps.image-name.outputs.image_name }}:${{ github.event.workflow_run.head_sha }}
    echo "✅ Docker image pull successful"
```

#### ⚠️ Step 3: Verify Token in GitHub Secrets

**Status:** Token added to staging environment (verified via `gh secret list`)

**Verify:**
1. GitHub → Settings → Environments → `staging`
2. Check that `GHCR_READ_TOKEN` exists in Environment secrets
3. Verify token has `read:packages` scope

#### ⚠️ Step 4: Verify Package Permissions

**Action required:** Check package settings in GitHub

1. GitHub → Your profile → Packages → Find your package
2. Package settings → **"Actions access"**
3. Ensure repository `Katsiarynakavaleuskaya/PulsePlate` has **Read** access

**If package is private:**
- Either make package public (if acceptable)
- Or ensure repository is explicitly granted access in package settings

#### ⚠️ Step 5: Verify Token Scope

**Action required:** Verify token has correct scope

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Find token used for `GHCR_READ_TOKEN`
3. Verify scope `read:packages` is checked

**If scope is missing:**
- Create new token with `read:packages` scope
- Update secret in GitHub

### Alternative: Use GITHUB_TOKEN (If Package Allows)

If package allows Actions access via `GITHUB_TOKEN`:

```yaml
- name: Login to GitHub Container Registry
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Test Docker image pull
  run: |
    docker pull ghcr.io/${{ steps.image-name.outputs.image_name }}:${{ github.event.workflow_run.head_sha }}
```

**Note:** `GITHUB_TOKEN` has limited permissions. If package requires explicit access, use `GHCR_READ_TOKEN` (current approach).

---

## 📋 Ready-to-Apply Patches

### Patch 1: Trivy Suppression (`.trivyignore`)

```bash
# Create .trivyignore if it doesn't exist
cat > .trivyignore << 'EOF'
# CVE-2026-0861: glibc memalign alignment overflow
# Status: UNFIXED upstream in Debian bookworm
# Suppression expires: 2026-03-01
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-0861
# Remove suppression when: Debian releases security update with fixed glibc
# Reference: docs/security/CVE-2026-0861-glibc.md
CVE-2026-0861
EOF
```

### Patch 2: Security Note Document

```markdown
# docs/security/CVE-2026-0861-glibc.md

# CVE-2026-0861: glibc memalign Alignment Overflow

**Status:** UNFIXED upstream in Debian bookworm
**Severity:** CRITICAL
**Suppression Expires:** 2026-03-01
**Monitor:** https://security-tracker.debian.org/tracker/CVE-2026-0861

## Summary

CVE-2026-0861 affects glibc memalign-family functions. This is a system library vulnerability, not application code.

## Current Status

- **Debian bookworm:** UNFIXED (no security update available)
- **Upstream glibc:** Patch in progress
- **Our mitigation:** Temporary suppression with expiry

## Action Required

1. Monitor Debian security tracker for fixed version
2. When fixed version available:
   - Remove suppression from `.trivyignore`
   - Update base image to include fixed glibc
   - Update this document with fix date

## Risk Assessment

- **Exploitability:** Medium (requires specific conditions)
- **Impact:** System-level (not application-level)
- **Mitigation:** Base image updates + monitoring
```

### Patch 3: Workflow Permissions (Already Applied)

```yaml
# .github/workflows/cd-test.yml
permissions:
  contents: read
  packages: read  # ← Required for GHCR access
  id-token: write
```

### Patch 4: Docker Login (Already Applied)

```yaml
# .github/workflows/cd-test.yml
- name: Test Docker image pull
  run: |
    set -euo pipefail
    echo "🐳 Testing Docker image pull..."
    if [ -z "${{ secrets.GHCR_READ_TOKEN }}" ]; then
      echo "❌ GHCR_READ_TOKEN is not set"
      exit 1
    fi
    echo "${{ secrets.GHCR_READ_TOKEN }}" | docker login ghcr.io -u ${{ github.repository_owner }} --password-stdin
    echo "✅ Docker login successful"
    docker pull ghcr.io/${{ steps.image-name.outputs.image_name }}:${{ github.event.workflow_run.head_sha }}
    echo "✅ Docker image pull successful"
```

---

## 🎯 PR Structure

### PR-SEC: Security Suppression (Quick Fix)

**Title:** `security: temporary suppression for unfixed glibc CVE-2026-0861`

**Changes:**
- Add `.trivyignore` with CVE-2026-0861 suppression (expiry: 2026-03-01)
- Create `docs/security/CVE-2026-0861-glibc.md`
- Update base image to latest digest (hygiene)

**DoD:**
- [ ] Trivy scan passes (with suppression)
- [ ] Security note documents unfixed status
- [ ] Suppression expiry date set
- [ ] Monitoring process documented

### PR-CD-FIX: CD-Test Workflow Fix (Already Applied)

**Status:** ✅ Already fixed in PR #536

**Remaining action:** Verify token is added to GitHub Secrets (staging environment)

---

## 📝 AGENTS.md Updates

Add to AGENTS.md:

### Unfixed Distro CVE Policy

```markdown
## Security: Unfixed Distro CVE Policy

**When a CRITICAL CVE is unfixed upstream in base image distro:**

1. **Document:** Create security note in `docs/security/`
2. **Suppress:** Add temporary suppression in `.trivyignore` with expiry date
3. **Monitor:** Check upstream tracker weekly until fix available
4. **Remove:** When fixed version available, remove suppression and update base image

**Suppression requirements:**
- Must have expiry date (max 90 days)
- Must reference CVE tracker URL
- Must document removal condition
- Must be reviewed in separate security PR (PR-SEC)

**Rationale:** We cannot fix system library vulnerabilities. We can only:
- Document unfixed status
- Monitor for upstream fix
- Update base image when fix available
```

### GHCR CI Policy

```markdown
## CI: GitHub Container Registry (GHCR) Policy

**Required for workflows that pull from GHCR:**

1. **Permissions:** Job must have `packages: read` permission
2. **Login:** Must use `docker login` before `docker pull`
3. **Username:** Use `${{ github.repository_owner }}` (not `github.actor`)
4. **Token:** Use `${{ secrets.GHCR_READ_TOKEN }}` from environment secrets
5. **Package access:** Package must grant repository access in settings

**Verification:**
- Token must have `read:packages` scope
- Token must be in Environment secrets (not Repository secrets)
- Package settings → Actions access → repository must have Read access
```

---

**Last updated:** 2026-01-16
**Status:** Active Fix Plan
