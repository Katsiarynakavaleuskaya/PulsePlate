# Main Docker gzip CVE Premortem

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Packet: `artifacts/orchestration/task_packets/66070820b5a9.json`
Branch: `codex/fix-main-docker-publish-gzip-cve-2026-41992`
Date: 2026-07-02

## Frame

It is 48 hours from now. This hotfix made the Docker publish lane worse while
trying to remediate `CVE-2026-41992`. We are looking backward to understand why.

This premortem is diff-first: a finding is useful only when it drives code/test
closure, or when the lane records a concrete stop-condition that prevents a
false readiness claim.

## Findings

### P1: The publish image path skipped the package-surface guard

Failure story: Pull-request CI proves `pulseplate:test` with
`check_docker_runtime_dependency_surface.py`, but the `publish` job builds a
separate production image path and then goes straight to Trivy. If a future
workflow edit changes tags, target, or build inputs, the publish image could
reintroduce `gzip` and only fail later as a scanner finding, after the guard
failed to give actionable package-inventory evidence.

Closure: FIXED in code. The `publish` job now runs
`check_docker_runtime_dependency_surface.py` against
`${{ steps.image-ref.outputs.ref }}` before the Trivy image scan, GHCR login,
push, SBOM, or attestations. The workflow contract test asserts that ordering
and the blocked `gzip` package argument.

### P1: The PR removed the Debian package but left a system gzip binary behind

Failure story: Trivy no longer reports the expected dpkg package state in the
runtime-surface check, but `/bin/gzip`, `gunzip`, or `zcat` still exists through
a base-image alias or unexpected package relationship. The PR appears locally
green while the published image still exposes the vulnerable command-line
surface.

Closure: FIXED. The Dockerfile production pruning block now fails closed if
`gzip`, `gunzip`, or `zcat` remains resolvable, and the Dockerfile contract test
guards the binary check.

### P1: Removing system gzip broke application-level compressed food-data handling

Failure story: The production image removes system `gzip`, but an app path
implicitly relied on the shell binary for `.gz` food-data artifacts. The publish
scan passes, but runtime OFF/FDC ingestion later fails.

Closure: FIXED. Existing app code uses Python stdlib `gzip`, and the Dockerfile
now runs a production-stage stdlib gzip round-trip smoke after pruning.

### P1: The lane claimed publish proof from PR checks that do not run publish

Failure story: The PR is called ready because pull-request Docker build checks
pass, but `.github/workflows/build.yml` skips `publish` on pull requests and
standalone `trivy.yml` is not PR-triggered. The real `main` publish lane stays
red after merge.

Closure: NOT-A-BUG with process evidence. The PR must state that pre-merge
image-level proof requires manual `trivy.yml` dispatch on the PR branch or must
remain post-merge `main` publish evidence. No readiness claim may cite ordinary
PR CI as publish proof.

### P2: The CVE was hidden with a broad suppression instead of remediated

Failure story: A future maintainer sees the open code-scanning alert and adds a
`.trivyignore` or Rego rule that suppresses `CVE-2026-41992` without removing the
vulnerable package, creating a permanent blind spot.

Closure: FIXED. This diff does not touch `.trivyignore` or `trivy/ignore-policy.rego`;
tests assert `CVE-2026-41992` and `gzip` are not broadly ignored, and the backlog
entry records production package removal as the disposition.

## Decision

Proceed with changes. The implementation is narrow and the identified failure
modes are closed by fail-closed Dockerfile assertions, workflow runtime-surface
guards, focused tests, and explicit PR evidence boundaries.

## Pre-Open Checklist

- Focused Docker/Trivy tests pass with the repo venv.
- `check_agent_consistency.py`, `make validate-changed`, and `pre-commit run --all-files` pass.
- Experiment Runner oracle-only evidence is produced after the coherent diff.
- PR body records that publish/#617 closure requires manual branch Trivy dispatch
  or post-merge main publish evidence.
