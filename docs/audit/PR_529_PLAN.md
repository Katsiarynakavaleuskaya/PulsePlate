# PR #529: CI — Fix Code Scanning Configuration Detection

## Problem

GitHub Code Scanning shows: "2 configurations not found":
- `build.yml:publish`
- `trivy.yml:build`

The workflows/jobs **exist in the repo**, but GitHub cannot resolve them for
baseline comparison because there has been **no successful SARIF upload run on
`main`** to establish the baseline for these configurations.

## Root cause

- `trivy.yml` was missing `workflow_dispatch`, so we couldn't trigger a manual
  baseline run on `main`.
- Both workflows (`trivy.yml` and `build.yml`) must have at least one successful
  run on `main` that uploads SARIF for GitHub to register the configurations.

## Fix

Add `workflow_dispatch` to `trivy.yml` so we can run it manually on `main` after merge.

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

## Post-merge steps (required)

After merging this PR:
1. Actions → run `trivy` workflow on `main` (manual Run workflow)
2. Actions → run `build` workflow on `main` (manual Run workflow)

These runs upload SARIF on `main`, establish the baseline, and should resolve
the "configurations not found" warning.

## Risk

Low — adding `workflow_dispatch` is safe and doesn't change existing behavior.
