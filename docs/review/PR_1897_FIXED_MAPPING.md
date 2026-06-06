# PR 1897 Fixed in Commit Mapping

## Scope

This PR updates only the iOS app target bundle identifier to the Apple
Developer registered identifier `com.kavaleuskaya.pulseplate`.

Out of scope: certificates, provisioning profiles, secrets, Fastlane protected
environment changes, App Store Connect upload authority, metadata, screenshots,
OpenAPI, backend, web, runtime behavior, `Info-Release.plist` churn, and Xcode
project recovered-reference noise.

## Lane Start Provenance

- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/ios-bundle-id-registration-v1`
- Base: `origin/main` at `ec44f6e57feccccffd1d62cbe6c6e227b6e9057e`
- Packet: `artifacts/orchestration/task_packets/78e32bf68da6.json`
- Required pre-open role order completed:
  `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> backend-engineer -> frontend-engineer -> creative-designer`

## Discussion Thread Pass

- [x] Discussion-thread pass completed for initial PR open; no unresolved review
  threads were present when this artifact was created.
- [x] Fixed in commit mapping completed for the initial implementation commit.
- Post-open review remains active; this artifact will be updated for any new
  actionable review findings.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b48a16a0ec920700aa38a431c260060940ff4926
Evidence: `ios/PulsePlate.xcodeproj/project.pbxproj` changes exactly the Debug and Release app target `PRODUCT_BUNDLE_IDENTIFIER` values from `com.katsiaryna.pulseplate.dev` to `com.kavaleuskaya.pulseplate`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1897

## Implementation Evidence

- Implementation commit: `b48a16a0ec920700aa38a431c260060940ff4926`
- Evidence:
  - `ios/PulsePlate.xcodeproj/project.pbxproj`

## Premortem Findings

- Disposition: FIXED
  Evidence: PR diff changes only the app target bundle identifier lines.
- Disposition: FIXED
  Evidence: `ios/PulsePlate/Info-Release.plist` is unchanged.
- Disposition: FIXED
  Evidence: no `Recovered References` or Xcode project group churn appears in
  the implementation diff.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-9a0d84974fe4.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution kind: `oracle_review`
- `shared_tree_untouched`: `true`
- `source_diff_applied`: `true`
- `promotion_ready`: `false`
- `coauthor_required`: `true`
- Co-author trailer is present on
  `b48a16a0ec920700aa38a431c260060940ff4926`.
- Rejected/not-used artifact: `artifacts/orchestration/experiments/results/exp-6b9f53104928.json`
  was rejected because the runner temp checkout lacked the shared `.venv` for
  `make validate-changed`; it is not used as PR evidence.

## Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --path ios/PulsePlate.xcodeproj/project.pbxproj`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `/usr/bin/plutil -lint ios/PulsePlate.xcodeproj/project.pbxproj ios/PulsePlate/Info-Release.plist`
- PASS: `xcodebuild -list -project ios/PulsePlate.xcodeproj`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files` with repo root `.venv/bin` on PATH
- PASS: pre-push hooks, including backend pre-push tests and full-repo Bandit

## Release Notes

- Protected `APP_STORE_BUNDLE_IDENTIFIER` / Fastlane environment configuration
  remains operator-owned and must be aligned to `com.kavaleuskaya.pulseplate`
  before any protected App Store upload.
- This PR does not claim protected upload readiness.

## Merge Readiness

- Not claimed.
- Current-head CI, bot/no-actionable checks, unresolved-thread checks, strict
  merge wrapper with auth, and wait-window remain pending.
