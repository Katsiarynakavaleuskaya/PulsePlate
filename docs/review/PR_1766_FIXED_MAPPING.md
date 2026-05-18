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
  - `8751b49584c375bedd4fd640f0247221560fa98a` - aligned the Rego predicate
    with Trivy 0.69.3 Bundler policy input fields.
  - `5053d698bc8b69655e471abb2918497bf2b81063` - clarified single file-level
    expiry handling and normalized `PkgID` wording.
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
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1766#pullrequestreview-4313494312 -> dd24159e3a6f099b6f7334098baae275e65459c7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1766#discussion_r3261793183 -> dd24159e3a6f099b6f7334098baae275e65459c7

Disposition: FIXED
Commit: 5053d698bc8b69655e471abb2918497bf2b81063
Evidence: Sourcery found inconsistent `package id` wording in the security note. `docs/security/CVE-2026-45363-jwt-fastlane.md` now uses explicit `PkgID` wording for the Trivy field.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1766#pullrequestreview-4313559314 -> 5053d698bc8b69655e471abb2918497bf2b81063
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1766#discussion_r3261847247 -> 5053d698bc8b69655e471abb2918497bf2b81063

Disposition: NOT-A-BUG
Evidence: `trivy/ignore-policy.rego:10` documents that CI enforces a single file-level expiry marker; `trivy/ignore-policy.rego:12` has the required `Suppression expires: 2026-05-27` marker; `scripts/ci/check_trivy_ignore_policy_expiry.py:21` rejects multiple markers with `expected exactly one expiry per policy file`; `trivy/ignore-policy.rego:435` now notes that expiry is governed by the single file-level marker.
Reason: CodeRabbit requested a second block-level `Suppression expires:` marker for the JWT rule, but adding it would break the canonical expiry checker. The current file-level expiry is the repo-approved policy format.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1766#pullrequestreview-4313617562
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1766#discussion_r3261895753

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
  `dd24159e3a6f099b6f7334098baae275e65459c7`; one expiry-format thread
  dispositioned as NOT-A-BUG because the requested second expiry marker would
  violate the repo's exactly-one-expiry checker.
- Sourcery: wording nit fixed in `5053d698bc8b69655e471abb2918497bf2b81063`;
  stale PkgPath helper comment was superseded by
  `8751b49584c375bedd4fd640f0247221560fa98a`.
- Cubic: no issues found in the current review pass.

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
  `8751b49584c375bedd4fd640f0247221560fa98a`; no runtime behavior changed.

## Merge Readiness

- [x] Pre-flight + agent consistency: PASS.
- [x] Canonical artifact: this file (`docs/review/PR_1766_FIXED_MAPPING.md`).
- [x] PR body mirror: PASS.
- [ ] Current-head CI: pending terminal current-head checks after the latest
  governance commit.
- [x] Bot summaries reviewed (CodeRabbit / Sourcery / Cubic): no open
  actionables after disposition.
- [x] Strict review-thread disposition: PASS
  (`check_review_threads_disposition.py --require-auth`).
- [x] Strict merge-readiness review governance: PASS
  (`check_pr_merge_readiness.py --pr-number 1766 --repo Katsiarynakavaleuskaya/PulsePlate`).

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-jwt-cve-2026-45363`
