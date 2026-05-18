<!-- markdownlint-disable MD013 MD034 -->
# PR 1766 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1766>
- Branch: `codex/security-jwt-cve-2026-45363`
- Title: `fix(security): scope jwt CVE suppression`
- Implementing commits:
  - `9df304969f34712868223eadd75151206ecf07fb` - added the initial
    temporary Trivy suppression, security note, and backlog removal item.
  - `dd24159e3a6f099b6f7334098baae275e65459c7` - added direct CVE/GHSA
    tracker references and Dependabot alert #142 evidence.
  - `8751b4958c0f3f432bd75f9860abbd37770f8533` - aligned the Rego predicate
    with Trivy 0.69.3 Bundler policy input fields.
- Scope: Trivy suppression governance for Ruby `jwt` CVE-2026-45363 in
  `ios/Gemfile.lock` release tooling only. No `.trivyignore`, lockfile,
  workflow, runtime backend, frontend, OpenAPI, iOS app binary, auth, billing,
  quota, or deployment behavior changed.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Initial post-open governance pass found one actionable CodeRabbit review thread,
fixed and mapped below. External CodeRabbit, Sourcery, and Cubic reviews remain
merge-blocking until their current-head statuses are terminal and reviewed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: dd24159e3a6f099b6f7334098baae275e65459c7
Evidence: CodeRabbit found that the new Trivy suppression block referenced Fastlane and jwt version pages but lacked a direct CVE tracker URL. The suppression block now includes `https://avd.aquasec.com/nvd/cve-2026-45363` and `https://github.com/advisories/GHSA-c32j-vqhx-rx3x`; the security note and ledger also link GitHub Dependabot alert #142 for the same `jwt` / `ios/Gemfile.lock` advisory.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1766#discussion_r3261793183 -> dd24159e3a6f099b6f7334098baae275e65459c7

## Role-Agent Findings

Disposition: FIXED
Commit: 9df304969f34712868223eadd75151206ecf07fb
Evidence: `bug-hunter` found that a CVE-only `.trivyignore` entry would be too
broad. The PR does not modify `.trivyignore`; `trivy/ignore-policy.rego` now
scopes the suppression to CVE-2026-45363, package `jwt`, installed version
`2.10.2`, fixed version `3.2.0`, `PkgID` `jwt@2.10.2`, PURL
`pkg:gem/jwt@2.10.2`, and primary advisory URL
`https://avd.aquasec.com/nvd/cve-2026-45363`.

Disposition: FIXED
Commit: 9df304969f34712868223eadd75151206ecf07fb
Evidence: `security-auditor` required temporary risk acceptance to remain
documented and removable. `docs/security/CVE-2026-45363-jwt-fastlane.md`
records the resolver blocker, release-tooling risk, monitor links, review
target, and removal condition; `docs/roadmap/BACKLOG_LEDGER.md` tracks the
follow-up removal DoD.

Disposition: NOT-A-BUG
Evidence: `app-store-release-agent` confirmed that this dependency is release
tooling, not iOS app binary runtime, and that local validation should not claim
protected App Store upload success.
Reason: The PR body and security note explicitly limit local Fastlane evidence
to no-auth metadata validation.

Disposition: NOT-A-BUG
Evidence: Codex Security diff-focused scan found no new reportable finding in
the diff. Artifact:
`/tmp/codex-security-scans/BMI-App_2025_clean/jwt_cve_2026_45363_20260518T200205Z/report.md`.
Reason: The patch adds no executable runtime code, no secrets, no auth/network
path, and no global suppression.

Disposition: FIXED
Commit: 9df304969f34712868223eadd75151206ecf07fb
Evidence: `pulseplate-premortem-risk-review` identified broad suppression and
stale risk acceptance as the likely failure modes. The Rego rule is scoped to
exact CVE, package, installed version, fixed version, PURL, and primary
advisory URL fields; the policy file keeps the shared 2026-05-27 expiry, and
the ledger entry requires removal once Fastlane permits `jwt >= 3.2.0` or the
release tooling no longer depends on Fastlane's `jwt` 2.x graph.

## Bot Review Notes

- CodeRabbit: one actionable thread fixed in
  `dd24159e3a6f099b6f7334098baae275e65459c7`; pending current-head terminal
  review after latest push.
- Sourcery: pending current-head terminal review.
- Cubic: pending current-head terminal review.

## Local Validation

- `.venv/bin/python scripts/orchestration/check_preflight.py` - PASS.
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py` - PASS.
- `.venv/bin/python scripts/ci/check_trivy_ignore_policy_expiry.py` - PASS.
- `.venv/bin/python scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-45363-jwt-fastlane.md docs/roadmap/BACKLOG_LEDGER.md` - PASS.
- `trivy 0.69.3 fs --scanners vuln --severity HIGH,CRITICAL --ignore-policy trivy/ignore-policy.rego --format json ios` - PASS; no `jwt` / `CVE-2026-45363` findings remained after the exact-field policy update.
- `cd ios && bundle check` - PASS.
- `cd ios && bundle exec fastlane validate_metadata_package` - PASS.
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS; no Python files changed.
- `pre-commit run --all-files` - PASS.
- Pre-push hook PASS: pip-audit, backend pre-push tests, and full-repo Bandit.

### Machine-heavy / operator-approved narrow gate

- Full local `make verify` is deferred per the operator-approved machine-safe
  policy and root `AGENTS.md` machine-heavy PR exception. This PR uses focused
  local gates plus current-head GitHub CI as the heavy matrix/security signal.

## Security Notes

- This is temporary release-tooling risk acceptance, not a full vulnerability
  remediation.
- The suppression must be removed once Fastlane permits `jwt >= 3.2.0` or iOS
  release tooling no longer depends on the Fastlane `jwt` 2.x graph.
- Current-head Trivy/GitHub Code Scanning evidence is required before any
  merge-ready claim.

## Risks / Rollback

- Risk: Trivy's Bundler policy input shape changes again and the exact
  package/advisory predicate no longer matches. This should fail current-head
  security-scan rather than silently over-suppress.
- Rollback: revert implementing commits `9df304969f34712868223eadd75151206ecf07fb`,
  `dd24159e3a6f099b6f7334098baae275e65459c7`, and
  `8751b4958c0f3f432bd75f9860abbd37770f8533`; no runtime behavior changed.

## Merge Readiness

- [x] Pre-flight + agent consistency: PASS.
- [x] Canonical artifact: this file (`docs/review/PR_1766_FIXED_MAPPING.md`).
- [x] PR body mirror: PASS.
- [ ] Current-head CI: pending terminal current-head checks.
- [ ] Bot summaries reviewed (CodeRabbit / Sourcery / Cubic): pending terminal statuses.
- [ ] Strict review-thread disposition: pending `check_review_threads_disposition.py --require-auth`.
- [ ] Strict merge readiness: pending `check_merge_ready.py --require-auth`.

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-jwt-cve-2026-45363`
