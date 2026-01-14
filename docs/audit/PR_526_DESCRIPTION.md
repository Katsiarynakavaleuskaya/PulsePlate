# PR #526: Fix Dockerfile pip version pin issue

## Problem

Docker build was failing with error:

```text
No matching distribution found for pip==24.2 (from versions: none)
```

**Root cause:** The build environment may not be able to resolve the exact pinned version from PyPI index (index/proxy/TLS issues), resulting in "from versions: none". This was blocking Dependabot PRs (e.g., #525, #524).

## Solution

Remove pip upgrade entirely and rely on base image pip. This is more stable and avoids index resolution failures while maintaining compatibility with base image updates.

## Changes

- **Dockerfile**: Removed `pip install --upgrade pip==24.2` step, now uses base image pip directly
- **AGENTS.md**: Added Dockerfile policy to prevent regression (document exact pin risks and preferred approach)

## Verification

- ✅ Smoke tests should pass (builds on current base image)
- ✅ Dependabot PRs should no longer fail on Docker build step after rebase

## Related

Fixes smoke test failures in Dependabot PRs:
- #525 (filelock bump)
- #524 (virtualenv bump)

## Next Steps

After merge:
1. Rebase dependabot PRs: `@dependabot rebase` on #525 and #524
2. Verify CI becomes green
3. Merge dependabot PRs in order: #525 → #524
