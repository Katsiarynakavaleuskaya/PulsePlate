# PR #527: Security - Bump setuptools to fix jaraco.context vulnerability

## Problem

Trivy/GitHub code scanning flags **GHSA-58pv-8j8x-9vj2** (jaraco.context < 6.1.0), inherited via setuptools vendored dependency. The vulnerability is a path traversal issue that can allow attackers to write files to arbitrary locations.

**Root cause:** setuptools vendors `jaraco.context` package, and older versions (< 6.1.0) contain the vulnerability. The vendored package is located at `setuptools/_vendor/...jaraco.context-5.3.0.dist-info`.

## Solution

Remove setuptools from runtime image after installing dependencies. setuptools is only needed for build-time (pip install), not runtime.

**Rationale:** setuptools==78.1.1 still vendors jaraco.context 5.3.0 (vulnerable). Adding jaraco.context>=6.1.0 to requirements doesn't fix the vendored dependency inside setuptools. Since setuptools isn't used in runtime code, we uninstall it in the builder stage (before copying venv to runtime-base), so the final production image does not contain setuptools. Verified via `python -c "import importlib.util as u; print(u.find_spec('setuptools'))"` returning `None` inside the built `production` image.

## Changes

- **requirements.txt**: Regenerated with `--allow-unsafe` to include `setuptools==78.1.1` (needed for build-time)
- **requirements-dev.txt**: Regenerated with `--allow-unsafe` for consistency
- **REQUIREMENTS.md**: Updated pip-compile commands to include `--allow-unsafe` flag
- **Dockerfile**: Uninstall setuptools/wheel from runtime image after installing dependencies
- **AGENTS.md**: Added rule that security fixes must be done via requirements with `--allow-unsafe`, not ad-hoc Dockerfile upgrades

## Verification

- ✅ Trivy/Code scanning should pass (no GHSA-58pv-8j8x-9vj2 alert)
- ✅ Docker build should succeed
- ✅ Smoke tests should pass

**Local verification (optional):**
```bash
# 1) Build production image
docker build -t pulseplate:test --target production .

# 2) Verify setuptools cannot be imported
docker run --rm pulseplate:test python -c "import importlib.util as u; print(u.find_spec('setuptools'))"
# Expected: None

# 3) Verify no setuptools/jaraco.context in site-packages
docker run --rm pulseplate:test sh -c 'ls -1 /opt/venv/lib/python*/site-packages | grep -iE "setuptools|jaraco.context" || echo "✅ Not found"'

# 4) (Optional) Verify API starts without setuptools
docker run --rm -p 8000:8000 pulseplate:test &
sleep 5
curl -sS http://localhost:8000/health && echo "✅ API works"
```

**If security alert #502 doesn't close after merge:**

1. Check alert details: "Detected in" field (image vs filesystem/SBOM)
2. If scanning filesystem/SBOM (not runtime image): Dismiss with reason "Not present in runtime image; build-time only; removed in Dockerfile"
3. If scanning wrong stage: Update CI workflow to scan `production` stage only

## Related

- Security alert: #502
- GHSA: <https://github.com/advisories/GHSA-58pv-8j8x-9vj2>
- CVE: CVE-2025-47273 (related setuptools vulnerability)

## Risk Assessment

This vulnerability is exploitable when processing malicious tar archives. For production FastAPI applications, this is typically not a runtime path. By removing setuptools from the runtime image, we eliminate the vulnerability entirely while keeping setuptools available during build-time (where it's needed for pip install).
