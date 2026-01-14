# PR #530: CI — Fix Code Scanning Configuration Detection

## Problem

GitHub Code Scanning shows "2 configurations not found":
- `build.yml:publish`
- `trivy.yml:build`

## Root Cause Analysis

### Current State

**build.yml:**
- ✅ Has `workflow_dispatch` trigger
- ✅ Has SARIF upload in `security-scan` job (filesystem scan)
- ✅ Has SARIF upload in `publish` job (image scan)
- ✅ Runs on `push` to `main`

**trivy.yml:**
- ❌ Missing `workflow_dispatch` trigger
- ✅ Has SARIF upload in `build` job
- ✅ Runs on `push` to `main`

### Why GitHub Can't Find Configurations

1. **trivy.yml** lacks `workflow_dispatch` → cannot create manual baseline run on main
2. Both workflows need at least one successful run on main that uploads SARIF to establish baseline

## Solution

Add `workflow_dispatch` to `trivy.yml` to enable manual baseline runs.

## Changes

### `.github/workflows/trivy.yml`

Add `workflow_dispatch` to `on:` triggers:

```yaml
on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]
  schedule:
    - cron: '16 15 * * 6'
  workflow_dispatch:  # ADD THIS
```

## Verification

After merge:
1. Go to Actions → `trivy` workflow
2. Click "Run workflow" → select `main` branch → Run
3. Wait for completion
4. Check any PR → "configurations not found" warning should disappear

## Risk

Low — adding `workflow_dispatch` is safe and doesn't change existing behavior.
