# GHSA-p423-j2cm-9vmq — `cryptography` private-index mirror lag seam

## Summary

- Advisory: `GHSA-p423-j2cm-9vmq`
- CVE: `CVE-2026-39892`
- Package: `cryptography`
- Public patched version: `46.0.7`
- Temporary repo pin while the approved mirror lags: `46.0.6`
- Remove-by: `9 May 2026`
- Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cryptography-private-index-bump`

## Context

`pip-audit` reports that `cryptography==46.0.6` is affected and that the first
patched release is `46.0.7`.

At the same time, the approved private package proxy used by shared CI and
Docker locked installs does not currently resolve `cryptography==46.0.7` for
the canonical install paths. Current evidence from PR `#1379`:

- `CI` / `lint` failed during locked install on `9 April 2026`
- `Frontend CI` / `build-and-test` failed during backend dependency install on
  `9 April 2026`
- `Docker OpenAPI Smoke` / `smoke` failed during Docker locked install on
  `9 April 2026`

Those jobs all fail with the same contract-level symptom: patched
`cryptography==46.0.7` cannot be resolved through `PULSEPLATE_PYTHON_INDEX_URL`
for the current CI/Docker environment.

## Temporary Decision

The repo keeps `cryptography==46.0.6` on tracked requirement surfaces only as a
temporary mirror-lag seam and carries a narrow local `pip-audit` exception for
`GHSA-p423-j2cm-9vmq` so unrelated PRs are not blocked while the approved
mirror catches up.

This seam is allowed only because all of the following are true:

1. the patched public version is known (`46.0.7`);
2. the approved private proxy currently blocks that version on shared CI/Docker
   install paths;
3. the exception is scoped to one GHSA identifier;
4. the removal path is tracked in the backlog ledger and this security note.

## Exit Criteria

Retire this seam only when all are true:

1. the approved private proxy resolves `cryptography==46.0.7` on locked
   install paths used by CI and Docker;
2. tracked requirement surfaces pin `46.0.7` (or a later safe version);
3. `.pre-commit-config.yaml` no longer carries
   `--ignore-vuln GHSA-p423-j2cm-9vmq`;
4. `pre-commit run --hook-stage pre-push pip-audit --all-files` passes without
   the temporary exception;
5. canonical CI and Docker smoke are green after the pin is raised.

## Evidence Anchors

- `.pre-commit-config.yaml`
- `requirements.in`
- `requirements.txt`
- `requirements-ci-lite.txt`
- `requirements-dev.txt`
- `requirements-lock.txt`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cryptography-private-index-bump`
