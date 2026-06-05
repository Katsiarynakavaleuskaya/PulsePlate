# PR #1890 Fixed In Commit Mapping

PR: `docs(release): promote FitChef App Store rendered review and TestFlight readiness wave`
Branch: `codex/fitchef-appstore-rendered-review-testflight-readiness`
Base after refresh: `origin/main` at `854562d20`
Implementation commit: `506d82322fa1cee017dd574deebbca0bcd397cf9`

## Scope

This PR moves the FitChef EN/RU/ES App Store packs from contract/localization QA into an `INTERNAL_REVIEW_ONLY` rendered-review and TestFlight readiness lane. It adds a repo-local release-readiness bundle, links seven App Store shots to iOS screenshot scenarios, strengthens `ios-appstore-verify`, and extends deterministic tests for locale/scenario parity and protected-boundary enforcement.

## Out Of Scope

Protected `ios/fastlane/metadata` mutation, screenshot/video binaries, Fastlane upload automation, App Store Connect mutation, frontend/iOS runtime changes, backend/OpenAPI changes, telemetry, billing, semantic cache, GraphRAG, Slack changes, and public submission readiness claims.

## Lane Start Provenance

- Starter: `scripts/orchestration/start_pr_lane.sh`
- Packet: `artifacts/orchestration/task_packets/c22f1f222682.json`
- Branch/worktree: `codex/fitchef-appstore-rendered-review-testflight-readiness` / `worktrees/fitchef-appstore-rendered-review-testflight-readiness`
- Operator override: pending post-merge `main` workflows were not treated as a PR-open blocker. This is not merge-readiness evidence.

## Role Agent Evidence

Pre-open bootstrap role order executed:

1. `agent-coordinator` - PASS after scope lock and product-designer disposition.
2. `architecture-specialist` - PASS.
3. `app-store-release-agent` - PASS after release-readiness wording and validator-linkage fixes.
4. `wellness-analyst-agent` - PASS after stale "improve health" wording was removed.
5. `cursor-specialist-agent` - PASS.
6. `security-auditor` - PASS after protected-action, secret/local-path, JSON-key, and media false-negative guards were added.
7. `qa-engineer-agent` - PASS after duplicate locale row false-green coverage was added.
8. `bug-hunter` - PASS after time-range drift, exact schema, and scenario-id type guards were fixed.

Coordinator disposition: requested `product-designer` was not in the executable dispatch and was recorded as rejected/unknown by the coordinator; no assigned executable role was skipped.

Post-open required order before readiness: `qa-engineer-agent -> bug-hunter -> security-auditor -> Codex Security diff scan / finding discovery -> pulseplate-pr-review`.

## Premortem Finding Closure

Skill: `pulseplate-premortem-risk-review`
Mode: `pr-premortem`
Local artifact: `artifacts/orchestration/premortem/fitchef-rendered-review-testflight-readiness-premortem.md`

| Finding | Disposition | Evidence |
| --- | --- | --- |
| Release-readiness wording could overclaim App Store submission readiness. | FIXED | `Makefile` now says repo-local release gates; `appstore/fitchef/release_readiness/shot_scenario_matrix.json` uses `classification: INTERNAL_REVIEW_ONLY` and `public_submission_allowed: false`; `scripts/release/check_ios_appstore_verify.py` rejects protected-action completion claims. |
| Locale/scenario drift could pass if the matrix was shape-only. | FIXED | `scripts/release/check_ios_appstore_verify.py` validates exact scenario ids, exact 21 locale rows, locale/shot uniqueness, manifest/storyboard path existence, filename linkage, and storyboard `time_range` parity; tests cover missing matrix, duplicates, time drift, manifest mismatch, and reviewer-matrix drift. |
| Wellness or pricing copy could leak into release prep. | FIXED | EN screenshot copy now says "support habits"; cross-locale prep mirrors bounded wording; validator/tests reject stale health-outcome wording and pricing/trial claims. |
| Internal artifact could accidentally carry secrets, local paths, or media binaries. | FIXED | Validator scans JSON keys and values for local path fragments, credential-looking key/value pairs, protected upload claims, and media suffixes; tests cover local paths, token-key labels, credential-assignment placeholders, protected JSON keys, and media files. |

Decision: proceed with changes.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-ae77c61bb5d4.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-ae77c61bb5d4.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Source diff applied: true
- Shared tree untouched: true
- Source diff paths: 11
- Oracle commands: `python scripts/release/check_ios_appstore_verify.py` and `python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py`, both return code 0.
- Contribution: Experiment Runner shaped the commit decision and fixed-mapping evidence; implementation commit `506d82322fa1cee017dd574deebbca0bcd397cf9` includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Tests And Gates

- `python3 scripts/orchestration/check_preflight.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/orchestration/check_preflight.py --path docs/roadmap/BACKLOG_LEDGER.md` - PASS.
- `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` - PASS.
- `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` - PASS, 11 passed / 0 failed.
- `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` - PASS.
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS after commit `2621360a8` review hardening.
- Direct localized wellness probes after commit `8ed1ecac5` - PASS: ES/RU boundary disclaimers are allowed, repeated localized claims and actual ES/RU medical claims are rejected.
- `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` - PASS after commit `8ed1ecac5`.
- `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` - PASS after commit `8ed1ecac5`, 11 passed / 0 failed.
- `make validate-changed` - PASS after commit `8ed1ecac5`.
- `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` - PASS after commit `8ed1ecac5`.
- `pre-commit run --all-files` - PASS after commit `8ed1ecac5`.
- Direct release-scan probes after commit `1d59f4af9` - PASS: localized treatment/professional-role claims, localized upload readiness claims, scalar JSON pricing/trial values, raw credential-token shapes, ruble price formats, protected-action JSON keys, symlinks, and guaranteed/clinical outcome claims are all blocked while localized boundary-disclaimer fixtures remain allowed.
- `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` - PASS after commit `1d59f4af9`.
- `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` - PASS after commit `1d59f4af9`, 11 passed / 0 failed.
- `make validate-changed` - PASS after commit `1d59f4af9`.
- `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` - PASS after commit `1d59f4af9`.
- `pre-commit run --all-files` - PASS before commit `1d59f4af9`.
- Direct validator/fixture checks after commit `ddd42468e` - PASS: schema version drift, all protected-action completion variants, and forbidden FitChef pack path segments are blocked.
- `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` - PASS after commit `ddd42468e`.
- `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` - PASS after commit `ddd42468e`, 11 passed / 0 failed.
- `make validate-changed` - PASS after commit `ddd42468e`.
- `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` - PASS after commit `ddd42468e`.
- `pre-commit run --all-files` - PASS before commit `ddd42468e`.
- Push pre-push hooks - PASS through commit `024729aaf` after mypy return-type/value narrowing fix in `scripts/release/check_ios_appstore_verify.py`, including changed-file mypy, pip-audit, backend tests, full-repo Bandit, and docker build test. Final push evidence must be refreshed after the mapping update.

Full local `make verify` was not run by default for this docs/release-validator PR under the operator-approved changed-scope gate policy. Merge readiness is not claimed without current-head CI, post-open role passes, Codex Security scan, `pulseplate-pr-review`, unresolved-thread checks, PR body/mapping parity, strict wrapper evidence, and wait-window.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No GitHub review threads existed when this artifact was created. Any post-open human, bot, role-agent, Codex Security, or PulsePlate PR review finding must be added below with `FIXED`, `NOT-A-BUG`, or `DEFERRED` disposition before resolution or readiness claims.

## Post-Open Review Evidence

- `qa-engineer-agent`: PASS. Evidence: post-open pass at head `acca8fc14df4df301d6e4fb4cb10d2b6475055e7` found no QA blockers, verified Phase2 mirror, focused validator/tests, `make validate-changed`, `make ios-appstore-verify`, and clean worktree; merge readiness was not claimed because CI/post-open gates remained pending.
- `bug-hunter`: PASS on head `8a5d032f9` after fixes. Evidence: `f57b215e8` fixed the original whole-pack scan, source path, blocked action, TestFlight status, Makefile coverage, governed path, and iOS source-linkage false-greens; `854ee4c2f` fixed the first negation-plus-overclaim bypass; `8a2c136a2` fixed the remaining comma-clause bypass and added validator/pack guard regressions; rerun agent `019e9946-d0e9-7571-b8f1-3739faa60b7a` returned PASS with no findings and no file changes. Later bot review hardening in `2621360a8` expands the protected text scan to the whole FitChef pack, redacts credential diagnostics, binds Swift screenshot expectations per case, validates wellness status/text evidence, removes forbidden dynamic test loading, and closes punctuation-only negation gaps.
- `security-auditor`: PASS on current head `8a5d032f9`. Evidence: agent `019e994b-6730-7890-a6b8-62bd3b75315f` found no protected release-surface drift, no screenshot/video binaries, no `ios/fastlane/metadata` mutation, no upload automation or App Store Connect mutation, no secret/local-path leakage, no unsafe pricing/trial/medical overclaim, and no validator fail-open/path-boundary regression.
- Codex Security diff scan / finding discovery: PASS / no findings. Evidence: scan id `8a5d032f9de3_20260605224323`; merge-base-corrected deep review closed 3/3 generated rows (`appstore/fitchef/en-US/iphone-6.9/screenshots/shot_manifest.json`, `appstore/fitchef/release_readiness/shot_scenario_matrix.json`, `scripts/release/check_ios_appstore_verify.py`); `report.md` format validation passed and `report.html` rendered in the gitignored scan workspace.
- `pulseplate-pr-review`: NOTE dispositioned as NOT-A-BUG. Evidence: dry-run report produced one advisory large-diff planning note only; the operator explicitly requested a broader MVP release-readiness slice, scope remained release-validator/App Store metadata only, no protected runtime/upload surfaces entered the PR, and `make validate-changed`, focused validator/tests, full pre-commit, current-head CI, post-open QA, bug-hunter, security-auditor, and Codex Security scan all passed. `.venv` calibration command `../../.venv/bin/python -m pytest tests/test_pr_review_report.py -q` passed; the earlier system `python3` attempt failed with missing local dependency `fastapi` and was not used as gate evidence.
- Late bot review hardening: FIXED in `0f9094f85`. Evidence: source PR provenance is now exact and fail-closed against PR #1886 / `26b7cf4f`; focused tests, direct validator, `make validate-changed`, and `pre-commit run --all-files` passed locally.
- Post-open `qa-engineer-agent` rerun on head `396909ff7`: FAIL with localized release-gate false-greens. Disposition: FIXED in `dd8803779`. Evidence: validator now blocks localized wellness/pricing/trial claims, Windows local temp paths, and missing/wrong XCTest capture methods; focused tests, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.
- Post-open `qa-engineer-agent` rerun on head `aca73dc8b`: FAIL with disposition-governance gap for already-resolved threads `discussion_r3364079340`, `discussion_r3364127016`, and `discussion_r3364127022`. Disposition: FIXED in `48e9ba365` plus this mapping update. Evidence: validator now evaluates every medical-term match per line and rejects repeated same-term overclaims after a boundary mention; mapping below lists the resolved thread URLs with commit evidence.
- Late bot review `discussion_r3365261866`: FIXED in `8ed1ecac5`. Evidence: localized wellness fragment scan now uses line-level `finditer` plus localized boundary-negation logic for ES/RU safe disclaimers while still rejecting repeated localized claims and actual localized medical/wellness overclaims.
- Late bot review batch after head `20f3c33a8`: FIXED in `1d59f4af9`. Evidence: release scan now blocks localized treatment/professional-role claims, localized upload readiness claims, scalar JSON pricing/trial values, raw credential-token shapes, ruble price formats, protected-action JSON keys, symlinks, and guaranteed/clinical outcome claims. Focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.
- Post-open `qa-engineer-agent` rerun on head `20f3c33a8`: FAIL with this artifact quoting raw localized probe text. Disposition: FIXED. Evidence: raw localized probe text was rewritten into neutral evidence wording in this artifact.
- Post-open `qa-engineer-agent` rerun on head `20f3c33a8`: live GitHub review threads remained unresolved. Disposition: DEFERRED. Evidence: unresolved review threads are mapped below and must be resolved only after the mapped fixes are pushed and reviewed.
- Late bot review batch after head `b9a8707d7`: FIXED in `ddd42468e`. Evidence: scenario matrix schema version is now value-checked, protected-action completion claims are synchronized with the blocked release action list, and forbidden local-artifact path segments under the governed FitChef pack are rejected before file-content scanning. Focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950396 -> f57b215e8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950401 -> f57b215e8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950404 -> f57b215e8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950408 -> f57b215e8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950409 -> f57b215e8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950415 -> f57b215e8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363978756 -> f57b215e8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363978760 -> f57b215e8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363978762 -> f57b215e8
Disposition: FIXED
Commit: f57b215e8
Evidence: `scripts/release/check_ios_appstore_verify.py` now scans the whole FitChef App Store pack for media/text boundaries, validates `source_paths` values and iOS source files, enforces `blocked_release_actions`, scans every release-readiness JSON/Markdown file for protected claims/secrets/pricing/wellness overclaims, requires `testflight_smoke_status: not_started`, and constrains locale rows to governed FitChef manifest/storyboard paths; `Makefile` adds `tests/test_fitchef_app_store_pack.py` to `ios-appstore-verify`; `tests/ios/test_ios_appstore_verify.py` adds regression tests for all nine review false-greens; focused pytest, validator, `make ios-appstore-verify`, changed-scope validation, and mypy passed locally.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364054086 -> 8a2c136a2
Disposition: FIXED
Commit: 8a2c136a2
Evidence: `scripts/release/check_ios_appstore_verify.py` replaced broad same-line negation with bounded forbidden-boundary context logic; `tests/ios/test_ios_appstore_verify.py` and `tests/test_fitchef_app_store_pack.py` reject negation-plus-overclaim separators including comma while preserving safe boundary-list language.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364054091 -> 2621360a8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364079331 -> 2621360a8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364134870 -> 2621360a8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364134876 -> 2621360a8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364134880 -> 2621360a8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364134882 -> 2621360a8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364218433 -> 2621360a8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364241495 -> 2621360a8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364241498 -> 2621360a8
Disposition: FIXED
Commit: 2621360a8
Evidence: `scripts/release/check_ios_appstore_verify.py` now scans all JSON/Markdown text under `appstore/fitchef`, redacts credential-like values in release-gate diagnostics, validates per-case Swift `screenshotName` and `accessibilityIdentifier` returns, enforces non-empty scenario/reviewer text and allowed `wellness_claim_status` values, allows natural wellness boundary disclaimers, and rejects punctuation-only negation gaps. `tests/ios/test_ios_appstore_verify.py` removes dynamic `importlib.util` loading and adds regressions for locale-pack protected claims/secrets, redaction, Swift case swaps, blank wellness notes, unsafe wellness statuses, natural disclaimers, and punctuation-only negation bypasses. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `make validate-changed` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365020667 -> 0f9094f85
Disposition: FIXED
Commit: 0f9094f85
Evidence: `scripts/release/check_ios_appstore_verify.py` now validates `source_pr` exactly against the landed multilingual localization QA provenance (`number: 1886`, `merge_commit: 26b7cf4f`), and `tests/ios/test_ios_appstore_verify.py` rejects `source_pr: {"number": 0, "merge_commit": ""}`. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365125647 -> dd8803779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365125654 -> dd8803779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365125659 -> dd8803779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365125664 -> dd8803779
Disposition: FIXED
Commit: dd8803779
Evidence: `scripts/release/check_ios_appstore_verify.py` now normalizes release-pack text with accent folding, blocks localized ES/RU medical/wellness fragments, blocks localized trial/pricing fragments and euro price forms, rejects Windows local temp paths with redacted diagnostics, and verifies every FitChef screenshot scenario has a matching XCTest capture method that calls `captureScreenshot(for: .<scenario>)`. `tests/ios/test_ios_appstore_verify.py` adds regressions for Spanish/Russian localized medical claims, Spanish/Russian pricing/trial claims, Windows temp paths, missing XCTest methods, and wrong XCTest capture calls. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; isolated QA probes return blocking errors for localized claims/pricing/path cases; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364079340 -> 48e9ba365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364127016 -> 48e9ba365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364127022 -> 48e9ba365
Disposition: FIXED
Commit: 48e9ba365
Evidence: `scripts/release/check_ios_appstore_verify.py` now uses `finditer` to evaluate every medical/wellness term occurrence on each line and refuses boundary negation when the same matched term already appears between the marker and current occurrence. `tests/ios/test_ios_appstore_verify.py` adds regressions for `No diagnosis and diagnosis patients.` and `No diagnosis, diagnosis patients.` while existing safe boundary-list and natural disclaimer tests continue to pass. Local evidence after the fix: direct probes reject repeated same-term overclaims and allow natural disclaimers; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365261866 -> 8ed1ecac5
Disposition: FIXED
Commit: 8ed1ecac5
Evidence: `scripts/release/check_ios_appstore_verify.py` now scans localized wellness fragments per line with `finditer` and applies localized ES/RU boundary-negation context instead of treating every boundary disclaimer as an overclaim. `tests/ios/test_ios_appstore_verify.py` adds ES/RU safe-disclaimer regressions plus repeated localized-claim regressions. Local evidence after the fix: direct probes allow localized no-medical-boundary disclaimer fixtures while rejecting repeated localized claims and actual localized medical claims; focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` all passed locally.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365279308 -> 1d59f4af9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365279316 -> 1d59f4af9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365279320 -> 1d59f4af9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365279327 -> 1d59f4af9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365279335 -> 1d59f4af9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365376634 -> 1d59f4af9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365376637 -> 1d59f4af9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365376640 -> 1d59f4af9
Disposition: FIXED
Commit: 1d59f4af9
Evidence: `scripts/release/check_ios_appstore_verify.py` now normalizes JSON keys/values for release scanning, rejects symlinks under the governed FitChef pack, blocks raw credential-token shapes with redacted diagnostics, blocks localized upload-readiness claims, blocks ruble price formats and scalar JSON pricing/trial values, expands localized wellness blockers for Spanish treatment/professional-role wording, and rejects guaranteed/clinical outcome claims with boundary-aware logic. `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for each blocked false-green class while preserving safe localized boundary-disclaimer coverage. Local evidence after the fix: direct probes for the eight bot-reported classes return blocking errors; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365432376 -> ddd42468e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365432378 -> ddd42468e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365432383 -> ddd42468e
Disposition: FIXED
Commit: ddd42468e
Evidence: `scripts/release/check_ios_appstore_verify.py` now requires the exact FitChef release-readiness schema version, blocks protected-action completion claims for all blocked release-action categories, and rejects forbidden local-artifact path segments anywhere under the governed FitChef App Store pack before content scanning. `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for schema-version drift, protected-action completion variants, and forbidden path segments. Local evidence after the fix: focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` all passed locally.

## Post-Open Role-Agent Finding Closure

Finding: post-open `bug-hunter` agent `019e98b2-aa05-7c81-b31a-e3ea0daba98c` reported a comma-clause wellness overclaim bypass.
Disposition: FIXED
Commit: 8a2c136a2
Evidence: `scripts/release/check_ios_appstore_verify.py` now limits boundary-negation to explicit forbidden-claim context words instead of broad same-line negation; `tests/ios/test_ios_appstore_verify.py` and `tests/test_fitchef_app_store_pack.py` cover `:`, `.`, `;`, `!`, `?`, and `,` separators plus safe boundary-list language. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `../../.venv/bin/python -m mypy scripts/release/check_ios_appstore_verify.py` PASS; `../../.venv/bin/python -m flake8 scripts/release/check_ios_appstore_verify.py tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS.

Finding: `pulseplate-pr-review` dry-run report flagged an advisory large-diff planning note for human review.
Disposition: NOT-A-BUG
Evidence: Operator scope intentionally broadened this release-readiness PR beyond a microscopic docs lane while keeping it bounded to repo-local App Store release-readiness metadata, validators, and tests. The PR does not touch protected upload/runtime surfaces, and the targeted gates plus current-head CI and role reviews cover the expanded scope. No code, security, wellness, or release-boundary defect was reported by the PR review.


## Merge Readiness

Not claimed. Required before merge: current-head CI, no unresolved review threads, no actionable bot comments, post-open role passes, Codex Security diff scan / finding discovery, `pulseplate-pr-review`, this mapping updated with every disposition, PR body mirror updated, strict merge-readiness wrapper evidence, and mandatory wait-window.
