# PR #1890 Fixed In Commit Mapping

PR: `docs(release): promote FitChef App Store rendered review and TestFlight readiness wave`
Branch: `codex/fitchef-appstore-rendered-review-testflight-readiness`
Base after refresh: `origin/main` at `ec44f6e57`; merged into this branch by `34cef2921`
Implementation commit: `8e3900c7b996e2f2e8794b960378aa99aa7cd473`

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
- Contribution: Experiment Runner shaped the commit decision and fixed-mapping evidence; implementation commit `8e3900c7b996e2f2e8794b960378aa99aa7cd473` includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Tests And Gates

- `python3 scripts/orchestration/check_preflight.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/orchestration/check_preflight.py --path docs/roadmap/BACKLOG_LEDGER.md` - PASS.
- `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` - PASS.
- `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` - PASS, 11 passed / 0 failed.
- `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` - PASS.
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS after commit `aa49d1492` review hardening.
- Direct localized wellness probes after commit `c227b9a93` - PASS: ES/RU boundary disclaimers are allowed, repeated localized claims and actual ES/RU medical claims are rejected.
- `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` - PASS after commit `c227b9a93`.
- `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` - PASS after commit `c227b9a93`, 11 passed / 0 failed.
- `make validate-changed` - PASS after commit `c227b9a93`.
- `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` - PASS after commit `c227b9a93`.
- `pre-commit run --all-files` - PASS after commit `c227b9a93`.
- Direct release-scan probes after commit `4b1c1c089` - PASS: localized treatment/professional-role claims, localized upload readiness claims, scalar JSON pricing/trial values, raw credential-token shapes, ruble price formats, protected-action JSON keys, symlinks, and guaranteed/clinical outcome claims are all blocked while localized boundary-disclaimer fixtures remain allowed.
- `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` - PASS after commit `4b1c1c089`.
- `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` - PASS after commit `4b1c1c089`, 11 passed / 0 failed.
- `make validate-changed` - PASS after commit `4b1c1c089`.
- `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` - PASS after commit `4b1c1c089`.
- `pre-commit run --all-files` - PASS before commit `4b1c1c089`.
- Direct validator/fixture checks after commit `4c8d71688` - PASS: schema version drift, all protected-action completion variants, and forbidden FitChef pack path segments are blocked.
- `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` - PASS after commit `4c8d71688`.
- `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` - PASS after commit `4c8d71688`, 11 passed / 0 failed.
- `make validate-changed` - PASS after commit `4c8d71688`.
- `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` - PASS after commit `4c8d71688`.
- `pre-commit run --all-files` - PASS before commit `4c8d71688`.
- Push pre-push hooks - PASS through commit `cb0fd0f26` after mypy return-type/value narrowing fix in `scripts/release/check_ios_appstore_verify.py`, including changed-file mypy, pip-audit, backend tests, full-repo Bandit, and docker build test. Final push evidence must be refreshed after the mapping update.
- Post-rebase validation on `origin/main` at `889e9a0ad`: `python3 scripts/orchestration/check_preflight.py` PASS; `python3 scripts/orchestration/check_agent_consistency.py` PASS; `python3 scripts/orchestration/check_preflight.py --path docs/roadmap/BACKLOG_LEDGER.md` PASS; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS; `python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1890` PASS for 10 resolved review threads.
- Main coverage carryover validation after commit `c98d318c4`: `../../.venv/bin/python -m pytest -q tests/test_user_coaching_state.py` PASS; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.
- Late CodeRabbit release-validator hardening validation after commit `0c414621f`: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.
- Late CodeRabbit pricing/export false-green validation after commit `cef1c738e`: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.
- Compact ISO-prefix pricing validation after commit `941042ad3`: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.
- Late validator false-green validation after commit `8160d9779`: direct probes reject `No diagnosis and treat patients.`, `Resultados rapidos para tu cuerpo.`, `Guaranteed adherence with meal plan.`, and `api key: [dummy value]`; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.
- App Store contract gap validation after commit `47e7dec8d`: direct probes reject `Most accurate nutrition app.`, `Available on Google Play too.`, and `Android companion app support.`; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.
- Authority-overclaim validation after commit `54539875d`: direct probes reject localized nutrition-professional claims, therapeutic variants, medical-grade copy, and medical-monitoring copy; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.
- Release-evidence guard validation after commit `7359f75ca`: direct probes reject `submit_ready: true`, `ready_for_upload`, `fastlane_upload_completed`, `price 9.99`, and `trial 14`; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.
- JSON submission-status validation after commit `d54a118dc`: direct probes show flattened JSON `submit_ready` and `public_submission_allowed` boolean claims are rejected as protected release action claims; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.
- Post-merge validation after commit `34cef2921`: `python3 scripts/orchestration/check_preflight.py` PASS; `python3 scripts/orchestration/check_agent_consistency.py` PASS; `python3 scripts/orchestration/check_preflight.py --path docs/roadmap/BACKLOG_LEDGER.md` PASS; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS. Branch head is no longer behind `origin/main`, and the direct Python subprocess governance policy is present in `AGENTS.md` and `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`.

Full local `make verify` was not run by default for this docs/release-validator PR under the operator-approved changed-scope gate policy. Merge readiness is not claimed without current-head CI, post-open role passes, Codex Security scan, `pulseplate-pr-review`, unresolved-thread checks, PR body/mapping parity, strict wrapper evidence, and wait-window.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No GitHub review threads existed when this artifact was created. Any post-open human, bot, role-agent, Codex Security, or PulsePlate PR review finding must be added below with `FIXED`, `NOT-A-BUG`, or `DEFERRED` disposition before resolution or readiness claims.

## Post-Open Review Evidence

- `qa-engineer-agent`: PASS. Evidence: post-open pass at post-rebase equivalent head `91b44a22bf7a3c15a755c9016ed1c5118f61e2be` found no QA blockers, verified Phase2 mirror, focused validator/tests, `make validate-changed`, `make ios-appstore-verify`, and clean worktree; merge readiness was not claimed because CI/post-open gates remained pending.
- `bug-hunter`: PASS on head `283cfa00b` after fixes. Evidence: `9840d503d` fixed the original whole-pack scan, source path, blocked action, TestFlight status, Makefile coverage, governed path, and iOS source-linkage false-greens; `ddeb83f95` fixed the first negation-plus-overclaim bypass; `1a588778f` fixed the remaining comma-clause bypass and added validator/pack guard regressions; rerun agent `019e9946-d0e9-7571-b8f1-3739faa60b7a` returned PASS with no findings and no file changes. Later bot review hardening in `aa49d1492` expands the protected text scan to the whole FitChef pack, redacts credential diagnostics, binds Swift screenshot expectations per case, validates wellness status/text evidence, removes forbidden dynamic test loading, and closes punctuation-only negation gaps.
- `security-auditor`: PASS on current head `283cfa00b`. Evidence: agent `019e994b-6730-7890-a6b8-62bd3b75315f` found no protected release-surface drift, no screenshot/video binaries, no `ios/fastlane/metadata` mutation, no upload automation or App Store Connect mutation, no secret/local-path leakage, no unsafe pricing/trial/medical overclaim, and no validator fail-open/path-boundary regression.
- Codex Security diff scan / finding discovery: PASS / no findings. Evidence: pre-rebase scan id `8a5d032f9de3_20260605224323`; merge-base-corrected deep review closed 3/3 generated rows (`appstore/fitchef/en-US/iphone-6.9/screenshots/shot_manifest.json`, `appstore/fitchef/release_readiness/shot_scenario_matrix.json`, `scripts/release/check_ios_appstore_verify.py`); `report.md` format validation passed and `report.html` rendered in the gitignored scan workspace.
- `pulseplate-pr-review`: NOTE dispositioned as NOT-A-BUG. Evidence: dry-run report produced one advisory large-diff planning note only; the operator explicitly requested a broader MVP release-readiness slice, scope remained release-validator/App Store metadata only, no protected runtime/upload surfaces entered the PR, and `make validate-changed`, focused validator/tests, full pre-commit, current-head CI, post-open QA, bug-hunter, security-auditor, and Codex Security scan all passed. `.venv` calibration command `../../.venv/bin/python -m pytest tests/test_pr_review_report.py -q` passed; the earlier system `python3` attempt failed with missing local dependency `fastapi` and was not used as gate evidence.
- Late bot review hardening: FIXED in `ee9407828`. Evidence: source PR provenance is now exact and fail-closed against PR #1886 / `26b7cf4f`; focused tests, direct validator, `make validate-changed`, and `pre-commit run --all-files` passed locally.
- Post-open `qa-engineer-agent` rerun on head `0594295f3`: FAIL with localized release-gate false-greens. Disposition: FIXED in `396afada8`. Evidence: validator now blocks localized wellness/pricing/trial claims, Windows local temp paths, and missing/wrong XCTest capture methods; focused tests, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.
- Post-open `qa-engineer-agent` rerun on head `08e13f25e`: FAIL with disposition-governance gap for already-resolved threads `discussion_r3364079340`, `discussion_r3364127016`, and `discussion_r3364127022`. Disposition: FIXED in `c613cc153` plus this mapping update. Evidence: validator now evaluates every medical-term match per line and rejects repeated same-term overclaims after a boundary mention; mapping below lists the resolved thread URLs with commit evidence.
- Late bot review `discussion_r3365261866`: FIXED in `c227b9a93`. Evidence: localized wellness fragment scan now uses line-level `finditer` plus localized boundary-negation logic for ES/RU safe disclaimers while still rejecting repeated localized claims and actual localized medical/wellness overclaims.
- Late bot review batch after head `7d1b47bab`: FIXED in `4b1c1c089`. Evidence: release scan now blocks localized treatment/professional-role claims, localized upload readiness claims, scalar JSON pricing/trial values, raw credential-token shapes, ruble price formats, protected-action JSON keys, symlinks, and guaranteed/clinical outcome claims. Focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.
- Post-open `qa-engineer-agent` rerun on head `7d1b47bab`: FAIL with this artifact quoting raw localized probe text. Disposition: FIXED. Evidence: raw localized probe text was rewritten into neutral evidence wording in this artifact.
- Post-open `qa-engineer-agent` rerun on head `7d1b47bab`: live GitHub review threads remained unresolved. Disposition: DEFERRED. Evidence: unresolved review threads are mapped below and must be resolved only after the mapped fixes are pushed and reviewed.
- Late bot review batch after head `831007886`: FIXED in `4c8d71688`. Evidence: scenario matrix schema version is now value-checked, protected-action completion claims are synchronized with the blocked release action list, and forbidden local-artifact path segments under the governed FitChef pack are rejected before file-content scanning. Focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.
- CodeRabbit review after head `e31c1b616`: FIXED in `ebf9eeafc` and `09ee45c21`. Evidence: committed test fixtures no longer contain complete credential-like values as source literals, and this artifact now uses canonical single dispositions instead of combined disposition wording.
- Late CodeRabbit release-validator hardening batch after head `eac8e00f1`: FIXED in `0c414621f` for medical-professional, cure, inflected medical-term, rapid-result, ranking, disease-condition, medication/prescription, raw dotted `ghs_` token, path-scan, prevention-claim, Swift-comment, and rendered-view false-greens. Evidence: validator now blocks these claim/token/path classes, strips Swift comments before parsing returns/captures, binds each scenario to the rendered `scenarioView` case, and tests cover each reported bypass. Focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally.
- Late CodeRabbit protected-media/locale-automation scope notes after head `eac8e00f1`: DEFERRED. Evidence: this PR is explicitly `INTERNAL_REVIEW_ONLY`, text/JSON-only, and forbids screenshot/video binaries and protected upload surfaces; `docs/roadmap/BACKLOG_LEDGER.md` keeps protected screenshot/video review, Fastlane upload, App Store Connect mutation, and locale-specific rendered evidence as protected follow-ups. Future protected media or locale-automation lanes may change validator policy with their own tests and release evidence.
- Post-open `qa-engineer-agent` rerun on head `9327943ab`: FAIL with live unresolved review threads. Status: blocking until the mapped fixes are pushed, thread evidence is rechecked, and the live threads are resolved. Evidence: mapped FIXED/DEFERRED evidence exists for known threads, two new CodeRabbit findings were fixed in `cef1c738e`, and merge readiness is not claimed.
- Late CodeRabbit pricing/export batch after head `9327943ab`: FIXED in `cef1c738e`. Evidence: validator now blocks prefix currency price formats and the release-readiness matrix includes protected binary export actions in `blocked_release_actions`; focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally.
- Post-open `qa-engineer-agent` rerun on head `8d4084816`: FAIL with compact ISO-prefix pricing false-greens (`EUR9.99`, `USD9.99`, `RUB999`). Disposition: FIXED in `941042ad3`. Evidence: validator now blocks compact `USD`/`EUR`/`RUB` prefixes before digits; focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.
- Post-open `qa-engineer-agent` rerun on head `c50193797`: FAIL with four current validator false-greens: boundary-negated treatment copy, localized rapid-results copy, generic guaranteed-adherence copy, and spaced credential labels. Disposition: FIXED in `8160d9779`. Evidence: validator now rejects those four classes, tests cover each reported seed, and focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.
- Post-open `qa-engineer-agent` rerun on head `d660b572e`: FAIL on governance only after seed regressions passed; four newer Codex threads required mapping. Status: three actionable threads are FIXED in `47e7dec8d`; one reachability thread is NOT-A-BUG with reachable-commit evidence. Evidence: validator now blocks most-accurate superlatives, cross-platform references, and capture-helper drift; mapped FIXED SHAs are ancestors of current PR head.
- Post-open `qa-engineer-agent` rerun on head `fd4d8532a`: FAIL with three current authority-overclaim false-greens: localized nutrition-professional claims, therapeutic variants, and medical-grade/monitoring copy. Disposition: FIXED in `54539875d`. Evidence: validator now blocks those classes, the real matrix note was rewritten to avoid `medical monitoring`, and focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.
- Post-open `qa-engineer-agent` rerun on head `aabe2eca9`: FAIL with three current release-evidence guard false-greens: snake_case protected release-status claims, generic scalar pricing/trial evidence, and ungoverned Swift screenshot scenarios/methods. Disposition: FIXED in `7359f75ca`. Evidence: validator now scans raw plus underscore/hyphen-collapsed variants for release-status and pricing/trial claims, blocks generic scalar price/trial evidence, and enforces exact Swift App Store screenshot scenario/test method sets; focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.
- Post-open `security-auditor` rerun on head `056117b45`: FAIL with JSON protected-submission status false-greens for extra release-readiness files containing `submit_ready` or `public_submission_allowed` boolean claims. Disposition: FIXED in `d54a118dc`. Evidence: validator now preserves scalar JSON key/value separators during flattening and blocks both submission-status claim families; focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally after the fix.
- Post-open `security-auditor` rerun on head `10a2958b3`: FAIL with branch-staleness governance policy drift against current `origin/main`. Disposition: FIXED in merge commit `34cef2921`. Evidence: the branch was merged forward from `origin/main` without rebase so existing mapped FIXED SHAs remain stable; head now contains the direct Python subprocess interpreter policy in `AGENTS.md` and `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`; post-merge focused tests, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed locally.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950396 -> 9840d503d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950401 -> 9840d503d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950404 -> 9840d503d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950408 -> 9840d503d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950409 -> 9840d503d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363950415 -> 9840d503d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363978756 -> 9840d503d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363978760 -> 9840d503d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3363978762 -> 9840d503d
Disposition: FIXED
Commit: 9840d503d
Evidence: `scripts/release/check_ios_appstore_verify.py` now scans the whole FitChef App Store pack for media/text boundaries, validates `source_paths` values and iOS source files, enforces `blocked_release_actions`, scans every release-readiness JSON/Markdown file for protected claims/secrets/pricing/wellness overclaims, requires `testflight_smoke_status: not_started`, and constrains locale rows to governed FitChef manifest/storyboard paths; `Makefile` adds `tests/test_fitchef_app_store_pack.py` to `ios-appstore-verify`; `tests/ios/test_ios_appstore_verify.py` adds regression tests for all nine review false-greens; focused pytest, validator, `make ios-appstore-verify`, changed-scope validation, and mypy passed locally.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364054086 -> 1a588778f
Disposition: FIXED
Commit: 1a588778f
Evidence: `scripts/release/check_ios_appstore_verify.py` replaced broad same-line negation with bounded forbidden-boundary context logic; `tests/ios/test_ios_appstore_verify.py` and `tests/test_fitchef_app_store_pack.py` reject negation-plus-overclaim separators including comma while preserving safe boundary-list language.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364054091 -> aa49d1492
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364079331 -> aa49d1492
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364134870 -> aa49d1492
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364134876 -> aa49d1492
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364134880 -> aa49d1492
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364134882 -> aa49d1492
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364218433 -> aa49d1492
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364241495 -> aa49d1492
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364241498 -> aa49d1492
Disposition: FIXED
Commit: aa49d1492
Evidence: `scripts/release/check_ios_appstore_verify.py` now scans all JSON/Markdown text under `appstore/fitchef`, redacts credential-like values in release-gate diagnostics, validates per-case Swift `screenshotName` and `accessibilityIdentifier` returns, enforces non-empty scenario/reviewer text and allowed `wellness_claim_status` values, allows natural wellness boundary disclaimers, and rejects punctuation-only negation gaps. `tests/ios/test_ios_appstore_verify.py` removes dynamic `importlib.util` loading and adds regressions for locale-pack protected claims/secrets, redaction, Swift case swaps, blank wellness notes, unsafe wellness statuses, natural disclaimers, and punctuation-only negation bypasses. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `make validate-changed` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365020667 -> ee9407828
Disposition: FIXED
Commit: ee9407828
Evidence: `scripts/release/check_ios_appstore_verify.py` now validates `source_pr` exactly against the landed multilingual localization QA provenance (`number: 1886`, `merge_commit: 26b7cf4f`), and `tests/ios/test_ios_appstore_verify.py` rejects `source_pr: {"number": 0, "merge_commit": ""}`. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365125647 -> 396afada8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365125654 -> 396afada8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365125659 -> 396afada8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365125664 -> 396afada8
Disposition: FIXED
Commit: 396afada8
Evidence: `scripts/release/check_ios_appstore_verify.py` now normalizes release-pack text with accent folding, blocks localized ES/RU medical/wellness fragments, blocks localized trial/pricing fragments and euro price forms, rejects Windows local temp paths with redacted diagnostics, and verifies every FitChef screenshot scenario has a matching XCTest capture method that calls `captureScreenshot(for: .<scenario>)`. `tests/ios/test_ios_appstore_verify.py` adds regressions for Spanish/Russian localized medical claims, Spanish/Russian pricing/trial claims, Windows temp paths, missing XCTest methods, and wrong XCTest capture calls. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; isolated QA probes return blocking errors for localized claims/pricing/path cases; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364079340 -> c613cc153
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364127016 -> c613cc153
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3364127022 -> c613cc153
Disposition: FIXED
Commit: c613cc153
Evidence: `scripts/release/check_ios_appstore_verify.py` now uses `finditer` to evaluate every medical/wellness term occurrence on each line and refuses boundary negation when the same matched term already appears between the marker and current occurrence. `tests/ios/test_ios_appstore_verify.py` adds regressions for `No diagnosis and diagnosis patients.` and `No diagnosis, diagnosis patients.` while existing safe boundary-list and natural disclaimer tests continue to pass. Local evidence after the fix: direct probes reject repeated same-term overclaims and allow natural disclaimers; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365261866 -> c227b9a93
Disposition: FIXED
Commit: c227b9a93
Evidence: `scripts/release/check_ios_appstore_verify.py` now scans localized wellness fragments per line with `finditer` and applies localized ES/RU boundary-negation context instead of treating every boundary disclaimer as an overclaim. `tests/ios/test_ios_appstore_verify.py` adds ES/RU safe-disclaimer regressions plus repeated localized-claim regressions. Local evidence after the fix: direct probes allow localized no-medical-boundary disclaimer fixtures while rejecting repeated localized claims and actual localized medical claims; focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` all passed locally.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365279308 -> 4b1c1c089
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365279316 -> 4b1c1c089
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365279320 -> 4b1c1c089
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365279327 -> 4b1c1c089
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365279335 -> 4b1c1c089
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365376634 -> 4b1c1c089
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365376637 -> 4b1c1c089
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365376640 -> 4b1c1c089
Disposition: FIXED
Commit: 4b1c1c089
Evidence: `scripts/release/check_ios_appstore_verify.py` now normalizes JSON keys/values for release scanning, rejects symlinks under the governed FitChef pack, blocks raw credential-token shapes with redacted diagnostics, blocks localized upload-readiness claims, blocks ruble price formats and scalar JSON pricing/trial values, expands localized wellness blockers for Spanish treatment/professional-role wording, and rejects guaranteed/clinical outcome claims with boundary-aware logic. `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for each blocked false-green class while preserving safe localized boundary-disclaimer coverage. Local evidence after the fix: direct probes for the eight bot-reported classes return blocking errors; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365432376 -> 4c8d71688
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365432378 -> 4c8d71688
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365432383 -> 4c8d71688
Disposition: FIXED
Commit: 4c8d71688
Evidence: `scripts/release/check_ios_appstore_verify.py` now requires the exact FitChef release-readiness schema version, blocks protected-action completion claims for all blocked release-action categories, and rejects forbidden local-artifact path segments anywhere under the governed FitChef App Store pack before content scanning. `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for schema-version drift, protected-action completion variants, and forbidden path segments. Local evidence after the fix: focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` all passed locally.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365497863 -> ebf9eeafc
Disposition: FIXED
Commit: ebf9eeafc
Evidence: `tests/ios/test_ios_appstore_verify.py` now composes credential-like dummy fixture labels and values from scanner-safe parts at runtime instead of storing complete credential-like assignment strings in source. Local evidence after the fix: focused pytest, direct validator, and `pre-commit run --all-files` passed locally.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365497854 -> 09ee45c21
Disposition: FIXED
Commit: 09ee45c21
Evidence: `docs/review/PR_1890_FIXED_MAPPING.md` now splits the earlier combined disposition wording into separate canonical `FIXED` and `DEFERRED` entries with matching evidence. Local evidence after the fix: commit hooks passed, including detect-secrets and conventional commit checks.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365502368 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365502373 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365551287 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365551293 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365551295 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365551299 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365588821 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365588829 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365588838 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365588842 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365635975 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365635979 -> 0c414621f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365635982 -> 0c414621f
Disposition: FIXED
Commit: 0c414621f
Evidence: `scripts/release/check_ios_appstore_verify.py` now blocks medical-professional copy, cure claims, inflected diagnosis/treatment forms, medication/prescription terms including ES/RU medical-context terms, disease-condition claims, rapid-result claims, ranking overclaims, prevention/outcome copy such as `avoid diabetes`, raw dotted `ghs_` token shapes, and protected claims in pack-relative paths. The validator strips Swift comments before parsing screenshot-name/accessibility returns and XCTest capture calls, then verifies every screenshot scenario has a rendered `scenarioView` case with `.appStoreScreenshotRoot(scenario.accessibilityIdentifier)`. `tests/ios/test_ios_appstore_verify.py` adds regressions for each class while preserving safe wellness boundary disclaimers and Spanish `recetas` recipe copy. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365502369
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md` - P1 FitChef App Store rendered review and TestFlight readiness protected follow-ups
Evidence: Current PR scope intentionally requires text/JSON-only App Store pack artifacts and blocks screenshot/video binaries. Protected production media, screenshot/video binary commits, Fastlane upload, and App Store Connect mutation remain separate follow-up lanes; those lanes may revise the media-boundary validator under their own release evidence and tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365588823
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md` - P1 FitChef App Store rendered review and TestFlight readiness protected follow-ups
Evidence: `appstore/fitchef/release_readiness/shot_scenario_matrix.json` records EN/RU/ES rendered-review rows for all seven shots and `appstore/fitchef/release_readiness/rendered_review_testflight_readiness.md` requires a human rendered pass across all locales before protected upload. Locale-specific screenshot launch automation and binary rendered evidence are intentionally deferred to a protected screenshot/export lane; no iOS runtime or Fastlane upload surface is changed in this PR.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365746961 -> cef1c738e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365746963 -> cef1c738e
Disposition: FIXED
Commit: cef1c738e
Evidence: `scripts/release/check_ios_appstore_verify.py` now rejects prefix currency price formats such as `€9,99`, `₽ 999`, and `EUR 9.99`. `appstore/fitchef/release_readiness/shot_scenario_matrix.json` and the validator's expected contract now include `screenshot_binary_export` and `preview_video_export` in `blocked_release_actions`; protected export completion text is also rejected. `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for prefix currency pricing, missing protected export actions, and preview-video export completion claims. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365791433 -> 8160d9779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365791437 -> 8160d9779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365791439 -> 8160d9779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3365791444 -> 8160d9779
Disposition: FIXED
Commit: 8160d9779
Evidence: `scripts/release/check_ios_appstore_verify.py` now treats `treat` after a boundary marker as an actionable medical overclaim instead of a safe boundary word, rejects compact localized rapid-results copy, expands guaranteed-outcome blocking to adherence guarantees, and accepts spaced `api key`, `gh token`, and `secret key` labels as credential-like values with redacted diagnostics. `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for `No diagnosis and treat patients.`, `Resultados rapidos para tu cuerpo.`, `Guaranteed adherence with meal plan.`, and spaced credential labels. Local evidence after the fix: direct probes reject all four reported seeds; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3366980299 -> 47e7dec8d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3366980303 -> 47e7dec8d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3366980306 -> 47e7dec8d
Disposition: FIXED
Commit: 47e7dec8d
Evidence: `scripts/release/check_ios_appstore_verify.py` now rejects `most accurate` unverifiable superlatives, rejects cross-platform App Store copy references such as Google Play / Play Store / Android, and validates that the iOS screenshot `captureScreenshot(for:)` helper uses each scenario for launch arguments, root lookup, and snapshot naming. `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for the reported copy examples plus constant-scenario and constant-snapshot helper drift. Local evidence after the fix: direct probes reject the reported copy seeds; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3366980308
Disposition: NOT-A-BUG
Evidence: The mapped FIXED proof commits are reachable from current PR head. Local proof: `git merge-base --is-ancestor 9840d503d HEAD`, `git merge-base --is-ancestor aa49d1492 HEAD`, `git merge-base --is-ancestor 8160d9779 HEAD`, and `git merge-base --is-ancestor 47e7dec8d HEAD` all returned success; `git log origin/main..HEAD` includes the mapped fix commits. The review's referenced squashed head `1fc6837619b3c443dbf1af093615cbcc0a920b80` is not the live PR head after subsequent pushes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3367001516 -> 54539875d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3367001517 -> 54539875d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3367001519 -> 54539875d
Disposition: FIXED
Commit: 54539875d
Evidence: `scripts/release/check_ios_appstore_verify.py` now rejects localized nutrition-professional claims (`nutricionista`, `dietista`, `диетолог`, `нутрициолог`, and expert-in-nutrition phrases), therapeutic variants (`therapeutic`, `terapeut`), and medical-authority copy (`medical-grade`, `medical monitoring`). `appstore/fitchef/release_readiness/shot_scenario_matrix.json` now avoids the blocked `medical monitoring` phrase in the governed internal note. `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for the reported ES/RU/EN seeds. Local evidence after the fix: direct probes reject the reported seeds; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3367018226 -> 7359f75ca
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3367018227 -> 7359f75ca
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1890#discussion_r3367018229 -> 7359f75ca
Disposition: FIXED
Commit: 7359f75ca
Evidence: `scripts/release/check_ios_appstore_verify.py` now scans raw plus underscore/hyphen-collapsed variants for protected release status and pricing/trial claims, rejects generic scalar price/trial evidence, and enforces exact Swift App Store screenshot scenario/test method sets. `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for snake_case release-status claims, generic scalar JSON pricing/trial evidence, extra Swift screenshot scenario cases, and extra XCTest screenshot methods. Local evidence after the fix: direct probes reject `submit_ready: true`, `ready_for_upload`, `fastlane_upload_completed`, `price 9.99`, and `trial 14`; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

## Post-Open Role-Agent Finding Closure

Finding: post-open `bug-hunter` agent `019e98b2-aa05-7c81-b31a-e3ea0daba98c` reported a comma-clause wellness overclaim bypass.
Disposition: FIXED
Commit: 1a588778f
Evidence: `scripts/release/check_ios_appstore_verify.py` now limits boundary-negation to explicit forbidden-claim context words instead of broad same-line negation; `tests/ios/test_ios_appstore_verify.py` and `tests/test_fitchef_app_store_pack.py` cover `:`, `.`, `;`, `!`, `?`, and `,` separators plus safe boundary-list language. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `../../.venv/bin/python -m mypy scripts/release/check_ios_appstore_verify.py` PASS; `../../.venv/bin/python -m flake8 scripts/release/check_ios_appstore_verify.py tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS.

Finding: `pulseplate-pr-review` dry-run report flagged an advisory large-diff planning note for human review.
Disposition: NOT-A-BUG
Evidence: Operator scope intentionally broadened this release-readiness PR beyond a microscopic docs lane while keeping it bounded to repo-local App Store release-readiness metadata, validators, and tests. The PR does not touch protected upload/runtime surfaces, and the targeted gates plus current-head CI and role reviews cover the expanded scope. No code, security, wellness, or release-boundary defect was reported by the PR review.

Finding: post-open `qa-engineer-agent` agent `019e99f6-0eda-7a80-aaed-8ebfc90cf7db` reported compact ISO-prefix pricing false-greens for `EUR9.99`, `USD9.99`, and `RUB999`.
Disposition: FIXED
Commit: 941042ad3
Evidence: `scripts/release/check_ios_appstore_verify.py` now blocks compact `USD`/`EUR`/`RUB` prefixes before digits, and `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for the three reported compact forms. Local evidence after the fix: `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

Finding: post-open `qa-engineer-agent` agent `019e9bff-724a-7110-8fda-c76e0163088b` reported four current validator false-greens: `No diagnosis and treat patients.`, `Resultados rapidos para tu cuerpo.`, `Guaranteed adherence with meal plan.`, and spaced credential labels such as `api key: [dummy value]`.
Disposition: FIXED
Commit: 8160d9779
Evidence: `scripts/release/check_ios_appstore_verify.py` now rejects all four classes and `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions. Local evidence after the fix: direct probes reject all four reported seeds; `../../.venv/bin/python -m pytest -q tests/ios/test_ios_appstore_verify.py tests/test_fitchef_app_store_pack.py` PASS; `../../.venv/bin/python scripts/release/check_ios_appstore_verify.py` PASS, 11 passed / 0 failed; `make validate-changed` PASS; `DEV_PYTHON=../../.venv/bin/python make ios-appstore-verify` PASS; `pre-commit run --all-files` PASS.

Finding: post-open `qa-engineer-agent` agent `019e9c0d-368c-7e72-bc47-5a6523a3244e` reported three actionable newer Codex threads covering most-accurate copy, cross-platform references, and screenshot capture-helper drift.
Disposition: FIXED
Commit: 47e7dec8d
Evidence: Three actionable threads are FIXED in `47e7dec8d` with deterministic tests and gate evidence.

Finding: post-open `qa-engineer-agent` agent `019e9c0d-368c-7e72-bc47-5a6523a3244e` reported one newer Codex thread claiming mapped FIXED SHAs were unreachable from the PR head.
Disposition: NOT-A-BUG
Evidence: The mapped fix commits are ancestors of current PR head; local `git merge-base --is-ancestor` checks for representative mapped SHAs returned success.

Finding: post-open `qa-engineer-agent` agent `019e9c1b-845a-7042-a751-3a558bae2bd6` reported three current authority-overclaim false-greens: localized nutrition-professional claims, therapeutic variants, and medical-grade/monitoring copy.
Disposition: FIXED
Commit: 54539875d
Evidence: `scripts/release/check_ios_appstore_verify.py` and `tests/ios/test_ios_appstore_verify.py` now reject those classes, and the real matrix note was rewritten to avoid the blocked `medical monitoring` phrase. Local focused gates passed after the fix.

Finding: post-open `qa-engineer-agent` agent `019e9c2a-035f-7d42-8346-51fbafdfce68` reported three current release-evidence guard false-greens: snake_case release-status claims, generic scalar pricing/trial evidence, and ungoverned Swift screenshot scenarios/methods.
Disposition: FIXED
Commit: 7359f75ca
Evidence: `scripts/release/check_ios_appstore_verify.py` and `tests/ios/test_ios_appstore_verify.py` now reject those classes with deterministic regressions. Local evidence after the fix: direct probes reject the reported seeds; focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed.

Finding: post-open `bug-hunter` agent `019e9c5c-5bf4-7970-81ff-a27550fd5600` reported machine-local absolute paths in this mapping artifact's new `ios-appstore-verify` evidence.
Disposition: FIXED
Commit: ff499b651
Evidence: This mapping update replaces the machine-local `DEV_PYTHON` evidence with repo-relative `DEV_PYTHON=../../.venv/bin/python`, keeping the canonical artifact free of absolute local paths. Local evidence after the fix: local-path pattern scan returned no matches; PR body phase2 gates passed; local disposition guard passed.

Finding: post-open `security-auditor` agent `019e9c6a-a6ef-7ec2-9b5c-ed797a6d6cef` reported a fail-open validator gap where extra JSON release-readiness files could assert `submit_ready` or `public_submission_allowed` boolean claims without being blocked.
Disposition: FIXED
Commit: d54a118dc
Evidence: `scripts/release/check_ios_appstore_verify.py` now emits `key: value` and `key=value` scan variants for scalar JSON pairs and blocks `submit ready` plus `public submission allowed` protected claims even when the separator is absent after underscore/hyphen normalization. `tests/ios/test_ios_appstore_verify.py` adds deterministic regressions for `{"submit_ready": true}` and `{"public_submission_allowed": true}` extra JSON files. Local evidence after the fix: direct flatten probes reject both reported payloads; focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed.

Finding: post-open `security-auditor` agent `019e9c79-ffd4-7a90-93fd-4e1af7368f69` reported branch-staleness governance policy drift where the local PR head had not yet incorporated current `origin/main` direct Python subprocess interpreter policy text.
Disposition: FIXED
Commit: 34cef2921
Evidence: `origin/main` was merged into the branch without rebasing, preserving existing fixed-mapping SHAs while bringing the current governance policy into `AGENTS.md` and `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`. Local evidence after the merge: `git rev-list --left-right --count HEAD...origin/main` returned `49 0`; `rg -n "Direct Python subprocess|repo-approved interpreter|sys\\.executable|Repo-approved Python interpreters" AGENTS.md docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md` found the expected policy lines; focused pytest, direct validator, `make validate-changed`, `make ios-appstore-verify`, and `pre-commit run --all-files` passed.

## Main Coverage Carryover

Finding: `main` CI for `889e9a0ad` failed `test-main (3.11, 60)` because global coverage was `96.99%`, below the `97.00%` threshold; `app/services/coaching_state_builder.py` carried 14 missed statements.
Disposition: FIXED
Commit: c98d318c4
Evidence: `tests/test_user_coaching_state.py` now covers fail-closed metric coercion, raw adherence payload object validation, non-dict payload score fallback, and non-datetime event timestamp fallback in the existing coaching-state service. This is a test-only carryover to restore the main coverage threshold; no coaching-state runtime code, route, OpenAPI, DB, frontend, iOS, or App Store release behavior changed.


## Merge Readiness

Not claimed. Required before merge: current-head CI, no unresolved review threads, no actionable bot comments, post-open role passes, Codex Security diff scan / finding discovery, `pulseplate-pr-review`, this mapping updated with every disposition, PR body mirror updated, strict merge-readiness wrapper evidence, and mandatory wait-window.
