# GHSA-5239-wwwm-4pmq — Pygments seam retirement remediation

## Summary

- Advisory: `GHSA-5239-wwwm-4pmq`
- Package: `Pygments`
- Patched repo version on the remediation branch: `2.20.0`
- Tracked repo surfaces carrying the pinned package:
  - `requirements-ci-lite.txt`
  - `requirements-test.txt`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `requirements-lock.txt`

## Current Triage Status

As of `30 March 2026`, the GitHub advisory page for `GHSA-5239-wwwm-4pmq`
reports `first_patched_version: 2.20.0`. That flips the temporary seam from an
allowed unblock to a required remediation, because the repo can now adopt a
safe upstream release across every tracked requirement surface. The current-head
remediation lane therefore:

- bumps `Pygments` to `2.20.0` in all tracked requirement files;
- removes the `pip-audit --ignore-vuln GHSA-5239-wwwm-4pmq` exception from
  `.pre-commit-config.yaml`;
- keeps the CI seam guard in place so future regressions still fail closed if
  the ignore ever reappears or the tracked pins drift below the patched floor.

## Remediation Completed

The temporary exception is retired on this branch:

- `.pre-commit-config.yaml` no longer carries `--ignore-vuln
  GHSA-5239-wwwm-4pmq`;
- `requirements-ci-lite.txt`, `requirements-test.txt`, `requirements.txt`,
  `requirements-dev.txt`, and `requirements-lock.txt` all pin
  `Pygments==2.20.0`;
- `scripts/ci/check_pygments_exception_guard.py` remains the contract guard that
  enforces "patched release exists -> seam must be gone".

## Evidence Anchors

- `.pre-commit-config.yaml:123`
- `scripts/ci/check_pygments_exception_guard.py:27`
- `scripts/ci/check_pygments_exception_guard.py:143`
- `scripts/ci/check_pygments_exception_guard.py:158`
- `scripts/ci/check_pygments_exception_guard.py:231`
- `.github/workflows/ci.yml:117`
- `.github/workflows/ci.yml:134`
- `docs/roadmap/BACKLOG_LEDGER.md:7856`
- `requirements-ci-lite.txt:278`
- `requirements-test.txt:27`
- `requirements.txt:230`
- `requirements-dev.txt:163`
- `requirements-lock.txt:230`
- `https://github.com/advisories/GHSA-5239-wwwm-4pmq`

## Exit Criteria

Satisfied on this remediation branch when all of the following hold:

1. `Pygments==2.20.0` is pinned across the tracked requirement surfaces;
2. `pip-audit` passes without `--ignore-vuln GHSA-5239-wwwm-4pmq`;
3. the seam guard passes against the live advisory state.
