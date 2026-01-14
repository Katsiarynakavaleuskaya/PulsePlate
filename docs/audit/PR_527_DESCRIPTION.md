# PR #527: Security - Remove vulnerable vendored jaraco.context from the production image (via setuptools removal)

## Problem

Trivy/GitHub code scanning flags **GHSA-58pv-8j8x-9vj2** (jaraco.context < 6.1.0), inherited via setuptools vendored dependency. The vulnerability is a path traversal issue that can allow attackers to write files to arbitrary locations.

**Root cause:** setuptools vendors `jaraco.context` package, and older versions (< 6.1.0) contain the vulnerability. The vendored package is located at `setuptools/_vendor/...jaraco.context-5.3.0.dist-info`.

## Solution

Remove setuptools from the production/runtime image after installing dependencies. setuptools is typically only needed for build-time (pip install / builds), not for serving the app.

**Rationale:** By removing setuptools from the production/runtime image, we remove the vulnerable vendored copy (jaraco.context 5.3.0, which is in the affected range for GHSA-58pv-8j8x-9vj2) from the shipped artifact. setuptools remains available during build-time. The development stage intentionally retains setuptools/wheel because they are required runtime dependencies of pip-tools for lockfile regeneration via `pip-compile`.

**Timing:** `requirements.txt` includes setuptools **for build-time install** (needed for `pip install`), then Dockerfile removes it **before runtime** (in builder stage, before copying venv to runtime-base). 

**Risk:** Uninstalling setuptools can break runtime if any dependency imports `pkg_resources` (from setuptools). Verify the app starts successfully and core imports succeed without setuptools to catch any transitive runtime dependency.

**Verification:** Verified via `python -c "import importlib.util as u; print(u.find_spec('setuptools'))"` returning `None` inside the built `production` image. Also verified the app starts and imports required modules successfully without setuptools present.
## Changes

- **requirements.txt**: Regenerated with `--allow-unsafe` to include `setuptools==78.1.1` (needed for build-time install, then removed before runtime)
- **requirements-dev.txt**: Regenerated with `--allow-unsafe` for consistency
- **REQUIREMENTS.md**: Updated pip-compile commands to include `--allow-unsafe` flag
- **Dockerfile**: Uninstall setuptools/wheel from builder stage (before copying venv to runtime-base). Development stage retains setuptools/wheel as they are required runtime dependencies of pip-tools for lockfile generation.
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

Two related vulnerabilities are addressed by removing setuptools from the production runtime image:

- **GHSA-58pv-8j8x-9vj2 (jaraco.context)**: Path traversal when processing tar archives (tarball extraction). The vulnerable version (jaraco.context < 6.1.0) is vendored within setuptools.
- **CVE-2025-47273 (setuptools)**: Path traversal in setuptools' `PackageIndex.download` (filename derived from URL). Affects setuptools < 78.1.1; primarily related to deprecated `easy_install`/`PackageIndex` flows, not typical FastAPI runtime paths.

Removing setuptools from the runtime image eliminates both vulnerabilities from production runtime while keeping build-time tooling intact.
