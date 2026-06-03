# PR #1871 - Fixed in Commit Mapping

**Title:** `fix(ci): migrate gha action pins to node24`
**Branch:** `codex/gha-node24-action-runtime-cleanup`
**Scope:** CI workflow JavaScript action runtime cleanup only. This PR updates
direct Node20-era GitHub Actions pins to verified Node24-compatible commit SHAs
and adds guard coverage. It does not change app/runtime Node, Python
dependencies, private-index policy, backend/OpenAPI, frontend runtime, Docker
image behavior, release logic, permissions, secrets, cache policy, or
operator-override behavior.
**Primary implementation commits:** `ef1a745654e89d7a14f676e70001c010878eff4a`,
`e556119b444742135cced7793b0da38aaa8f9353`,
`c6aabad09ab876bb13b7f2700363166ee386880c`,
`6e1b7f425e52cadcc2864a666102e1f7d6f2ddf8`,
`be9e1a5d2d8f3427af2d70627e571b286b235651`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [ ] Post-open bot/human review disposition completed after latest push

Current live PR snapshot before the latest mapping update:

- Codex Review posted one actionable inline comment on the Trivy wrapper pin.
  This is mapped below to `be9e1a5d2d8f3427af2d70627e571b286b235651`.
- Codex Review posted one mapping-ancestry inline comment against a synthetic
  reviewed head. This is dispositioned below as `NOT-A-BUG` because the mapped
  commits are ancestors of the real GitHub PR head.
- CodeRabbit had posted a summary comment only.
- Sourcery returned a weekly-rate-limit comment, not a code actionable.
- Cubic reported no issues on the initial head.
- Current-head CI and bot review must be rechecked after this mapping update is
  pushed.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1871 -> ef1a745654e89d7a14f676e70001c010878eff4a
Disposition: FIXED
Commit: ef1a745654e89d7a14f676e70001c010878eff4a
Evidence: Initial implementation replaced scoped checkout and Docker JavaScript action pins with verified Node24-compatible full commit SHAs and added guard coverage for old SHA absence, exact Node24 pin counts, forbidden operator override literal absence, and Docker step behavior preservation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1871 -> e556119b444742135cced7793b0da38aaa8f9353
Disposition: FIXED
Commit: e556119b444742135cced7793b0da38aaa8f9353
Evidence: Post-open QA found remaining direct Node20 `actions/setup-go` and `actions/upload-artifact` pins in the touched workflow surface. The commit updates those refs to verified Node24-compatible full commit SHAs and extends `tests/test_ci_workflow_pr_size_governance_contract.py` so the old SHAs cannot be reintroduced.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/26880958762/job/79280576044 -> c6aabad09ab876bb13b7f2700363166ee386880c
Disposition: FIXED
Commit: c6aabad09ab876bb13b7f2700363166ee386880c
Evidence: Current-head Greenlight failed because `greenlight@v0.1.0` requires Go `>=1.24.0` while the workflow still used `go-version: "1.22"` with `GOTOOLCHAIN=local`. The commit updates only `.github/workflows/greenlight-ios.yml` to Go `1.24` and updates the workflow guard snapshot.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/26881378007/job/79282206670 -> 6e1b7f425e52cadcc2864a666102e1f7d6f2ddf8
Disposition: FIXED
Commit: 6e1b7f425e52cadcc2864a666102e1f7d6f2ddf8
Evidence: Current-head Docker/security-scan logs showed the remaining Node20 warning came from `aquasecurity/trivy-action@57a97c7e7821a5776cebc9bb87c984fa69cba8f1 # v0.35.0`, whose composite action invoked nested `actions/cache@0400d5f644dc74513175e3cd8d07132dd4860809 # v4.2.4` with `runs.using: node20`. The commit updates only the pinned Trivy wrapper action in `.github/workflows/build.yml` and `.github/workflows/trivy.yml` to `aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0 / Node 24 cache path`, preserving Trivy binary `version: v0.69.3` and scan inputs, and extends `tests/test_ci_workflow_pr_size_governance_contract.py` to reject the old wrapper SHA plus nested cache warning source.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1871#discussion_r3348168393 -> be9e1a5d2d8f3427af2d70627e571b286b235651
Disposition: FIXED
Commit: be9e1a5d2d8f3427af2d70627e571b286b235651
Evidence: Codex Review correctly identified that the previous `aquasecurity/trivy-action@a9c7b0f06e461e9d4b4d1711f154ee024b8d7ab8` ref was the annotated `v0.36.0` tag object rather than the peeled commit. `git ls-remote https://github.com/aquasecurity/trivy-action.git 'refs/tags/v0.36.0*'` showed `a9c7b0f06e461e9d4b4d1711f154ee024b8d7ab8 refs/tags/v0.36.0` and `ed142fd0673e97e23eac54620cfb913e5ce36c25 refs/tags/v0.36.0^{}`. The commit updates only the Trivy action refs and workflow guard constant to the peeled commit SHA while preserving all Trivy scanner inputs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1871#discussion_r3348494286
Disposition: NOT-A-BUG
Evidence: The review comment referenced synthetic reviewed head `41440402068da0a827fc6d43fc3fe608d373aeff`, not the actual PR branch head. Local ancestry proof on the real branch head (`git merge-base --is-ancestor <mapped_sha> HEAD`) returned `ancestor` for `ef1a745654e89d7a14f676e70001c010878eff4a`, `e556119b444742135cced7793b0da38aaa8f9353`, `c6aabad09ab876bb13b7f2700363166ee386880c`, `6e1b7f425e52cadcc2864a666102e1f7d6f2ddf8`, `be9e1a5d2d8f3427af2d70627e571b286b235651`, and `191a0671d8c279ff1eabcee41f610af9a6ae3134`. `git cat-file -e 41440402068da0a827fc6d43fc3fe608d373aeff^{commit}` did not find that synthetic commit in local branch history. The mapping therefore already ties fixes to commits that will be merged from the actual PR branch.
Reason: The comment checked ancestry against a synthetic/non-branch reviewed head instead of the real GitHub PR head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/26882447867/job/79285782067 -> 191a0671d8c279ff1eabcee41f610af9a6ae3134
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/26882447867/job/79285782087 -> 191a0671d8c279ff1eabcee41f610af9a6ae3134
Disposition: FIXED
Commit: 191a0671d8c279ff1eabcee41f610af9a6ae3134
Evidence: Current-head `test-main` shards failed `tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths` because review evidence used machine-local absolute command paths. The commit replaces those paths with repo-relative `.venv/bin/python` commands and adds `docs/ENGINEERING_LESSONS.md` guidance for this repeated CI loop pattern.

## Dependency Scope / Private-Index Notes

- No `frontend/package.json`, `frontend/package-lock.json`,
  `requirements*.txt`, `constraints.txt`, `.github/actions/python-setup`, or
  `scripts/ci/install_locked_python_requirements.py` changes.
- Python private-index validation remains unchanged and explicit:
  `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json`.
- No public-PyPI bypass, ambient `PIP_INDEX_URL` /
  `PIP_EXTRA_INDEX_URL` override, or emergency-wheel widening was introduced.
- No `CI_ALLOW_MERGE_OVERRIDE`, `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION`, or
  docs-only merge bypass was added.

## Implementation Evidence

Disposition: FIXED
Commit: `ef1a745654e89d7a14f676e70001c010878eff4a`
Evidence:

- `.github/workflows/cd-test.yml`, `.github/workflows/codecov-upload.yml`,
  `.github/workflows/codeql.yml`, `.github/workflows/greenlight-ios.yml`,
  `.github/workflows/ios-appstore-assets.yml`, and
  `.github/workflows/security.yml` use the repo-adopted
  `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd` Node24 pin.
- `.github/workflows/build.yml`, `.github/workflows/cd.yml`, and
  `.github/workflows/trivy.yml` use verified Node24 Docker
  setup-buildx/login/metadata action pins.
- The workflow guard rejects the old checkout and Docker Node20 SHAs, checks
  exact Node24 pin counts, preserves Docker step `with`, `if`, `env`, and
  `continue-on-error` contracts, and rejects operator override env literals.
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-gha-node24-cache-warning-cleanup`
  remains open because cache-warning audit and current-head warning evidence are
  not complete yet.

Disposition: FIXED
Commit: `e556119b444742135cced7793b0da38aaa8f9353`
Evidence:

- `.github/workflows/greenlight-ios.yml` now uses
  `actions/setup-go@4a3601121dd01d1626a1e23e37211e3254c1c06c # v6.4.0 / Node 24`
  and
  `actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1 / Node 24`.
- `.github/workflows/ios-appstore-assets.yml` and
  `.github/workflows/security.yml` now use the same verified Node24
  `actions/upload-artifact` pin.
- GitHub API metadata checks confirmed the selected `actions/setup-go` and
  `actions/upload-artifact` SHAs declare `runs.using: node24`.
- `tests/test_ci_workflow_pr_size_governance_contract.py` rejects the retired
  setup-go/upload-artifact Node20 SHAs and snapshots the setup/upload step
  contracts for the touched workflows.

Disposition: FIXED
Commit: `c6aabad09ab876bb13b7f2700363166ee386880c`
Evidence:

- `.github/workflows/greenlight-ios.yml` now uses `go-version: "1.24"` for the
  Greenlight preflight, matching the current-head log requirement that
  `greenlight@v0.1.0` requires Go `>=1.24.0`.
- `tests/test_ci_workflow_pr_size_governance_contract.py` snapshots the
  Greenlight setup-go contract with Go `1.24`.

Disposition: FIXED
Commit: `6e1b7f425e52cadcc2864a666102e1f7d6f2ddf8`
Evidence:

- Current-head Docker/security-scan log evidence identified the remaining
  `actions/cache@0400d5f644dc74513175e3cd8d07132dd4860809` Node20 warning as a
  nested step inside
  `aquasecurity/trivy-action@57a97c7e7821a5776cebc9bb87c984fa69cba8f1`, not a
  direct workflow `actions/cache` pin.
- GitHub `git ls-remote` metadata for `aquasecurity/trivy-action@v0.36.0`
  confirms the selected full commit SHA
  `ed142fd0673e97e23eac54620cfb913e5ce36c25` uses nested
  `actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae # v5.0.5`.
- GitHub API metadata for the old nested cache SHA confirmed
  `runs.using: node20`.
- `.github/workflows/build.yml` and `.github/workflows/trivy.yml` update only
  the pinned Trivy wrapper action. The Trivy binary remains `version: v0.69.3`
  and scan inputs, severity, SARIF output, and fail/report-only contracts are
  preserved by guard assertions.

Disposition: FIXED
Commit: `191a0671d8c279ff1eabcee41f610af9a6ae3134`
Evidence:

- `docs/review/PR_1871_FIXED_MAPPING.md` no longer records local absolute
  command paths; repo-relative `.venv/bin/python` command evidence is used
  instead.
- `docs/ENGINEERING_LESSONS.md` now records the repeated loop pattern: do not
  paste machine-local absolute paths into review docs or PR body mirrors.
- The exact failed guard was rerun locally and passed:
  `tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths`.

## Role-Agent / Premortem Pass

Pre-open role order completed from packet
`artifacts/orchestration/task_packets/495c23aac239.json`:

- `agent-coordinator` - PASS; scope locked to CI action runtime cleanup and
  excluded app/runtime Node bump and operator override behavior.
- `security-auditor` - PASS; required full commit SHAs, old-SHA absence, no
  secret/permission drift, and no Node20 opt-out envs.
- `architecture-specialist` - PASS; required behavior-preservation guard
  coverage and kept the cache-warning backlog open.
- `qa-engineer-agent` - PASS; required exact pin/count assertions and
  current-head PR log evidence before any closure claim.
- `bug-hunter` - PASS; identified the false-green gap in the existing Node24
  guard surface.
- `cursor-specialist-agent` - PASS; flagged stale-loop/upstream tracking risk.
- `web-research-agent` - PASS; registered the official Node20 deprecation
  driver and action metadata verification boundary.

Post-open role order from packet
`artifacts/orchestration/task_packets/9366b0634ad1.json`:

- `agent-coordinator` - BLOCK until the canonical mapping artifact is added,
  PR body Phase2 mirror is updated, QA-found Node20 pins are fixed, and
  current-head checks are re-run.
- `qa-engineer-agent` - FIXED; found direct `actions/setup-go` and
  `actions/upload-artifact` Node20 pins that could keep the warning alive.
  Commit `e556119b444742135cced7793b0da38aaa8f9353` fixes the pins and guard
  coverage.
- `bug-hunter` - PASS after the QA fix; no code-level blocker found, with
  mapping/push still required.
- `security-auditor` - PASS after the QA fix; no security finding on
  permissions, secrets, fail-open behavior, moving refs, or old direct Node20
  pins, with mapping/push still required.
- `cursor-specialist-agent` - BLOCK before publication; found no committed
  code-scope blocker, but required committing this mapping artifact and backlog
  edit, pushing `e556119b444742135cced7793b0da38aaa8f9353`, updating the PR
  body mirror, and rechecking current-head CI before any readiness claim.
- `web-research-agent` - PASS for upstream metadata/no-override evidence and
  BLOCK for current-head warning evidence until the local QA-fix is pushed.
  Evidence: selected `actions/setup-go` and `actions/upload-artifact` SHAs
  declare `runs.using: node24`; current published logs still reflected the old
  `ef1a745654e89d7a14f676e70001c010878eff4a` head.

Premortem:

- Skill: `pulseplate-premortem-risk-review`.
- Frame: 48 hours from now this CI cleanup made things worse.
- Decision: proceed with narrow changes.
- Closed as FIXED: missed legacy Node20 pins, Docker action behavior drift, and
  backlog over-closure risk.
- Post-open correction: QA showed the missed-pins risk was not fully closed on
  the initial published head because `actions/setup-go` and
  `actions/upload-artifact` still used Node20-era SHAs. Commit
  `e556119b444742135cced7793b0da38aaa8f9353` and Experiment Runner v3 close
  that premortem risk for the local head before republishing.
- Current-head log correction: Docker/security-scan logs then showed one
  remaining warning from nested `actions/cache@0400d5...` inside
  `aquasecurity/trivy-action@57a97...`. Commit
  `6e1b7f425e52cadcc2864a666102e1f7d6f2ddf8` and Experiment Runner v4 close the
  code-side residual by updating the wrapper action to v0.36.0, whose nested
  cache path is `actions/cache@27d5... # v5.0.5`.
- Residual risk after this fix: current-head GitHub logs after the next push
  still must prove the warning cleanup and disposition any unrelated cache
  service availability noise.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/gha-node24-action-runtime-cleanup-oracle-packet-v2.json`
- Artifact: `artifacts/orchestration/experiments/results/gha-node24-action-runtime-cleanup-oracle-result-v2.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted.
- Oracles: old checkout/Docker Node20 SHA and bypass literal absence, action
  pin guard, docs phase1 gate.
- `mutated_paths=[]`
- `coauthor_required=true`
- Commit trailer used on `ef1a745654e89d7a14f676e70001c010878eff4a`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

- Packet: `artifacts/orchestration/experiments/gha-node24-action-runtime-cleanup-oracle-packet-v3.json`
- Artifact: `artifacts/orchestration/experiments/results/gha-node24-action-runtime-cleanup-oracle-result-v3.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted.
- Oracles: old checkout/Docker/setup-go/upload-artifact Node20 SHA and bypass
  literal absence, action pin guard, focused workflow guard pytest.
- `mutated_paths=[]`
- `coauthor_required=true`
- Commit trailer used on `e556119b444742135cced7793b0da38aaa8f9353`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

- Packet: `artifacts/orchestration/experiments/gha-node24-action-runtime-cleanup-oracle-packet-v3.json`
- Artifact: `artifacts/orchestration/experiments/results/gha-node24-action-runtime-cleanup-oracle-result-v4.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted.
- Oracles: old checkout/Docker/setup-go/upload-artifact Node20 SHA and bypass
  literal absence, action pin guard, focused workflow guard pytest. The focused
  workflow guard now also rejects the old `aquasecurity/trivy-action@57a97...`
  wrapper and nested `actions/cache@0400d5...` Node20 warning source.
- `mutated_paths=[]`
- `coauthor_required=true`
- Commit trailer used on `6e1b7f425e52cadcc2864a666102e1f7d6f2ddf8`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --mode analyze ...` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json` - PASS.
- `.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py` - PASS; 21 tests.
- `python3 scripts/ci/guard_actions_pin.py --root .` - PASS.
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md` - PASS.
- `python3 scripts/orchestration/experiment_runner.py --packet artifacts/orchestration/experiments/gha-node24-action-runtime-cleanup-oracle-packet-v3.json ...` - PASS; result accepted.
- Commit hooks for `ef1a745654e89d7a14f676e70001c010878eff4a` - PASS.
- Commit hooks for `e556119b444742135cced7793b0da38aaa8f9353` - PASS after
  `black` formatted the guard test.
- Direct `python3 -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py`
  outside the repo venv failed with `ModuleNotFoundError: No module named
  'fastapi'`; rerun with the repo venv passed.

- `make validate-changed` - PASS after the mapping/backlog edit; selected
  `tests/test_ci_workflow_pr_size_governance_contract.py`, 21 tests.
- `.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py`
  - PASS after the Greenlight Go `1.24` fix; 21 tests.
- `python3 scripts/ci/guard_actions_pin.py --root .` - PASS after the
  Greenlight Go `1.24` fix.
- `.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py -q`
  - PASS after the Trivy wrapper/cache-path fix; 21 tests.
- `python3 scripts/ci/guard_actions_pin.py --root .` - PASS after the Trivy
  wrapper/cache-path fix.
- `make validate-changed` - PASS after the Trivy wrapper/cache-path fix;
  selected `tests/test_ci_workflow_pr_size_governance_contract.py`, 21 tests.
- `python3 scripts/orchestration/experiment_runner.py --packet artifacts/orchestration/experiments/gha-node24-action-runtime-cleanup-oracle-packet-v3.json --output gha-node24-action-runtime-cleanup-oracle-result-v4.json ...`
  - PASS; result accepted with source diff paths `.github/workflows/build.yml`,
  `.github/workflows/trivy.yml`, and
  `tests/test_ci_workflow_pr_size_governance_contract.py`.
- `tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths`
  - PASS after replacing machine-local absolute command paths with repo-relative
  evidence.
- Trivy peeled commit fix:
  - `git ls-remote https://github.com/aquasecurity/trivy-action.git 'refs/tags/v0.36.0*'`
    showed tag object `a9c7b0f06e461e9d4b4d1711f154ee024b8d7ab8` and peeled
    commit `ed142fd0673e97e23eac54620cfb913e5ce36c25`.
  - `.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py`
    - PASS; 21 tests.
  - `python3 scripts/ci/guard_actions_pin.py --root .` - PASS.
  - `python3 scripts/ci/check_docs_phase1_gates.py --files docs/review/PR_1871_FIXED_MAPPING.md docs/roadmap/BACKLOG_LEDGER.md docs/ENGINEERING_LESSONS.md`
    - PASS.
  - `python3 scripts/ci/check_pr_body_phase2_gates.py --body "$(cat /tmp/pr1871_body_update.md)" --pr-number 1871 --commit-range origin/main..HEAD --experiment-runner-evidence-mode advisory`
    - PASS.
  - `pre-commit run --all-files` - PASS.

Pending after this mapping commit:

- Current-head GitHub CI/log review after the next push

## Codex Security Evidence

- Scan directory:
  `/tmp/codex-security-scans/BMI-App_2025_clean/c6aabad09_20260603T111626Z`
- Mode: diff-scoped security scan / finding discovery for PR #1871 local head
  plus the prepared mapping artifact.
- Result: no findings.
- Coverage: 12/12 rows in
  `artifacts/02_discovery/deep_review_input.csv` have receipts in
  `artifacts/02_discovery/work_ledger.jsonl`.
- Note: the default source-like diff helper produced zero rows for
  workflow/docs/test files, so the scan manually seeded the final workflow,
  guard-test, backlog, and mapping surfaces to avoid a false no-op security
  scan.
- Final reports written and validated:
  - `report.md`
  - `report.html`

## PulsePlate PR Review Evidence

- Context: `/tmp/pulseplate_pr1871_review_context.json`
- Reports:
  - `/tmp/pulseplate_pr1871_review_report.md`
  - `/tmp/pulseplate_pr1871_review_report.json`
- Mode: side-effect-free dry-run report for local head.
- Result: one advisory `note` from `bug-hunter` for large-diff review risk.
- Disposition: NOT-A-BUG.
- Evidence: scope is intentionally limited to representative workflow `uses:`
  refs, one guard test, and the existing backlog row; `make validate-changed`
  passed after the mapping/backlog edit and selected
  `tests/test_ci_workflow_pr_size_governance_contract.py`.
- Reason: the advisory note is review-planning evidence, not a code/security
  actionable, and does not replace current-head CI or bot review governance.

## Merge Readiness

- Current-head PR CI must pass on the latest pushed head before merge.
- Docker Build and Push, CodeQL, CI, and touched workflow logs must be checked
  for direct Node20 action warnings after the latest push.
- The broader cache-warning backlog item remains open until representative log
  evidence is available.
- Review-thread disposition must pass with GitHub auth after final bot review.
- Bot actionables must be fixed or explicitly dispositioned before merge.
- Strict `check_merge_ready.py --require-auth` must pass before any
  merge-readiness claim.
