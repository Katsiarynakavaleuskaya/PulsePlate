# PR #2062 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2062

Branch: `codex/fix-main-docker-publish-gzip-cve-2026-41992`

## Summary

This PR removes Debian `gzip` from the final production Docker image surface to
remediate Trivy `CVE-2026-41992` without `.trivyignore` or Rego suppression. It
adds fail-closed package/binary assertions, build/publish/standalone Trivy
runtime-surface guards, focused tests, a production package-removal disposition,
backlog tracking, and a diff-first premortem with code closures.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [x] CodeRabbit actionable review comments checked and dispositioned.
- [x] Sourcery actionable review comments checked and dispositioned.
- [x] Cubic actionable review comments checked and dispositioned.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2062#pullrequestreview-4615936341 -> b7353977e414f88840bb9c13c764726ce71cd662
Disposition: FIXED
Commit: b7353977e414f88840bb9c13c764726ce71cd662
Evidence: The review-level CodeRabbit summary contained three actionable items. `docs/roadmap/BACKLOG_LEDGER.md` now targets PR #2062, `docs/security/CVE-2026-41992-gzip.md` now has concrete file:line anchors, and `.github/workflows/build.yml` now passes the publish image reference through `env: IMAGE_REF` before the shell `run:` block. `tests/test_docker_workflow_build_path_contract.py` asserts the env binding and forbids `steps.image-ref.outputs.ref` inside that runtime-surface guard script.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2062#pullrequestreview-4616005241 -> d5e1f60c25cbedd7bc2471d723340330498073d1
Disposition: FIXED
Commit: d5e1f60c25cbedd7bc2471d723340330498073d1
Evidence: The later CodeRabbit review-level summary requested concrete fixed-mapping entries. `docs/review/PR_2062_FIXED_MAPPING.md` now lists each actionable CodeRabbit thread with disposition-specific proof and post-comment commit SHAs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2062#discussion_r3511718210 -> 5583e6f337156606d1f681f9e74b17fbc9e222ce
Disposition: FIXED
Commit: 5583e6f337156606d1f681f9e74b17fbc9e222ce
Evidence: `docs/security/CVE-2026-41992-gzip.md` now cites concrete `file:line` anchors for Dockerfile package pruning, build/publish/trivy workflow guards, runtime-surface tests, and no-suppression tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2062#discussion_r3511718203 -> 95428f1d98820893000c60f48258381bc3bbd262
Disposition: FIXED
Commit: 95428f1d98820893000c60f48258381bc3bbd262
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` now records `Target PR: PR #2062` with the PR URL and keeps the branch slug in a separate `Branch:` field.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2062#discussion_r3511776681 -> d5e1f60c25cbedd7bc2471d723340330498073d1
Disposition: FIXED
Commit: d5e1f60c25cbedd7bc2471d723340330498073d1
Evidence: `docs/review/PR_2062_FIXED_MAPPING.md` replaced the no-actionable sentinel with concrete CodeRabbit review-thread mappings and disposition proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2062#pullrequestreview-4615879762
Disposition: NOT-A-BUG
Evidence: Sourcery posted a rate-limit notice, not actionable code-review feedback for this diff. The PR status context reports `Sourcery review` as pass, and no Sourcery code comments require code or documentation changes.

- Cubic status check: https://www.cubic.dev/pr/Katsiarynakavaleuskaya/PulsePlate/pull/2062
Disposition: NOT-A-BUG
Evidence: Cubic exposed a neutral/skipped status check and no actionable review comments in the GitHub PR review/comment surfaces inspected for PR #2062.

## Role-Agent Finding Dispositions

Disposition: FIXED
Source: post-open `qa-engineer-agent`
Evidence: This artifact adds the missing canonical mapping file required by PR
Phase2 and merge-readiness governance for PR #2062.

Disposition: FIXED
Source: post-open `qa-engineer-agent`
Evidence: `docs/security/CVE-2026-41992-gzip.md` now uses concrete `file:line`
evidence anchors for Dockerfile package pruning, build/publish/trivy workflow
guards, runtime-surface tests, and no-suppression tests.

Disposition: NOT-A-BUG
Source: post-open `qa-engineer-agent`
Evidence: The QA pass found no actionable test-adequacy issue for the Docker
`gzip` behavior. It confirmed that PR body evidence boundaries are truthful:
ordinary PR CI is not cited as publish proof, and image-level proof remains
manual branch `trivy.yml` dispatch or post-merge `main` publish evidence.

Disposition: NOT-A-BUG
Source: pre-open and post-open `bug-hunter`
Evidence: The final diff keeps the publish image guard before Trivy, GHCR login,
push, SBOM, and attestations, and the premortem/backlog/security docs keep the
same no-suppression disposition. No actionable bug-hunter finding remains after
the security-doc anchor fix.

Disposition: NOT-A-BUG
Source: pre-open and post-open `security-auditor`
Evidence: The final diff removes `gzip` from the production package surface,
checks Debian package absence, checks `gzip`/`gunzip`/`zcat` binary absence,
keeps Python stdlib `gzip` smoke coverage, and does not add `.trivyignore` or
`trivy/ignore-policy.rego` suppression.

Disposition: NOT-A-BUG
Source: Codex Security diff scan / finding discovery
Evidence: Codex Security scan `b126c050-0cc0-4070-ab1f-c83d66b76b59` completed
with 0 findings and 10/10 diff surfaces covered. The scan focused on
production-image package surface, publish workflow ordering before GHCR push,
scanner suppression surfaces, and truthful evidence boundaries.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-f8a00f94aae2.json`
- Experiment ID: `exp-f8a00f94aae2`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Source diff applied: true
- Oracles: 3/3 passed
- Co-author required: yes, `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Premortem Code Closure

- `docs/review/PR_MAIN_DOCKER_GZIP_CVE_PREMORTEM.md` records the concrete
  production failure story that publish could build a separate image path
  without the runtime dependency-surface guard.
- `.github/workflows/build.yml` closes that risk in code by checking
  `${{ steps.image-ref.outputs.ref }}` before Trivy, GHCR login, push, SBOM, or
  attestations.
- `tests/test_docker_workflow_build_path_contract.py` asserts the publish guard
  ordering and `--blocked-debian-package gzip` argument.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/66070820b5a9.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`

## Merge Readiness

Not claimed. This artifact records post-open dispositions and local evidence
only. Current-head PR CI, manual branch `trivy.yml` image-level proof or
post-merge `main` publish evidence, and final review-bot disposition checks
must complete before any readiness language.
