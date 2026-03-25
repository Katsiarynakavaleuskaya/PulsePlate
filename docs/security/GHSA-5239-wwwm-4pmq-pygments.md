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

As of `25 March 2026`, the repo has no patched Pygments release available to
adopt for this advisory. Because of that, a strict `pip-audit` pre-push gate on
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

## Evidence Anchors

- `.pre-commit-config.yaml:126`
- `docs/roadmap/BACKLOG_LEDGER.md:7540`
- `requirements.txt:230`
- `requirements-dev.txt:163`
- `requirements-lock.txt:230`

## Exit Criteria

Remove the ignore when all of the following are true:

1. a patched `Pygments` release exists;
2. the lockfiles can be regenerated to that safe version without breaking local gates;
3. `pip-audit` passes without `--ignore-vuln GHSA-5239-wwwm-4pmq`.
