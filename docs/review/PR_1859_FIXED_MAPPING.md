# PR #1859 - Fixed in Commit Mapping

**Title:** `chore(toolchain): align runtime pins`
**Branch:** `codex/runtime-toolchain-python-3-13-6`
**Scope:** Runtime/toolchain alignment to Python `3.13.6`, Ruby `3.1`, and Fastlane `2.235.0`.
**Primary commit:** `123b7e7aa`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1859#pullrequestreview-4397396260 -> a25636fe9
Disposition: FIXED
Commit: a25636fe9
Evidence: The aggregate Sourcery review asked for a shared Python version constant and broader workflow scanning; `tests/runtime_toolchain_versions.py:3` now defines `CANONICAL_PYTHON`, `tests/test_python_supply_chain_controls.py:15` imports it, and `tests/test_runtime_toolchain_alignment.py:117` scans both `.yml` and `.yaml` workflow files.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1859#discussion_r3330742616 -> a25636fe9
Disposition: FIXED
Commit: a25636fe9
Evidence: `tests/runtime_toolchain_versions.py:3` defines `CANONICAL_PYTHON`, and `tests/test_python_supply_chain_controls.py:308` / `tests/test_python_supply_chain_controls.py:330` use it instead of hardcoded `3.13.6` workflow assertions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1859#discussion_r3330742620 -> a25636fe9
Disposition: FIXED
Commit: a25636fe9
Evidence: `tests/test_runtime_toolchain_alignment.py:117` builds the workflow scan from both `*.yml` and `*.yaml` patterns before checking for bare `3.13` setup-python pins.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1859#discussion_r3330747454 -> a25636fe9
Disposition: FIXED
Commit: a25636fe9
Evidence: `.tool-versions:2` now pins `ruby 3.1`, and `tests/test_runtime_toolchain_alignment.py:70` / `tests/test_runtime_toolchain_alignment.py:72` assert the parsed `.tool-versions` Ruby entry matches the canonical Ruby pin.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1859#discussion_r3330747452
Disposition: NOT-A-BUG
Evidence: `.python-version:1` and `.tool-versions:1` intentionally pin local Python to `3.13.6`, matching the operator-approved runtime target and current CI `PYTHON_VERSION`; local validation on this host reports `python3 --version` as `Python 3.13.6` and `pyenv versions --bare` includes `3.13.6`.
Reason: A checkout whose pyenv has not installed the repo-pinned patch will fail until the developer installs the declared version; reverting local pins to `3.13.13` would reintroduce the exact local/CI drift this PR exists to close.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1859#discussion_r3330754983 -> 7fc34a1d4
Disposition: FIXED
Commit: 7fc34a1d4
Evidence: `docs/review/PR_1859_FIXED_MAPPING.md` no longer claims `No actionable review comments`; it maps the Sourcery and Codex actionable review comments with FIXED or NOT-A-BUG dispositions and proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1859#discussion_r3330754987 -> a25636fe9
Disposition: FIXED
Commit: a25636fe9
Evidence: `tests/test_runtime_toolchain_alignment.py:57` parses `.tool-versions` by tool key, while `tests/test_runtime_toolchain_alignment.py:70` / `tests/test_runtime_toolchain_alignment.py:72` assert both Python and Ruby entries instead of freezing `.tool-versions` to one Python-only line.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1859#discussion_r3330754988
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor 123b7e7aa HEAD` exited 0 locally at branch head `7fc34a1d4`, proving the primary implementation commit recorded in this artifact is reachable from the current PR branch history.
Reason: The reviewed connector SHA was a synthetic merge/review view, not the canonical PR branch head. The artifact records implementation and mapping proof commits that are reachable from the actual PR branch.

## Implementation Evidence

Disposition: FIXED
Commit: 123b7e7aa
Evidence: `.python-version` and `.tool-versions` pin the local Python runtime to `3.13.6`, matching the canonical CI env used by `.github/workflows/ci.yml` and `.github/workflows/frontend-ci.yml`.

Disposition: FIXED
Commit: a25636fe9
Evidence: `.tool-versions` now also pins `ruby 3.1`, so mise/asdf-managed local checkouts use the same Ruby family as `.ruby-version` and the CI/Fastlane workflows.

Disposition: FIXED
Commit: 123b7e7aa
Evidence: `.ruby-version` adds a repo-local Ruby source with `3.1`, matching the Ruby family used by the CI/Fastlane workflows.

Disposition: FIXED
Commit: 123b7e7aa
Evidence: `ios/Gemfile` pins `fastlane` to `= 2.235.0`, and `ios/Gemfile.lock` records the matching dependency constraint while preserving the already-resolved `fastlane (2.235.0)` spec.

Disposition: FIXED
Commit: 123b7e7aa
Evidence: Auxiliary workflow setup-python pins in `.github/workflows/build-equivalence-evidence.yml`, `.github/workflows/ci-metrics.yml`, `.github/workflows/experiment-runner-dispatch.yml`, `.github/workflows/experiment-runner-slack-socket-smoke.yml`, `.github/workflows/nightly.yml`, `.github/workflows/release-control-plane-evidence.yml`, and `.github/workflows/release-manifest-evidence.yml` use exact `3.13.6` runtime pins instead of bare `3.13`.

Disposition: FIXED
Commit: 123b7e7aa
Evidence: `tests/test_runtime_toolchain_alignment.py` verifies local Python/Ruby sources, visible CI label preservation, auxiliary setup-python pins, and Fastlane/Gemfile.lock parity.

Disposition: FIXED
Commit: a25636fe9
Evidence: `tests/test_runtime_toolchain_alignment.py` now parses `.tool-versions` by tool key and scans both `.github/workflows/*.yml` and `.github/workflows/*.yaml`, while `tests/runtime_toolchain_versions.py` centralizes the canonical test constants.

Disposition: FIXED
Commit: 123b7e7aa
Evidence: `tests/test_python_supply_chain_controls.py::test_nightly_workflow_jobs_use_runtime_dev_direct_proxy_setup` now expects the exact `3.13.6` nightly direct-proxy runtime while keeping private-index/direct-proxy controls intact.

Disposition: FIXED
Commit: 123b7e7aa
Evidence: `docs/review/PR_RUNTIME_TOOLCHAIN_ALIGNMENT_PREMORTEM.md` records the premortem risk review for Python patch-pin drift, check-label preservation, auxiliary workflow normalization, Fastlane pinning, Ruby drift, private-index availability, and out-of-scope SQLite/Docker surfaces.

## Role-Agent / Premortem Pass

- `agent-coordinator` - completed; initial block on main current-head health was operator-overridden for this lane.
- `dev-operator` - completed; validation plan, local Ruby timeout risk, and machine-heavy gate deferral were recorded.
- `architecture-specialist` - completed; required exact runtime pins while preserving visible `3.13` CI labels and keeping Python `3.11` / `3.12` diagnostics.
- `app-store-release-agent` - completed; confirmed Fastlane pin is release-tooling scope only and does not touch App Store metadata, upload lanes, screenshots, privacy files, or iOS deployment target.
- `qa-engineer-agent` - completed; required a structured guard covering Python pin source, check-name stability, Fastlane parity, and supply-chain controls.
- `bug-hunter` - completed; reviewed drift hazards around auxiliary workflows, Gemfile/Gemfile.lock parity, and accidental Docker/Node/SQLite scope expansion.
- `security-auditor` - completed; reviewed private-index/direct-proxy, workflow supply-chain, action pin, secret handling, and Fastlane release-surface boundaries.
- `frontend-engineer` - completed; confirmed no frontend package, Node, OpenAPI, or generated client changes are in scope.
- `creative-designer` - completed; confirmed no design-token, screenshot, copy, or UI-asset changes are in scope.
- `pulseplate-premortem-risk-review` - completed in `docs/review/PR_RUNTIME_TOOLCHAIN_ALIGNMENT_PREMORTEM.md`.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/25cc045688f1.json`
- Operator override: main current-head health was treated as non-blocking by explicit operator instruction for this lane.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/runtime_toolchain_alignment_oracle_result.json`
- Mode: `oracle_review`
- Result: accepted; both oracle commands returned `0`; `shared_tree_untouched=true`; `source_diff_applied=true`; `coauthor_required=true`.
- Commit trailer used: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` on commit `123b7e7aa`.
- Squash-merge note: if this PR is squash-merged, preserve `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` in the final merge commit message.

## Codex Security Evidence

- Scan: `/tmp/codex-security-scans/runtime-toolchain-python-3-13-6/local_runtime_toolchain_20260531T182544Z/report.md`
- HTML: `/tmp/codex-security-scans/runtime-toolchain-python-3-13-6/local_runtime_toolchain_20260531T182544Z/report.html`
- Result: no reportable findings in the runtime/toolchain diff.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path ...` - PASS.
- `python scripts/orchestration/check_agent_consistency.py` - PASS.
- `python -m pytest -q tests/test_runtime_toolchain_alignment.py tests/test_python_supply_chain_controls.py::test_nightly_workflow_jobs_use_runtime_dev_direct_proxy_setup tests/test_jwt_fastlane_unblock_guard.py` - PASS.
- `python -m pytest -q tests/test_runtime_toolchain_alignment.py tests/test_python_supply_chain_controls.py tests/test_jwt_fastlane_unblock_guard.py tests/test_current_head_pr_checks.py tests/test_build_equivalence_evidence_workflow.py tests/test_release_manifest_evidence_workflow.py tests/test_release_control_plane_evidence_publication_workflow.py` - PASS.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_runtime_toolchain_alignment.py tests/test_python_supply_chain_controls.py tests/test_jwt_fastlane_unblock_guard.py` - PASS after Sourcery/Codex review fixes.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/ruff check tests/test_runtime_toolchain_alignment.py tests/test_python_supply_chain_controls.py tests/runtime_toolchain_versions.py` - PASS after Sourcery/Codex review fixes.
- `ruff check tests/test_runtime_toolchain_alignment.py tests/test_python_supply_chain_controls.py` - PASS.
- `git diff --check` - PASS.
- `make validate-changed` - PASS (`49 passed` after commit).
- `pre-commit run --all-files` - PASS.
- Pre-push hooks - PASS.

## Local Ruby / Fastlane Deferral

- `python scripts/ci/check_jwt_fastlane_unblock.py` timed out after 180 seconds in the local Bundler resolver/network path.
- `cd ios && bundle install && bundle exec fastlane ios validate_metadata_package` did not reach Fastlane because local `bundle install` timed out after 300 seconds in the Bundler resolver/network path.
- CI `Ruby jwt/Fastlane unblock guard` passed on current-head run `26721168101`; Fastlane metadata validation still requires current-head CI or a local Ruby resolver that completes.

## Machine-Heavy Gate Deferral

Full local `make verify` is deferred under the operator-approved machine-heavy exception for this CI/tooling PR. This artifact does not claim full local verify readiness.

Merge readiness still requires current-head CI parity, no unresolved review threads, no actionable bot findings, mandatory post-open `qa-engineer-agent -> bug-hunter -> security-auditor`, strict merge-readiness checks, and the mandatory wait-window.
