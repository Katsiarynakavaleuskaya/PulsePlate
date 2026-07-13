# PR #2113 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2113

Branch: `codex/ruby-3-4-release-toolchain`

## Summary

This PR migrates the privileged Fastlane release control plane from EOL Ruby
3.1 to exact Ruby 3.4.10, updates the pinned `ruby/setup-ruby` action required
to provide that runtime, adds exhaustive workflow ownership/version guards,
and aligns dormant Codecov metadata without changing the gem graph or upload
authority.

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass completed
- [ ] Codex Security exact-head diff scan completed
- [ ] `pulseplate-pr-review` completed
- [ ] Current-head CI completed
- [ ] Mandatory review wait-window and strict merge-readiness completed

## Fixed in Commit Mapping

No GitHub review findings have been dispositioned yet. Any actionable comment
must be classified as FIXED, NOT-A-BUG with evidence, or DEFERRED with a
backlog link before its thread is resolved.

## Pre-open Role and Premortem Evidence

### Agent Coordinator

Disposition: NOT-A-BUG
Evidence: The 10 implementation files plus this canonical fixed-mapping
artifact form one bounded Release/control-plane migration; they contain no
backend, OpenAPI, Python requirement, private-proxy, Fastfile, Gemfile, or
Gemfile.lock change.
Reason: The selected task class, scope, ordered role path, rollback, and current
CI stop conditions match repository governance.

### App Store Release Agent

Disposition: NOT-A-BUG
Evidence: All four active setup owners use the exact action SHA and Ruby
3.4.10; PR events reach validation only, while upload jobs remain manual and
fail closed on boolean, ref, environment, and secret gates.
Reason: No App Store submission behavior or release asset changed.

### Security Auditor

Disposition: NOT-A-BUG
Evidence: The pinned upstream action commit lists Ruby 3.4.10; there is no new
permission, `pull_request_target`, secret path, upload authority, or gem-source
change, and Dependabot alert #231 is confirmed fixed.
Reason: No actionable supply-chain or workflow-security defect remained.

### Marketing Strategist

Disposition: NOT-A-BUG
Evidence: The diff contains no App Store listing copy, screenshot,
localization, pricing, positioning, ASO, or user-facing claim change.
Reason: Codecov and workflow edits are release-control-plane metadata only.

### QA Engineer Agent

Disposition: NOT-A-BUG
Evidence: 150 focused toolchain, App Store workflow/validator, JWT/Fastlane,
CI-governance, and Trivy-expiry tests passed; Gemfile/lock remain unchanged.
Reason: No deterministic acceptance regression was found.

### Actual-diff Premortem

Disposition: FIXED
Commit: fb957acce9ec5d70c91fce18b848d97271c8f6b2
Evidence: `docs/security/CVE-2026-54171-excon-fastlane.md` now points to the
actual Fastlane/Excon guard, and
`docs/security/DEPENDABOT_ALERT_INVENTORY.md` labels its mixed-state table as
an alert status inventory.
Reason: Both bounded documentation inconsistencies were fixed before PR open;
the PR body records the required whole-PR rollback and App Store upload pause.

## Post-open Role Pass Evidence

### QA Engineer Agent

Disposition: FIXED
Commit: e38b445d94be95fa496619fa00c3df689ceff4ef1
Evidence: The backlog now points to open PR #2113 and accurately records the
in-progress implementation/review state; focused runtime-toolchain alignment
tests and the Gemfile/lock immutability check passed.

### Bug Hunter

Disposition: FIXED
Commit: e38b445d94be95fa496619fa00c3df689ceff4ef1
Evidence: Rebased proof now identifies `fb957acce9ec5d70c91fce18b848d97271c8f6b2`,
the backlog footer no longer says the migration is merely planned, and no stale
pre-rebase or TBD governance reference remains.

### Security Auditor

Disposition: NOT-A-BUG
Evidence: All four workflow owners use exact Ruby 3.4.10 and immutable
`ruby/setup-ruby@d45b1a4e94b71acab930e56e79c6aa188764e7f9`; no permission,
secret, trigger, upload-authority, Gemfile, or Gemfile.lock change exists, and
upload jobs remain manual and fail closed.
Reason: The ordered security pass found no actionable supply-chain or release
control-plane defect after the governance correction.

## Experiment Runner Evidence

Artifact:
`artifacts/orchestration/experiments/results/ruby-3-4-release-toolchain-oracle-result.json`
(local-only, gitignored)

- Accepted `oracle_only_governance_reviewer` result with 44 focused tests.
- `mutated_paths=[]`, `shared_tree_untouched=true`, and no promotion authority.
- Contribution kind `oracle_review`; commit uses the canonical Experiment
  Runner co-author trailer.

## Lane Start Provenance

Packet:
`artifacts/orchestration/task_packets/ruby_3_4_release_toolchain_current.json`
(local-only, gitignored)

The packet routed mandatory ordered roles and did not execute them implicitly.

## Validation Evidence

- PASS: scoped `python3 scripts/orchestration/check_preflight.py`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: 150 focused release-toolchain/App Store/JWT/workflow/Trivy tests.
- PASS: accepted isolated Experiment Runner 44-test oracle.
- PASS: unchanged `ios/Gemfile` and `ios/Gemfile.lock`.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files`.
- PASS: pre-push pip-audit, backend tests, and full-repo Bandit.
- Not run: local `make verify`, per repository machine-budget policy.

## Merge Readiness

Not claimed. Current-head CI, post-open role passes, Codex Security,
PulsePlate PR review, review-bot/thread disposition, the mandatory wait window,
and strict authenticated merge-readiness must pass first.

## Deferred / Follow-ups

None inside this Ruby migration. Caddy provenance, Coverage, PyArrow,
pgvector, and BOLA remain separate epic lanes.
