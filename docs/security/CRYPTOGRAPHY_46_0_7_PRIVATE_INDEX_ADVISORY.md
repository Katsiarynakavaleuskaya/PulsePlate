# `cryptography 46.0.7` approved-index availability advisory

## Summary

This advisory is now closed by branch-side remediation. `PR #1378` originally
attempted to raise the exact `cryptography` pin from `46.0.6` to `46.0.7`, but
current-head CI showed the approved private Python index lagged the upstream
release on `09 April 2026`. The branch now uses the still-safe exact release
`46.0.6`, which remains above the canonical CVE floor (`46.0.5`) documented in
`docs/security/CVE-2026-26007-cryptography.md:8`.

## Governance (closed)

- **Owner:** @katsiaryna_kavaleuskaya
- **Resolution date:** 2026-04-09
- **Backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cryptography-private-index-sync`
- **Current PR:** `PR #1378`

## Production exposure (posture)

This is not a waiver to ship a lower floor. The current branch keeps the
security floor at `46.0.6`, which is still above the required fixed minimum
`46.0.5` for CVE-2026-26007. The temporary `46.0.7` exact pin was reverted
because merge readiness depends on current-head installability against the
approved index, not on waiting for a newer non-required patch release.

## Current repo state (2026-04-09)

- **Current branch pins:** `requirements.txt`, `requirements-ci-lite.txt`,
  `requirements-dev.txt`, `requirements-lock.txt`, and `constraints.txt` now
  require `cryptography 46.0.6` or `>=46.0.6`; representative anchors:
  `requirements.txt:39`, `constraints.txt:53`.
- **Root cause captured:** the failed `46.0.7` exact pin was triggered by an
  upstream release published on `08 April 2026` (`PyPI release history`) before
  the approved mirror caught up; branch install paths are still anchored at
  `scripts/ci/install_locked_python_requirements.py:277`,
  `scripts/ci/install_locked_python_requirements.py:356`,
  `.github/actions/python-setup/action.yml:61`, and `.github/workflows/ci.yml:400`.
- **Observed failing runs on PR #1378 head `38510e8f2` before safe repin:**
  - `CI` run `24175455245`
  - `Frontend CI` run `24175455183`
  - `Docker OpenAPI Smoke` run `24175455210`
  - `Docker Build and Push` run `24175455229`
  - `Docker Image CI` run `24175455190`
- **Local branch status:** branch now targets the safe installable release and
  should be validated through normal local + PR gates rather than held in draft.

## Closed remediation path

1. Keep `PR #1378` on the safe exact release `46.0.6` unless a follow-up PR
   intentionally upgrades to a newer mirrored release.
2. If a future PR wants `46.0.7` or higher, verify approved-index availability
   first and then rerun locked installs before landing the upgrade.

## Prohibited shortcut

- Do **not** lower the floor below `46.0.5`.
- Do **not** remove the constraint or widen the pin to mask the security floor.

## References

- `docs/security/CVE-2026-26007-cryptography.md:8`
- `requirements.txt:39`
- `constraints.txt:53`
- `scripts/ci/install_locked_python_requirements.py:277`
- `scripts/ci/install_locked_python_requirements.py:356`
- `.github/actions/python-setup/action.yml:61`
- `.github/workflows/ci.yml:400`
- `docs/review/PR_1378_FIXED_MAPPING.md:1`
