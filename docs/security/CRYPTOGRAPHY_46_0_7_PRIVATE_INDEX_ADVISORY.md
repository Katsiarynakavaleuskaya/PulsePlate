# `cryptography 46.0.7` approved-index availability advisory

## Summary

`PR #1378` intentionally raises the repository security floor for `cryptography`
from `46.0.6` to `46.0.7` to remediate the active advisory lane. The branch
itself is correct, but current GitHub Actions and Docker install steps are
blocked because the approved private Python index behind
`PULSEPLATE_PYTHON_INDEX_URL` does not currently serve a matching
`cryptography==46.0.7` artifact for the CI environment.

## Governance (intentional draft blocker)

- **Owner:** @katsiaryna_kavaleuskaya
- **Remove-by:** 2026-06-09 — reassess: if the approved private index serves
  `cryptography==46.0.7` (or a higher safe release), rerun locked installs,
  keep the raised floor, and close this advisory + ledger note in the same PR;
  if the index still lags, extend the remove-by date in this doc + ledger note.
- **Backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cryptography-private-index-sync`
- **Current PR:** `PR #1378`

## Production exposure (posture)

This is not a waiver to ship a lower floor. The current branch keeps the
security floor at `46.0.7`, and the blocker is operational supply-chain
availability in the approved internal mirror, not a code-level regression in
the branch. The PR must remain draft until the approved index serves the fixed
artifact or a separately approved higher safe release.

## Current repo state (2026-04-09)

- **Current branch pins:** `requirements.txt`, `requirements-ci-lite.txt`,
  `requirements-dev.txt`, `requirements-lock.txt`, and `constraints.txt` all
  require `cryptography 46.0.7` or `>=46.0.7`; representative anchors:
  `requirements.txt:39`, `constraints.txt:53`.
- **Approved private CI/Docker index:** current-head installs fail with
  `Cannot install cryptography==46.0.7 ... no matching distributions available
  for your environment: cryptography` followed by `ResolutionImpossible`; the
  locked installer + workflow path is anchored at
  `scripts/ci/install_locked_python_requirements.py:277`,
  `scripts/ci/install_locked_python_requirements.py:356`,
  `.github/actions/python-setup/action.yml:61`, and `.github/workflows/ci.yml:400`.
- **Observed failing runs on PR #1378 head `22670ae9`:**
  - `CI` run `24175455245`
  - `Frontend CI` run `24175455183`
  - `Docker OpenAPI Smoke` run `24175455210`
  - `Docker Build and Push` run `24175455229`
  - `Docker Image CI` run `24175455190`
- **Local branch status:** local validation remains clean (`check_preflight`,
  `check_agent_consistency`, `pre-commit run --all-files`), which supports the
  conclusion that the blocker is mirror/index availability rather than branch
  behavior.

## Allowed remediation paths

1. Promote or sync `cryptography 46.0.7` into the approved private index, then
   rerun current-head CI and Docker lanes.
2. If the approved index already has a higher safe `cryptography` release,
   repin to that exact available secure version and regenerate lock/guard
   surfaces in the same narrow security lane.
3. Keep `PR #1378` in draft until one of the above is true.

## Prohibited shortcut

- Do **not** lower the floor back to `46.0.6` or `46.0.5` just to make CI green.
- Do **not** remove the constraint or widen the pin to mask the mirror problem.

## References

- `requirements.txt:39`
- `constraints.txt:53`
- `scripts/ci/install_locked_python_requirements.py:277`
- `scripts/ci/install_locked_python_requirements.py:356`
- `.github/actions/python-setup/action.yml:61`
- `.github/workflows/ci.yml:400`
- `docs/review/PR_1378_FIXED_MAPPING.md:1`
