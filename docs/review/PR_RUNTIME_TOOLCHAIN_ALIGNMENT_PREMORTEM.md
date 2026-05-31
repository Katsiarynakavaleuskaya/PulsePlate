# Runtime Toolchain Alignment Premortem

## Summary

Plan: align PulsePlate local and CI runtime pins around Python `3.13.6`, add a
local Ruby source, and pin Fastlane to the lockfile-resolved release tooling
version without changing runtime product behavior.

Failure frame: it is 48 hours from now, this CI/tooling PR made dependency and
release validation less trustworthy, and we are looking backward to understand
why.

## Scope

In scope:

- `.python-version` -> `3.13.6`
- `.tool-versions` -> `python 3.13.6`
- `.ruby-version` -> `3.1`
- `ios/Gemfile` Fastlane -> `= 2.235.0`
- `ios/Gemfile.lock` dependency stanza aligned with resolved Fastlane `2.235.0`
- Auxiliary workflow setup-python pins normalized from bare `3.13` to `3.13.6`
- Focused workflow/toolchain guard coverage

Out of scope:

- Docker `python:3.13.13-slim-bookworm`
- Node and `.nvmrc`
- iOS deployment target
- SQLite/test-runtime architecture
- Python `3.11` / `3.12` compatibility matrix removal
- Python `3.14` migration
- App Store metadata, screenshots, upload lanes, and release submissions

## Role Gate Evidence

- `agent-coordinator`: `BLOCK` until main CI completed; operator explicitly
  overrode this as non-blocking for implementation start and retained main CI
  monitoring outside this lane.
- `dev-operator`: confirmed clean worktree and main CI in progress; operator
  override applies only to start gating, not readiness.
- `architecture-specialist`: `PASS_TO_NEXT_ROLE`; prefer direct `3.13.6` pins
  in auxiliary workflows and preserve visible matrix/check labels.
- `app-store-release-agent`: `PASS_TO_NEXT_ROLE`; Fastlane pin is release
  tooling only, with no upload/metadata/asset changes.
- `qa-engineer-agent`: `PASS_TO_NEXT_ROLE`; add structured guard coverage and
  keep machine-heavy `make verify` deferral explicit if used.
- `bug-hunter`: `PASS_TO_NEXT_ROLE`; cover easy-miss workflow pins and avoid
  regex-only false positives.
- `security-auditor`: `PASS_TO_NEXT_ROLE`; preserve private-index fail-closed
  installs, action SHA pins, masking, and Fastlane/jwt guard posture.
- `frontend-engineer`: `PASS_TO_NEXT_ROLE`; no frontend source, Node, OpenAPI,
  or build validation is needed unless frontend artifacts change.
- `creative-designer`: `PASS_TO_NEXT_ROLE`; no design tokens, screenshots,
  metadata copy, or visual assets are in scope.

## Findings

### F1: Python Patch Pin Drift

Failure story: Local developers run `3.13.13` from `.python-version` or
`.tool-versions`, while CI exercises `3.13.6`. A failure reproduces only on one
side, so dependency and SQLite test failures are misdiagnosed as package drift
instead of runtime drift.

Underlying assumption: all repo Python sources already point at the same patch
runtime.

Early warning signs:

- `.python-version`, `.tool-versions`, and CI env disagree.
- A setup-python step still uses broad `3.13`.

Containment action: pin local files and auxiliary setup-python inputs to
`3.13.6`, then add a guard that fails on future drift.

Disposition: `FIXED_BY_PLAN`.

### F2: Required Check Labels Accidentally Renamed

Failure story: A well-intended broad replacement changes matrix values from
`3.13` to `3.13.6`. GitHub required-check names shift, branch protection no
longer matches the historical check identity, and merge-readiness scripts or
operator dashboards read the lane incorrectly.

Underlying assumption: runtime patch pin strings and visible check labels are
the same contract.

Early warning signs:

- `matrix.python-version` values become `3.13.6`.
- Artifact/check names lose `3.13` identity.

Containment action: keep CI matrix labels as `3.13` and route only the
underlying setup runtime through `env.PYTHON_VERSION` or direct `3.13.6`.

Disposition: `FIXED_BY_PLAN`.

### F3: Auxiliary Workflow Normalization Misses Side Lanes

Failure story: The main CI workflow is aligned, but release evidence,
Experiment Runner, metrics, or nightly workflows keep broad `3.13`. Later a
release or evidence job fails on a patch/runtime mismatch that the PR claimed to
remove.

Underlying assumption: only canonical CI and frontend CI matter.

Early warning signs:

- `rg "python-version:.*3.13"` still finds setup inputs after implementation.
- Workflow guard coverage targets only `ci.yml`.

Containment action: include all known auxiliary workflow setup inputs in the
guard and update the packet path set to cover them.

Disposition: `FIXED_BY_PLAN`.

### F4: Fastlane Pin Is Only Half Applied

Failure story: `ios/Gemfile` pins Fastlane exactly but `ios/Gemfile.lock`
dependency metadata remains range-based, or Bundler churns unrelated gems. The
release tooling surface looks pinned but still creates noisy or ambiguous
resolver evidence.

Underlying assumption: changing only `Gemfile` is sufficient.

Early warning signs:

- `DEPENDENCIES` still says `fastlane (~> 2.228)`.
- `bundle install` rewrites unrelated lockfile sections or creates tracked
  local bundler artifacts.

Containment action: align only the Fastlane dependency stanza unless Bundler
proves more is required, and add guard coverage for Gemfile/lock parity.

Disposition: `FIXED_BY_PLAN`.

### F5: Ruby Local/CI Drift Persists

Failure story: CI uses Ruby `3.1`, but local App Store validation runs under a
different Ruby family. A contributor sees Bundler or Fastlane behavior that
does not match CI and produces avoidable lockfile churn.

Underlying assumption: CI Ruby version is obvious enough without a repo-local
file.

Early warning signs:

- root `.ruby-version` is missing.
- local `ruby -v` differs from workflow `ruby-version: "3.1"`.

Containment action: add `.ruby-version` with `3.1`.

Disposition: `FIXED_BY_PLAN`.

### F6: Private Python Index Availability Is Weakened

Failure story: A workflow pin cleanup accidentally switches from the composite
private-index installer to direct public dependency installation, masking
private wheel availability gaps and weakening supply-chain controls.

Underlying assumption: setup-python pin changes cannot affect installation
policy.

Early warning signs:

- workflows gain unscoped `pip install`.
- `.github/actions/python-setup` direct-proxy usage changes.

Containment action: change only runtime version inputs, preserve
`requirements-profile` and `install-mode: direct-proxy`, and keep supply-chain
tests green.

Disposition: `FIXED_BY_PLAN`.

### F7: SQLite Runtime Problems Get Bundled Into Toolchain PR

Failure story: Historical SQLite flakes draw the PR into test architecture
changes. The alignment lane becomes broad, high-risk, and hard to review.

Underlying assumption: every Python/runtime issue should be solved in this PR.

Early warning signs:

- tests or app DB bootstrap code changes appear in the diff.
- PR body claims SQLite root-cause remediation.

Containment action: keep SQLite explicitly out of scope unless this PR exposes
a new reproducible failure in its focused gates.

Disposition: `NOT_A_BUG`.

### F8: Docker Runtime Is Accidentally Rebased

Failure story: A broad search/replace changes production Docker from
`3.13.13-slim-bookworm` to `3.13.6`, mixing image/security policy with local/CI
toolchain alignment.

Underlying assumption: every Python string in repo belongs to this lane.

Early warning signs:

- `Dockerfile` or Docker docs appear in the diff.
- production image tags change without image/security review.

Containment action: do not touch Docker image surfaces in this PR.

Disposition: `NOT_A_BUG`.

## Revised Plan

1. Apply only the scoped runtime/toolchain edits.
2. Add structured guard coverage for exact local pins, workflow setup inputs,
   visible CI label preservation, Ruby version, and Fastlane Gemfile/lock parity.
3. Preserve private-index/direct-proxy workflow install controls.
4. Run the focused gates before push; defer full local `make verify` only under
   the machine-heavy exception with PR evidence.
5. Treat current-head CI, bot/actionable review disposition, fixed mapping, and
   wait-window as merge-readiness requirements, not as start-gate shortcuts.

## Pre-Merge Checklist

- [ ] No out-of-scope Docker, Node, iOS deployment target, SQLite, frontend UI,
      design, metadata, screenshot, or upload-lane changes.
- [ ] All setup-python runtime pins are `3.13.6` or existing
      `${{ env.PYTHON_VERSION }}`.
- [ ] Visible `3.13` CI matrix/check labels remain stable.
- [ ] Fastlane Gemfile and lockfile dependency stanza both pin `2.235.0`.
- [ ] Private-index/direct-proxy controls remain unchanged.
- [ ] Focused runtime/toolchain guard tests pass.
- [ ] Full `make verify` is either run locally or explicitly deferred under the
      machine-heavy PR exception with current-head CI parity evidence.

## Decision

`proceed with changes`.

Proceed only with the guard-backed scoped implementation above. Do not open or
claim readiness while any in-scope finding lacks a code/config/test fix or a
formal disposition.
