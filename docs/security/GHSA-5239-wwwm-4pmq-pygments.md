# GHSA-5239-wwwm-4pmq — Pygments temporary pip-audit exception

## Summary

- Advisory: `GHSA-5239-wwwm-4pmq`
- Package: `Pygments`
- Pinned repo version at the time of triage: `2.19.2`
- Tracked repo surfaces carrying the pinned package:
  - `requirements-ci-lite.txt`
  - `requirements-test.txt`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `requirements-lock.txt`

## Current Triage Status

As of `28 March 2026`, the GitHub advisory page for `GHSA-5239-wwwm-4pmq`
still lists patched versions as `None`, so the repo has no upstream Pygments
release it can safely adopt yet. GitHub Dependabot alerts `#80` and `#81`
remain open across `requirements-ci-lite.txt` and `requirements-test.txt`
while the repo pin stays at `2.19.2` across the tracked requirement surfaces.
Because of that, the strict `pip-audit` pre-push gate on `requirements.txt`,
combined with the CI seam guard over the tracked requirement surfaces, would
still block unrelated narrow PRs even when no dependency regression was
introduced in the branch.

## Temporary Exception

The security-unblock PR adds a documented `pip-audit` ignore for:

```text
GHSA-5239-wwwm-4pmq
```

Scope of the exception:

- limited to the `pip-audit` pre-push hook in `.pre-commit-config.yaml`
- does not remove the pinned `Pygments` evidence from requirement surfaces
- remains tracked in `docs/roadmap/BACKLOG_LEDGER.md` until a patched release is available
- is now watched by `scripts/ci/check_pygments_exception_guard.py`, which fails
  CI as soon as the public GHSA advisory reports a patched version; when repo
  tokens can read Dependabot alerts, the same guard also checks that tracked
  alerts no longer silently remain open

## Evidence Anchors

- `.pre-commit-config.yaml:132`
- `.pre-commit-config.yaml:135`
- `scripts/ci/check_pygments_exception_guard.py:27`
- `scripts/ci/check_pygments_exception_guard.py:143`
- `scripts/ci/check_pygments_exception_guard.py:158`
- `scripts/ci/check_pygments_exception_guard.py:231`
- `.github/workflows/ci.yml:117`
- `.github/workflows/ci.yml:134`
- `docs/roadmap/BACKLOG_LEDGER.md:7856`
- `requirements-ci-lite.txt:278`
- `requirements-test.txt:27`
- `https://github.com/advisories/GHSA-5239-wwwm-4pmq`

## Exit Criteria

Remove the ignore when all of the following are true:

1. a patched `Pygments` release exists;
2. the lockfiles can be regenerated to that safe version without breaking local gates;
3. `pip-audit` passes without `--ignore-vuln GHSA-5239-wwwm-4pmq`.
