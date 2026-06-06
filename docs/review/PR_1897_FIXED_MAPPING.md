# PR 1897 Fixed in Commit Mapping

## Scope

This PR updates the iOS app target bundle identifier and matching local
Fastlane bundle identifier fallbacks to the Apple Developer registered
identifier `com.kavaleuskaya.pulseplate`.

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

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Initial implementation review mapping completed for the app target bundle
  identifier change.
- [x] Post-open Codex review finding on Fastlane snapshot bundle identifier
  fallback was fixed and mapped.
- [x] Stale squash-preview Codex review findings were dispositioned with
  current-branch ancestry and trailer evidence.
- Post-open review remains active; this artifact will be updated for any new
  actionable review findings.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b48a16a0ec920700aa38a431c260060940ff4926
Evidence: `ios/PulsePlate.xcodeproj/project.pbxproj` changes exactly the Debug and Release app target `PRODUCT_BUNDLE_IDENTIFIER` values from `com.katsiaryna.pulseplate.dev` to `com.kavaleuskaya.pulseplate`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1897

Disposition: FIXED
Commit: 264e2d2863b0b3b56f98f143c2bd106875d92eea
Evidence: `ios/fastlane/Fastfile` and `ios/fastlane/Appfile` now use `com.kavaleuskaya.pulseplate` as their local bundle identifier fallback while preserving CI fail-closed `APP_STORE_BUNDLE_IDENTIFIER` behavior for protected App Store lanes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1897#discussion_r3367169317 -> 264e2d2863b0b3b56f98f143c2bd106875d92eea

Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor 264e2d2863b0b3b56f98f143c2bd106875d92eea HEAD` passed locally on `codex/ios-bundle-id-registration-v1`; the Fastlane fix commit is reachable from the current branch head.
Reason: The review comment was based on stale squash-preview commit `a7e0117e`. The current PR branch is linear and retains the mapped Fastlane fix commit in ancestry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1897#discussion_r3367857456

Disposition: NOT-A-BUG
Evidence: `git log -1 --format=%B b48a16a0ec920700aa38a431c260060940ff4926` includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
Reason: The Experiment Runner materially shaped the initial implementation commit, and that commit carries the governed trailer. Later mapping/checklist commits were review-governance maintenance and not material Experiment Runner outputs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1897#discussion_r3367857457

Disposition: NOT-A-BUG
Evidence: `python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1897 --require-auth` passed locally with all resolved threads mapped against the real PR branch history.
Reason: The review comment uses a synthetic squash-preview commit as its ancestry model. Repo merge-readiness and disposition guards validate the actual PR branch checkout and reachable branch commits.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1897#discussion_r3367905576

Disposition: NOT-A-BUG
Evidence: `git log -1 --format=%B b48a16a0ec920700aa38a431c260060940ff4926` includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
Reason: The governed Experiment Runner attribution applies to the commit materially shaped by the runner. The connector's synthetic squash-preview commit is not the repo branch commit used by local disposition proof.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1897#discussion_r3367905578

## Implementation Evidence

- Implementation commit: `b48a16a0ec920700aa38a431c260060940ff4926`
- Fastlane alignment commit: `264e2d2863b0b3b56f98f143c2bd106875d92eea`
- Evidence:
  - `ios/PulsePlate.xcodeproj/project.pbxproj`
  - `ios/fastlane/Fastfile`
  - `ios/fastlane/Appfile`

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
- Co-author trailer is present on
  `b48a16a0ec920700aa38a431c260060940ff4926`.
- Rejected/not-used artifact: `artifacts/orchestration/experiments/results/exp-6b9f53104928.json`
  was rejected because the runner temp checkout lacked the shared `.venv` for
  `make validate-changed`; it is not used as PR evidence.

## Tests

- PASS: `python3 scripts/orchestration/check_preflight.py --path ios/PulsePlate.xcodeproj/project.pbxproj`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `/usr/bin/plutil -lint ios/PulsePlate.xcodeproj/project.pbxproj ios/PulsePlate/Info-Release.plist`
- PASS: `ruby -c ios/fastlane/Fastfile && ruby -c ios/fastlane/Appfile`
- PASS: `.venv/bin/python -m pytest -q tests/test_ios_appstore_assets_workflow_contract.py tests/test_ios_appstore_asset_validators.py`
- PASS: `xcodebuild -list -project ios/PulsePlate.xcodeproj`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files` with repo root `.venv/bin` on PATH
- PASS: pre-push hooks, including backend pre-push tests and full-repo Bandit

## Release Notes

- Protected `APP_STORE_BUNDLE_IDENTIFIER` / Fastlane environment configuration
  remains operator-owned and must be set to `com.kavaleuskaya.pulseplate`
  before any protected App Store upload.
- This PR does not claim protected upload readiness.

## Merge Readiness

- Not claimed.
- Current-head CI, bot/no-actionable checks, unresolved-thread checks, strict
  merge wrapper with auth, and wait-window remain pending.
