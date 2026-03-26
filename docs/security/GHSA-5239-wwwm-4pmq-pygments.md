# GHSA-5239-wwwm-4pmq — Pygments temporary pip-audit exception

## Summary

- Advisory: `GHSA-5239-wwwm-4pmq`
- Package: `Pygments`
- Pinned repo version at the time of triage: `2.19.2`
- Tracked repo surfaces carrying the pinned package:
  - `requirements.txt`
  - `requirements-dev.txt`
  - `requirements-lock.txt`

## Current Triage Status

As of `26 March 2026`, the repo still has no patched Pygments release available
to adopt for this advisory. GitHub Dependabot alerts `#58`, `#59`, and `#60`
remain open across `requirements-dev.txt`, `requirements-lock.txt`, and
`requirements.txt`. Because of that, a strict `pip-audit` pre-push gate on
`requirements.txt` blocks unrelated narrow PRs even when no dependency
regression was introduced in the branch.

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
- `scripts/ci/check_pygments_exception_guard.py:44`
- `scripts/ci/check_pygments_exception_guard.py:151`
- `scripts/ci/check_pygments_exception_guard.py:158`
- `scripts/ci/check_pygments_exception_guard.py:231`
- `.github/workflows/ci.yml:117`
- `.github/workflows/ci.yml:134`
- `docs/roadmap/BACKLOG_LEDGER.md:7540`
- `requirements.txt:230`
- `requirements-dev.txt:163`
- `requirements-lock.txt:230`

## Exit Criteria

Remove the ignore when all of the following are true:

1. a patched `Pygments` release exists;
2. the lockfiles can be regenerated to that safe version without breaking local gates;
3. `pip-audit` passes without `--ignore-vuln GHSA-5239-wwwm-4pmq`.
