# PR #2023 Premortem Risk Review

Mode: `pr-premortem`

## Summary

Plan: expand PR #2023 from the narrow installer security-floor fix into PR-1 of
the dependency completion split by adding a canonical Python dependency surface
contract, offline validator, compatibility wrapper, and focused tests without
changing dependency versions or lockfiles.

Failure frame: it is one review cycle later and the PR still looks green locally
but dependency ownership remains ambiguous or a security floor can still be
silently bypassed.

## Findings

### PM-2023-001: New dependency surfaces are not seen by changed-file validation

Failure story: the PR adds a new validator and contract document, but local
validation only exercises the previously tracked installer test file. The branch
then appears locally validated while the new checker is untracked, untested, or
excluded from `make validate-changed`.

Disposition: FIXED.

Evidence: new files are staged with the PR diff:
`scripts/ci/check_python_dependency_surfaces.py`,
`tests/test_python_dependency_surfaces.py`, and
`docs/contracts/PYTHON_DEPENDENCY_SURFACES.md`. Focused pytest covered the new
validator, and `make validate-changed` was rerun after staging so the branch
diff did not silently skip the touched installer tests.

### PM-2023-002: PR-1 accidentally absorbs PR-2 package or Faraday churn

Failure story: while improving dependency architecture, the branch starts
regenerating Python locks, changing Ruff/Pillow pins, or editing the Ruby
Faraday lockfile. Review then cannot separate surface-contract policy from
actual package remediation, and the planned two-PR split collapses into a risky
mixed dependency PR.

Disposition: FIXED.

Evidence: this PR touches only scripts, tests, docs, and the
`verify_requirements.py` wrapper. No `requirements*.in`, `requirements*.txt`,
`constraints.txt`, `ios/Gemfile.lock`, Trivy suppression, or Faraday advisory
file is changed.

### PM-2023-003: `verify_requirements.py` remains a stale second authority

Failure story: the repo adds a better dependency-surface checker, but the old
`verify_requirements.py` parser keeps enforcing outdated production/dev/all
rules. Future agents and Dependabot lanes call the old script and get a false
pass or false failure unrelated to the canonical profile model.

Disposition: FIXED.

Evidence: `verify_requirements.py` now delegates to
`scripts/ci/check_python_dependency_surfaces.py`, and
`tests/test_verify_requirements.py` asserts that delegation instead of keeping a
second parser.

### PM-2023-004: The validator is not runnable as a repo-root script

Failure story: the validator imports repo modules successfully under pytest but
fails when run as `python scripts/ci/check_python_dependency_surfaces.py`
because Python sets `sys.path[0]` to `scripts/ci`. CI or local operators then
cannot use the documented command.

Disposition: FIXED.

Evidence: the validator inserts the resolved repo root into `sys.path` before
loading installer profile constants, and direct execution with
`python scripts/ci/check_python_dependency_surfaces.py` passes.

## Revised Plan

- Keep PR #2023 as PR-1 only: installer floor preservation, surface contract,
  validator, docs, and tests.
- Leave Faraday, Trivy suppression removal, Pillow duplicate cleanup, and Ruff
  lock regeneration for PR-2 after PR-1 merges.
- Treat `requirements-all.txt` and `requirements-lock.txt` as noncanonical
  aggregate install surfaces, not shared install profiles.
- Keep full local `make verify` deferred under the operator-approved
  machine-heavy exception; use focused tests, `make validate-changed`, and
  `pre-commit run --all-files`.

## Pre-Merge Checklist

- [x] Coordinator-first startup and declared pre-open role passes completed.
- [x] Premortem findings dispositioned in this artifact.
- [x] Focused dependency-surface and installer tests pass.
- [x] `make validate-changed` passes after staging new files.
- [x] Experiment Runner oracle-only evidence is recorded:
  `artifacts/orchestration/experiments/results/pr2023-dependency-surface-contract-oracle-result-v2.json`
  (`accepted`, `shared_tree_untouched=true`).
- [x] `pre-commit run --all-files` passes before push.
- [ ] Post-open QA, bug-hunter, security, Codex Security, and
  `pulseplate-pr-review` passes are repeated after push.
- [ ] Current-head CI and review-thread dispositions are inspected before any
  readiness claim.

## Decision

`proceed with changes`: the plan is acceptable with the revisions already
applied in this PR-1 diff and with PR-2 dependency-remediation work kept out.
