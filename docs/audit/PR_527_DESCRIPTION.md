# PR #527: Security - Bump setuptools to fix jaraco.context vulnerability

## Problem

Trivy/GitHub code scanning flags **GHSA-58pv-8j8x-9vj2** (jaraco.context < 6.1.0), inherited via setuptools vendored dependency. The vulnerability is a path traversal issue that can allow attackers to write files to arbitrary locations.

**Root cause:** setuptools vendors `jaraco.context` package, and older versions (< 6.1.0) contain the vulnerability. The vendored package is located at `setuptools/_vendor/...jaraco.context-5.3.0.dist-info`.

## Solution

Include setuptools>=78.1.1 in lockfile via `pip-compile --allow-unsafe`. This includes patched jaraco.context >= 6.1.0 and ensures locked version in `requirements.txt`.

**Rationale:** `pip-compile` marks setuptools as "unsafe" by default, but we allow it via `--allow-unsafe` so security fixes live in the lockfile. Dockerfile remains simple (no ad-hoc installs/upgrades).

## Changes

- **requirements.txt**: Regenerated with `--allow-unsafe` to include `setuptools==78.1.1` (locked version)
- **requirements-dev.txt**: Regenerated with `--allow-unsafe` for consistency
- **REQUIREMENTS.md**: Updated pip-compile commands to include `--allow-unsafe` flag
- **Dockerfile**: Remains simple (no ad-hoc setuptools install)
- **AGENTS.md**: Added rule that security fixes must be done via requirements with `--allow-unsafe`, not ad-hoc Dockerfile upgrades

## Verification

- ✅ Trivy/Code scanning should pass (no GHSA-58pv-8j8x-9vj2 alert)
- ✅ Docker build should succeed
- ✅ Smoke tests should pass

## Related

- Security alert: #502
- GHSA: https://github.com/advisories/GHSA-58pv-8j8x-9vj2
- CVE: CVE-2025-47273 (related setuptools vulnerability)

## Risk Assessment

This vulnerability is exploitable when processing malicious tar archives. For production FastAPI applications, this is typically not a runtime path, but:
- Security gates (Trivy/code scanning) require the update
- The package is present in CI/containers → must be fixed
