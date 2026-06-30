# PR #2055 Docker/Trivy ACL Attr Premortem

Mode: `pr-premortem`
Packet: `artifacts/orchestration/task_packets/acba65b177db.json`
Branch: `codex/fix-main-docker-trivy-acl-attr`
Date: 2026-06-30

## Summary

PR #2055 removes `libacl1` and `libattr1` from the final production Docker
image and keeps the Docker Build and Push plus scheduled Trivy runtime-surface
guards fail-closed.

Failure frame: it is 48 hours from now, this urgent Docker/Trivy hotfix made
`main` worse, and we are looking backward to understand why.

## Findings

### PM-2055-001. Only the PR Docker lane blocks ACL/attr reintroduction

Failure story: the pull-request Docker build blocks `libacl1` and `libattr1`,
but the `main`/scheduled/manual Trivy lane keeps the old blocked-package list.
The PR appears green, then `main` later rebuilds through the Trivy workflow and
the explicit dependency-surface guard misses an ACL/attr regression. Trivy may
still flag the packages, but the repo loses the deterministic package-surface
failure that this PR intended to add.

Underlying assumption: updating `.github/workflows/build.yml` is enough to
cover all production-image scan paths.

Early warning signs:

- `build.yml` and `trivy.yml` pass different `--blocked-debian-package` values.
- The two-workflow guard test checks only one workflow or only one image ref.

Containment action: keep both workflows aligned and require the focused
workflow test to inspect both `pulseplate:test` and
`pulseplate:trivy-scan-${{ github.sha }}`.

Disposition: FIXED

Evidence:

- `.github/workflows/build.yml` and `.github/workflows/trivy.yml` both pass
  `--blocked-debian-package libacl1` and
  `--blocked-debian-package libattr1`.
- `tests/test_docker_workflow_build_path_contract.py` checks both workflows in
  `test_docker_runtime_surface_guard_blocks_perl_runtime_packages`.
- Fix commit:
  `3b8089b7c263951c0834a175da771ee189fdee3c`.

### PM-2055-002. The fix hides the Trivy finding with a broad ignore

Failure story: instead of removing the unused packages, the PR adds a broad
`.trivyignore` entry or Rego policy suppression for the ACL/attr findings. The
Docker security scan goes green while the vulnerable packages remain in the
production image, and future scans inherit a stale suppression that masks
unrelated package state.

Underlying assumption: any green Trivy result is equivalent to reducing the
runtime surface.

Early warning signs:

- `.trivyignore` or `trivy/ignore-policy.rego` mentions the ACL/attr packages
  or the associated finding IDs.
- The PR changes Trivy `ignore-unfixed`, `continue-on-error`, or fail-open scan
  behavior.

Containment action: keep the remediation as package removal plus explicit
runtime-surface guards, and add regression tests proving no broad ignore was
introduced.

Disposition: FIXED

Evidence:

- The PR changes no `.trivyignore` or `trivy/ignore-policy.rego` suppression.
- `tests/test_trivy_ignore_policy_expiry.py` asserts the ACL/attr findings and
  package names are absent from both suppression surfaces.
- Current-head CI reports `Trivy ignore-policy expiry` and Docker
  `security-scan` passing.

### PM-2055-003. Production pruning removes a library still needed at runtime

Failure story: `libacl1` or `libattr1` is indirectly required by a runtime
binary in the final production image. The image scan is clean, but the app or a
health-check path fails after deployment because an expected system library was
removed too aggressively.

Underlying assumption: ACL/attr packages are unused in the final PulsePlate
runtime after the existing production-only pruning block.

Early warning signs:

- The built production image fails the Python smoke check for `ssl`, SQLite, or
  `/bin/sh`.
- Docker Build and Push `Test Docker image` fails after the pruning change.

Containment action: keep pruning limited to the final `production` stage and
prove the built image with the existing Docker smoke checks.

Disposition: FIXED

Evidence:

- `Dockerfile` removes ACL/attr packages only after `FROM runtime-base AS
  production`; `runtime-base` and `development` keep their apt workflows.
- Local image smoke evidence in the mapping artifact validates `ssl`, SQLite
  3.53.2, and `/bin/sh`.
- Current-head Docker Build and Push `build` and `security-scan` passed on PR
  #2055 head `c2d9bd45b6b8d764f913f752b77a892f87d1bb0c`.

### PM-2055-004. Governance evidence goes green before review findings are mapped

Failure story: the PR body and fixed mapping keep the
`No actionable review comments` sentinel while Codex and Sourcery have already
left actionable or disposition-required feedback. Merge readiness fails, or
worse, threads are resolved without disposition proof.

Underlying assumption: passing Docker/Trivy CI is enough to close the PR
without artifact-level review governance.

Early warning signs:

- `docs/review/PR_2055_FIXED_MAPPING.md` contains
  `- No actionable review comments` after bot comments exist.
- Discussion pass checkboxes are marked complete while role, premortem,
  Experiment Runner, or security scan evidence remains pending.

Containment action: replace the sentinel with FIXED or NOT-A-BUG disposition
blocks, map each review URL, keep thread resolution after mapping, and rerun the
strict merge-readiness wrapper.

Disposition: FIXED

Evidence:

- This premortem records the required PR-scoped risk findings and closures.
- `docs/review/PR_2055_FIXED_MAPPING.md` is updated in the follow-up governance
  mapping commit to replace the sentinel with explicit disposition blocks.

## Revised Plan

- Keep the code diff narrow to Docker production pruning, Docker/Trivy workflow
  runtime-surface guards, focused tests, and review evidence.
- Do not add Trivy suppressions for the ACL/attr findings.
- Treat `docs/review/PR_2055_FIXED_MAPPING.md` as the canonical source for
  thread dispositions and update the PR body only as a mirror.
- Resolve review threads only after the updated mapping lands and strict
  merge-readiness passes.

## Pre-Merge Checklist

- [x] Docker Build and Push `build` and `security-scan` passed on current head.
- [x] Focused Docker/Trivy tests passed locally and in CI.
- [x] No broad Trivy ignore or fail-open scan behavior was added.
- [x] Premortem findings are closed above.
- [ ] Mapping artifact and PR body mirror include all current actionable
  comments and post-open evidence.
- [ ] Strict merge-readiness wrapper passes after the latest commit and after
  mapped threads are resolved.

## Decision

`proceed with changes`

The implementation is narrow and covered by focused tests/current-head CI, but
the PR cannot claim readiness until the governance artifact, PR body mirror,
mandatory role/security review evidence, and strict merge-readiness checks are
updated after the latest review activity.
