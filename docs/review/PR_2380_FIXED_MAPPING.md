# PR 2380 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/a79f914c550e.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/ios-v5-catalog-fix-v10.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 698a2b90922bbfa64443e812274a5fca9da78e82
Evidence: ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:199 explicitly checks runtime-output hashes and paired canonical records; docs/design/FITCHEF_MASCOT_ASSET_CANON.md separates external source provenance from checked-in output proof.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#discussion_r3936821695 -> 698a2b90922bbfa64443e812274a5fca9da78e82

Disposition: FIXED
Commit: 698a2b90922bbfa64443e812274a5fca9da78e82
Evidence: ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:57 verifies frozen PNG/JPEG metadata, encoding and exact ICC payload; full iOS tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#discussion_r3936821712 -> 698a2b90922bbfa64443e812274a5fca9da78e82

Disposition: FIXED
Commit: eb0bfc246a681d6da6ba9a15847891f4a3f2a721
Evidence: ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:199 parses one six-column canonical row for the same runtime path and compares its exact output hash.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#discussion_r3936839884 -> eb0bfc246a681d6da6ba9a15847891f4a3f2a721

Disposition: FIXED
Commit: eb0bfc246a681d6da6ba9a15847891f4a3f2a721
Evidence: ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:222 scans every regular non-symlink app Swift file for bounded literal references and checks the sole approved owner and RootTabs exclusion.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#discussion_r3936839899 -> eb0bfc246a681d6da6ba9a15847891f4a3f2a721

Disposition: FIXED
Commit: 341506f74d731b27fbd37662bf08d4f70df34b7d
Evidence: docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md:61 and ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:154 bind seven semantic imagesets with exact 1x/2x/3x inventories; native iPhone and iPad lookup passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#discussion_r3937351044 -> 341506f74d731b27fbd37662bf08d4f70df34b7d

Disposition: FIXED
Commit: 9702f5eab9f2aaed8287bffcb66f90229b0cc772
Evidence: ios/PulsePlate/Views/PlateView.swift:338 uses ppRequiredBundleAsset with the semantic catalog key; the other four owners share that boundary; IOSREL2V5AssetParityTests.swift:259 rejects direct catalog-image bypasses. Full iOS 286 XCTest plus 13 Swift Testing and Release iPad 10 tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#discussion_r3937782094 -> 9702f5eab9f2aaed8287bffcb66f90229b0cc772

Disposition: FIXED
Commit: 05252469ec2257bcf88f18bfca8b98e8a5c41c3a
Evidence: ios/PulsePlate/Views/Home/HomeExperience.swift:371 and :562 share one presentation size selector across both arrangements; ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:12 tests compact/regular by normal/Accessibility cases. Full 287 XCTest plus 13 Swift tests pass and the normal compact native frame shows the portrait hero.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#discussion_r3937939415 -> 05252469ec2257bcf88f18bfca8b98e8a5c41c3a

Disposition: FIXED
Commit: 2e213a6d32d0629ec0e2e048a726b51b5f3d8773
Evidence: ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:261 positively requires the admitted initializer at each known owner; :283 covers decorative, bundle-argument, UIImage and multiline bypass spellings; :782 normalizes formatting for that bounded call shape. Full 288 XCTest plus 13 Swift Testing tests and all-files pre-commit pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#discussion_r3937955331 -> 2e213a6d32d0629ec0e2e048a726b51b5f3d8773

Disposition: FIXED
Commit: 698a2b90922bbfa64443e812274a5fca9da78e82
Evidence: ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:57 and :180 address both source-proof scope and metadata/encoding findings from this review.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#pullrequestreview-5116548136 -> 698a2b90922bbfa64443e812274a5fca9da78e82

Disposition: FIXED
Commit: eb0bfc246a681d6da6ba9a15847891f4a3f2a721
Evidence: ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:199 and :203 fix both canonical association and cross-file owner census findings from this review.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#pullrequestreview-5116567453 -> eb0bfc246a681d6da6ba9a15847891f4a3f2a721

Disposition: FIXED
Commit: 341506f74d731b27fbd37662bf08d4f70df34b7d
Evidence: docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md:61 and ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:154 implement the dedicated catalog packaging requested in the associated inline finding.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#pullrequestreview-5117130238 -> 341506f74d731b27fbd37662bf08d4f70df34b7d

Disposition: FIXED
Commit: 9702f5eab9f2aaed8287bffcb66f90229b0cc772
Evidence: ios/PulsePlate/Views/PlateView.swift:338 and ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:259 fix the review's required-image loading finding while preserving pixels, semantic keys and rendering modifiers.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#pullrequestreview-5117675730 -> 9702f5eab9f2aaed8287bffcb66f90229b0cc772

Disposition: FIXED
Commit: 05252469ec2257bcf88f18bfca8b98e8a5c41c3a
Evidence: ios/PulsePlate/Views/Home/HomeExperience.swift:371 and :562 share one presentation size selector across both arrangements; ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:12 tests compact/regular by normal/Accessibility cases. Full 287 XCTest plus 13 Swift tests pass and the normal compact native frame shows the portrait hero.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#pullrequestreview-5117921760 -> 05252469ec2257bcf88f18bfca8b98e8a5c41c3a

Disposition: FIXED
Commit: 2e213a6d32d0629ec0e2e048a726b51b5f3d8773
Evidence: ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift:261 positively requires the admitted initializer at each known owner; :283 covers decorative, bundle-argument, UIImage and multiline bypass spellings; :782 normalizes formatting for that bounded call shape. Full 288 XCTest plus 13 Swift Testing tests and all-files pre-commit pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#pullrequestreview-5117941085 -> 2e213a6d32d0629ec0e2e048a726b51b5f3d8773

Disposition: NOT-A-BUG
Evidence: AGENTS.md:120 classifies external status checks as advisory; .coderabbit.yaml:15 defines path-specific instructions without a Swift docstring-percentage contract; docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md:61 and IOSREL2V5AssetParityTests.swift:154 document and execute the actual asset contract.
Reason: The reported docstring percentage is not disputed. It is a provider-specific style metric over internal presentation builders and self-describing test methods, not a missing public API or behavior contract. The canonical taxonomy/provenance and executable tests document the admitted behavior; no undocumented external contract or correctness defect is identified. No repo check or threshold is disabled.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#issuecomment-5544747062

Disposition: NOT-A-BUG
Evidence: AGENTS.md:120 keeps non-required external status advisory; all actual Sourcery findings are fixed in 698a2b90922bbfa64443e812274a5fca9da78e82 and separately mapped. Current-head required CI and exact-material self-review remain mandatory.
Reason: This notice withdraws a stale approval because the automatic review limit is exhausted; it identifies no new code defect. No current Sourcery approval is claimed. Do not request another exhausted-provider review; retain the notice and prove the actual findings and repository gates independently.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380#issuecomment-5546669149

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:5e947b2929874ba80b6c8ba6dfa145eab06fb5f81b2caa4a6be8c5762eb4fb9c","material_head_sha":"2e213a6d32d0629ec0e2e048a726b51b5f3d8773","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"863d16ea2328dd32fa6fec6cef4d8f117b6edf85","blocking":false,"head_revision":"2e213a6d32d0629ec0e2e048a726b51b5f3d8773","material_digest":"sha256:5e947b2929874ba80b6c8ba6dfa145eab06fb5f81b2caa4a6be8c5762eb4fb9c","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"863d16ea2328dd32fa6fec6cef4d8f117b6edf85","digest":"sha256:5e947b2929874ba80b6c8ba6dfa145eab06fb5f81b2caa4a6be8c5762eb4fb9c","material_head_sha":"2e213a6d32d0629ec0e2e048a726b51b5f3d8773","merge_base_sha":"863d16ea2328dd32fa6fec6cef4d8f117b6edf85","policy_version":"pulseplate.material-classification/v1"},"pr_number":2380,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:5e947b2929874ba80b6c8ba6dfa145eab06fb5f81b2caa4a6be8c5762eb4fb9c","material_head_sha":"2e213a6d32d0629ec0e2e048a726b51b5f3d8773","report_payload":{"actionable_findings_count":0,"base_ref_oid":"863d16ea2328dd32fa6fec6cef4d8f117b6edf85","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/a79f914c550e.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"a79f914c550e"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 2094 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make validate-changed"],"generated_at_utc":"2026-09-04T23:00:08Z","material_digest":"sha256:5e947b2929874ba80b6c8ba6dfa145eab06fb5f81b2caa4a6be8c5762eb4fb9c","material_head_sha":"2e213a6d32d0629ec0e2e048a726b51b5f3d8773","merge_base_sha":"863d16ea2328dd32fa6fec6cef4d8f117b6edf85","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"863d16ea2328dd32fa6fec6cef4d8f117b6edf85..2e213a6d32d0629ec0e2e048a726b51b5f3d8773","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2380_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":["docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md","docs/design/FITCHEF_MASCOT_ASSET_CANON.md","docs/roadmap/BACKLOG_LEDGER.md","ios/PulsePlate/Assets.xcassets/FitChefActionNutritionPlate.imageset/Contents.json","ios/PulsePlate/Assets.xcassets/FitChefActionNutritionPlate.imageset/FitChefActionNutritionPlate@1x.png","ios/PulsePlate/Assets.xcassets/FitChefActionNutritionPlate.imageset/FitChefActionNutritionPlate@2x.png","ios/PulsePlate/Assets.xcassets/FitChefActionNutritionPlate.imageset/FitChefActionNutritionPlate@3x.png","ios/PulsePlate/Assets.xcassets/FitChefActionProgressTracking.imageset/Contents.json","ios/PulsePlate/Assets.xcassets/FitChefActionProgressTracking.imageset/FitChefActionProgressTracking@1x.png","ios/PulsePlate/Assets.xcassets/FitChefActionProgressTracking.imageset/FitChefActionProgressTracking@2x.png","ios/PulsePlate/Assets.xcassets/FitChefActionProgressTracking.imageset/FitChefActionProgressTracking@3x.png","ios/PulsePlate/Assets.xcassets/FitChefOnboardingProfileSetup.imageset/Contents.json","ios/PulsePlate/Assets.xcassets/FitChefOnboardingProfileSetup.imageset/FitChefOnboardingProfileSetup@1x.png","ios/PulsePlate/Assets.xcassets/FitChefOnboardingProfileSetup.imageset/FitChefOnboardingProfileSetup@2x.png","ios/PulsePlate/Assets.xcassets/FitChefOnboardingProfileSetup.imageset/FitChefOnboardingProfileSetup@3x.png","ios/PulsePlate/Assets.xcassets/FitChefOnboardingWelcome.imageset/fitchef-onboarding-welcome@1x.png","ios/PulsePlate/Assets.xcassets/FitChefOnboardingWelcome.imageset/fitchef-onboarding-welcome@2x.png","ios/PulsePlate/Assets.xcassets/FitChefOnboardingWelcome.imageset/fitchef-onboarding-welcome@3x.png","ios/PulsePlate/Assets.xcassets/FitChefPortraitEncouraging.imageset/Contents.json","ios/PulsePlate/Assets.xcassets/FitChefPortraitEncouraging.imageset/FitChefPortraitEncouraging@1x.png","ios/PulsePlate/Assets.xcassets/FitChefPortraitEncouraging.imageset/FitChefPortraitEncouraging@2x.png","ios/PulsePlate/Assets.xcassets/FitChefPortraitEncouraging.imageset/FitChefPortraitEncouraging@3x.png","ios/PulsePlate/Assets.xcassets/FitChefPortraitHappy.imageset/Contents.json","ios/PulsePlate/Assets.xcassets/FitChefPortraitHappy.imageset/FitChefPortraitHappy@1x.png","ios/PulsePlate/Assets.xcassets/FitChefPortraitHappy.imageset/FitChefPortraitHappy@2x.png","ios/PulsePlate/Assets.xcassets/FitChefPortraitHappy.imageset/FitChefPortraitHappy@3x.png","ios/PulsePlate/Assets.xcassets/FitChefThinking.imageset/fitchef-thinking@1x.png","ios/PulsePlate/Assets.xcassets/FitChefThinking.imageset/fitchef-thinking@2x.png","ios/PulsePlate/Assets.xcassets/FitChefThinking.imageset/fitchef-thinking@3x.png","ios/PulsePlate/Resources/Images/photo-activity-endurance-v1.jpg","ios/PulsePlate/Resources/Images/photo-activity-movement-everyday-fitness-v1.jpg","ios/PulsePlate/Resources/Images/photo-daily-plate-salmon-v1.jpg","ios/PulsePlate/Screens/BMICalculatorScreen.swift","ios/PulsePlate/Views/Home/HomeExperience.swift","ios/PulsePlate/Views/PlateView.swift","ios/PulsePlate/Views/ProfileView.swift","ios/PulsePlate/Views/ProgressView.swift","ios/PulsePlate/en.lproj/Localizable.strings","ios/PulsePlate/es.lproj/Localizable.strings","ios/PulsePlate/ru.lproj/Localizable.strings","ios/PulsePlateTests/AIInsightViewModelTests.swift","ios/PulsePlateTests/IOSREL2V5AssetParityTests.swift"],"diff_summary":{"additions":1990,"changed_lines":2094,"deletions":104,"files":42},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","ios/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:121f7aa8ea6a2cf8672a5ffd97d15cb8c3f568a50b87ce1c832a4dedb25f73f5","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
