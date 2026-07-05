# Trivy Ignore Policy Production Premortem

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Task packet: `artifacts/orchestration/task_packets/9dcf5d232ef5.json`
Branch: `codex/fix-trivy-ignore-policy-expiry`
Date: 2026-07-05

## Summary

This PR changes security scanning policy for the production Docker image and
iOS release-tooling dependency evidence. It removes the resolved Faraday
scanner-lag suppression, keeps only exact residual Debian base-image
suppressions, and refreshes source-backed evidence.

Frame: it is 48 hours after this hotfix merged. Production release confidence
got worse. We are looking backward to understand why.

## Production Safety Baseline

- Product runtime code, API contracts, billing, auth, data flows, and iOS app
  binary code are not changed.
- The production-sensitive surface is scan policy: a bad change can either hide
  a real image vulnerability or block deploy/release with a false positive.
- Fastlane/Faraday is privileged release tooling, not shipped product runtime,
  but it still affects release availability and operator trust.
- The fail-closed Trivy gate must stay strict: no broad `.trivyignore`, no
  catch-all Rego rules, and no date-only suppression extension.

## Scope

- `trivy/ignore-policy.rego`
- `tests/test_trivy_ignore_policy_expiry.py`
- `docs/security/CVE-2026-54297-faraday-fastlane.md`
- `docs/security/CVE-2026-27171-zlib1g.md`
- `docs/security/CVE-2026-3184-util-linux.md`
- `docs/security/CVE-2025-69720-ncurses.md`
- `docs/security/DEPENDABOT_ALERT_INVENTORY.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

Out of scope: Dependabot PR #2078 pyarrow, Dependabot PR #2077 testing group,
Python lockfiles, Dockerfile changes, workflow policy changes, and broad
`.trivyignore` entries.

## Failure Mode 1: Real Production Image CVE Gets Hidden

Failure story: an expired suppression is refreshed as a calendar bump instead
of being rechecked against the production image. A future base-image scan still
contains a real zlib, util-linux, or ncurses finding, but the policy suppresses
more than the exact package/version tuple. CI looks clean, the image can ship,
and the team loses the signal that the base image needs an upstream fix or image
refresh.

Underlying assumption: an old suppression remains safe because it was once
reviewed.

Early warning signs:

- Rego rules match CVE/package names without installed version and package ID.
- `.trivyignore` gains new entries for this lane.
- Image scan without policy is not captured before a suppression is retained.

Containment action: keep only exact OS-package rules, require image scan
evidence without the policy, and keep short expiry windows.

Disposition: FIXED. The Faraday rule was removed. The remaining zlib,
util-linux, and ncurses suppressions retain exact package/version/package-ID
scope, and local production-image Trivy evidence shows those findings still
exist without `trivy/ignore-policy.rego`.

## Failure Mode 2: Release Pipeline Blocks on a False Positive

Failure story: the team deletes all expired policy blocks because one
scanner-lag finding disappeared. The next production-image or filesystem scan
goes red on unfixed Debian base-image CVEs. The release path is blocked even
though Debian bookworm still has no actionable package update for the affected
runtime packages. Under time pressure, someone is tempted to add broad ignore
entries or bypass the gate.

Underlying assumption: removing suppressions is always safer than retaining
them.

Early warning signs:

- `trivy image --severity HIGH,CRITICAL` without policy reports ncurses but the
  policy no longer contains the exact ncurses tuple.
- All-severity image scan still reports zlib/util-linux, but docs claim those
  CVEs are resolved.
- PR discussion shifts from evidence-backed exceptions to "make Trivy green".

Containment action: separate removable scanner lag from active residual
base-image risk, keep the gate fail-closed, and document upstream removal
conditions.

Disposition: FIXED. The retained OS suppressions are documented as residual
Debian base-image risk, not resolved vulnerabilities, and the review window is
shortened to 2026-07-12.

## Failure Mode 3: Fastlane Tooling Risk Is Misclassified

Failure story: the local Trivy database stops reporting Faraday, so the PR marks
the release-tooling alert resolved without checking the actual lockfile and
advisory. If the lock had drifted below Faraday 1.10.6, iOS release tooling
would retain a DoS risk in privileged automation. The product runtime still
would not ship Faraday, but release availability and operator trust would be
weaker.

Underlying assumption: scanner silence proves dependency safety.

Early warning signs:

- `ios/Gemfile.lock` no longer has `faraday (1.10.6)` while docs still say the
  alert is resolved.
- Fastlane changes appear in the same diff without a focused release-tooling
  review.
- GitHub Dependabot still reports `GHSA-98m9-hrrm-r99r` after refresh.

Containment action: pin resolution to the lockfile and advisory, not only the
scanner result; keep the lane independent from broad Fastlane churn.

Disposition: FIXED. The lock remains on Faraday 1.10.6, the GitHub advisory
lists 1.10.6 as patched, and the test suite prevents reintroducing a Faraday
suppression in either Rego or `.trivyignore`.

## Failure Mode 4: Local Evidence Diverges From GitHub Current-Head Truth

Failure story: local Trivy v0.71.2 says the policy is correct, but GitHub
code-scanning or Dependabot alert state lags or uses different metadata. The PR
claims production security closure before current-head CI and GitHub security
surfaces confirm it. This creates false merge confidence and hides a release
blocker until late review.

Underlying assumption: local scanner evidence is equivalent to GitHub alert
state.

Early warning signs:

- Local `gh api` cannot list code-scanning or Dependabot alerts.
- PR body says "GitHub alerts closed" before current-head CI runs.
- A required or advisory security check reports a different head SHA.

Containment action: state local evidence precisely, record the alert API access
limitation, and require current-head CI/security evidence before merge
readiness.

Disposition: FIXED for pre-open scope. Local `gh` has repo admin access but the
security-alert REST endpoints returned HTTP 404, so this PR must not claim
GitHub alert closure before current-head GitHub evidence is available.

## Hidden Assumption

The hidden assumption is that this is a "Trivy date bump" task. It is actually a
production security signal-control task: every retained suppression must prove
why hiding that finding is safer than blocking release, and every removed
suppression must prove the finding is no longer active or no longer applicable.

## Revised Plan

1. Keep this PR as a production security hotfix, not a dependency update lane.
2. Remove only the resolved Faraday scanner-lag rule.
3. Retain zlib/util-linux/ncurses only with exact package/version/package-ID
   scope and a 2026-07-12 review window.
4. Use Docker/Trivy v0.71.2 image evidence to justify retained OS-package
   suppressions.
5. Record that GitHub security-alert closure is a current-head CI/browser
   follow-up, not a local claim from an unavailable REST endpoint.

## Production Pre-Merge Checklist

- Production image builds from the same Dockerfile path used by CI.
- Trivy v0.71.2 image scan without policy still reports retained OS CVEs.
- Trivy v0.71.2 image scan with policy has zero HIGH/CRITICAL findings for the
  retained production-image context.
- Trivy filesystem/iOS scan without policy does not report Faraday
  `CVE-2026-54297`.
- `ios/Gemfile.lock` remains on Faraday 1.10.6.
- Current-head GitHub CI/security checks are inspected before merge readiness.
- No broad `.trivyignore` entries or fail-open workflow changes are introduced.

## Decision

Proceed with changes. The production risk is reduced by removing a resolved
scanner-lag suppression while keeping exact residual base-image suppressions
that are still active in the production-image scan. Merge readiness is not
claimed until current-head GitHub CI, GitHub security surfaces, post-open role
passes, Codex Security, and fixed mapping are complete.
