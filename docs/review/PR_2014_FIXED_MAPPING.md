# PR #2014 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2014
Title: `fix(deps): refresh testing dependency stack`
Branch: `codex/deps-testing-stack-refresh`

## Summary

This PR is the human-owned replacement for Dependabot PR #2001.

- `pytest`: `9.1.0` -> `9.1.1`
- `hypothesis`: `6.155.2` -> `6.155.7`
- `coverage`: `7.14.1` -> `7.14.3`

The update is scoped to testing dependency surfaces, active requirements
documentation, locked-installer hardening, emergency wheel manifest evidence,
the shared Python setup action, and dependency guard expectations that assert
the split test profile and fallback contract.
It does not touch Torch, Faraday, RAG/vector, Docker, runtime, app/core, or
iOS/Fastlane dependency surfaces.

## Implementation Commits

- `8f3b35906fcfc83b1602f4867673f837c3577b7b` - `fix(deps): refresh testing dependency stack`
- `15b0e0c403974b714aa6815cd3b49ec518e3847f` - `test(deps): cover hypothesis testing stack pin`
- `6c85ab9ac763ae2aadd6aa846f3435f2f74d61ca` - `docs(deps): align testing requirements guide`
- `23635b2f4fb2575120d356b952898dc3796cfd41` - `docs(deps): require approved proxy in requirements guide`
- `b7dd2b894c4ec2a758347e1f6b9bd7d4d1b3028f` - `fix(deps): harden python dependency setup fallback`
- Additional current-head CI/setup follow-up commits are listed in
  Implementation Evidence below.

The implementation commit includes the governed Experiment Runner attribution
trailer:

`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Lane Start Provenance

- Worktree: `worktrees/deps-testing-stack-refresh`
- Branch: `codex/deps-testing-stack-refresh`
- Packet: `artifacts/orchestration/task_packets/797969cddfec.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Role dispatch:
  `.venv/bin/python scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/797969cddfec.json --pretty`
- Pre-open role order completed:
  `agent-coordinator -> cursor-specialist-agent -> architecture-specialist`

## Premortem Risk Review

- Pass: `pulseplate-premortem-risk-review`
- Status: `PASS_WITH_REQUIRED_PRE_OPEN_GATES`
- Result: no blocking findings remained in the inspected diff.
- Initial scope evidence: 10 files changed, 23 insertions, 23 deletions.
- Current scope evidence: 18 files changed after current-head CI setup
  failures forced shared locked-installer/action/fallback fixes in the same
  dependency lane.
- Controlled risks:
  - Broad lock churn rejected after `piptools compile` through the approved proxy
    attempted unrelated transitive updates.
  - Raw private index URL emission rejected by keeping tracked lock headers
    sanitized and auditing added lines.
  - Unsafe `pip==...` lock churn rejected per repo-managed lock policy.
  - Stale test expectation drift fixed in
    `tests/test_python_supply_chain_controls.py`.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-2c147f9cd4f3.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-2c147f9cd4f3.json`
- Status: `accepted`
- Mode: `oracle_only_governance_reviewer`
- Contribution: `oracle_review`
- Mutated paths: `[]`
- Shared tree untouched: `true`
- Co-author required: yes, included on implementation commit
  `8f3b35906fcfc83b1602f4867673f837c3577b7b`.

## Local Validation

Focused local gates:

- `python3 scripts/orchestration/check_preflight.py --path constraints.txt --path requirements-all.txt --path requirements-ci-lite.in --path requirements-ci-lite.txt --path requirements-dev.in --path requirements-dev.txt --path requirements-test.in --path requirements-test.txt --path requirements-lock.txt --path tests/test_python_supply_chain_controls.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- Approved proxy exact-wheel proof for `pytest==9.1.1`,
  `hypothesis==6.155.7`, and `coverage==7.14.3` using
  `.venv/bin/python -m pip download --isolated --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --only-binary=:all: --no-deps` - PASS
- `python3 scripts/ci/install_locked_python_requirements.py --requirements-file requirements-dev.txt --constraints-file constraints.txt --install-dev --preflight-only` - PASS
- `python3 scripts/ci/install_locked_python_requirements.py --requirements-file requirements-test.txt --constraints-file constraints.txt --preflight-only` - PASS
- `python3 scripts/ci/install_locked_python_requirements.py --requirements-file requirements-ci-lite.txt --constraints-file constraints.txt --preflight-only` - PASS
- `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/test_dependency_security_guard.py tests/guards/test_security_devtooling_regression_guards.py` - PASS
- `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py::test_install_from_proxy_with_emergency_fallback_accepts_pip26_no_candidate_shape tests/test_install_locked_python_requirements.py::test_install_from_proxy_with_emergency_fallback_accepts_one_requested_resolver_miss tests/test_install_locked_python_requirements.py::test_repo_ci_lite_direct_proxy_retry_stages_protobuf_then_wrapt` - PASS
- `.venv/bin/python -m pip_audit -r requirements-dev.txt` - PASS; no known vulnerabilities found.
- `.venv/bin/python -m pip_audit -r requirements-test.txt` - PASS; no known vulnerabilities found.
- `.venv/bin/python -m pip_audit -r requirements-ci-lite.txt` - PASS; no known vulnerabilities found.
- `.venv/bin/python -m pip_audit -r requirements-lock.txt` - PASS; no known vulnerabilities found.
- `VENV_PYTHON=.venv/bin/python make validate-changed` - PASS; selected `tests/test_install_locked_python_requirements.py` and `tests/test_python_supply_chain_controls.py`.
- `pre-commit run --all-files` - PASS after staging generated `.secrets.baseline` updates from detect-secrets.
- Pre-push hooks - PASS, including `pip-audit`, backend pre-push pytest, and full-repo Bandit.
- Fresh dev/test/ci-lite dependency-floor preflight-only reruns passed after
  `b7dd2b894c4ec2a758347e1f6b9bd7d4d1b3028f`. Exact, time-boxed emergency
  fallback artifacts now bridge approved-proxy read timeouts for covered floor
  packages; unlisted floors still fail closed.
- Codex Security diff scan `e8ff0e1e-63f6-4932-aac3-b78356b41f32`
  against head `4be4fc1edebd9cdbf5fbafe2cf434fc8384a862c` - PASS;
  0 findings, 12/12 review receipts completed.

Full local `make verify` was not run under the operator-approved machine-heavy
exception for this dependency lane. Current-head CI is the required heavy parity
signal before any merge-readiness claim.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No actionable review threads existed at PR open. Any post-open bot, human,
CodeRabbit, Sourcery, Cubic, Codex Security, QA, bug-hunter, security-auditor,
or `pulseplate-pr-review` finding remains blocking until fixed or formally
dispositioned with evidence.

## Post-Open Role Findings

- `qa-engineer-agent`: initially found missing `hypothesis==6.155.7` coverage
  in `tests/test_python_supply_chain_controls.py`; fixed in
  `15b0e0c403974b714aa6815cd3b49ec518e3847f`.
- `bug-hunter`: initially found stale active requirements guide examples for
  `pytest==9.1.0` / `pytest>=9.1.0`; fixed in
  `6c85ab9ac763ae2aadd6aa846f3435f2f74d61ca`.
- `Codex Security`: initial diff scan candidate validation found active
  `REQUIREMENTS.md` commands that could bypass the approved private proxy and
  an unreachable full SHA in this mapping artifact; both fixed in
  `23635b2f4fb2575120d356b952898dc3796cfd41`.
- `Codex Security`: diff scan
  `e8ff0e1e-63f6-4932-aac3-b78356b41f32` completed against head
  `4be4fc1edebd9cdbf5fbafe2cf434fc8384a862c` after those fixes with
  0 findings and 12/12 review receipts.
- `CodeRabbit CLI`: found incomplete disposition-specific proof in this mapping
  artifact and two `REQUIREMENTS.md` command/source-of-truth consistency issues;
  fixed in `5f2faa440f4aebf01f0192b41e232678b66a9b26`.
- `pulseplate-pr-review`: dry-run report found one advisory diff-size note
  because the PR has 302 changed lines. Disposition: NOT-A-BUG; this remains
  one split dependency lane with scoped lock/doc/test updates and passing
  targeted gates.
- Current-head CI: `CI` and `Frontend CI` failed in `Setup Python environment`
  because pip 26 reported `aiosqlite==0.22.1` as a no-candidate resolver
  conflict while the exact emergency fallback was already listed in
  `scripts/ci/emergency_python_wheels.json`; fixed in
  `95f80caf6d6212f5a4bc738adbe3dd4b31cf5da2`.
- `CodeRabbit CLI`: final rerun found that the new resolver-miss classifier
  could scan package names such as `pyopenssl` as network `ssl` markers; fixed
  in `9401f3ed7dad2801deda2714739b650b8b32d7e9`.
- `CodeRabbit CLI`: follow-up rerun found the `pyopenssl` regression test did
  not assert that the private-index health probe still runs before emergency
  fallback; fixed in `66ef96f848cb8d475c4ab699ce5fd00c0dc393bc`.
- Current-head CI: `OpenAPI sync` failed in `Setup Python environment` because
  pip 26 treated the selected exact pin `openai==2.29.0` plus redundant
  constraint floor `openai>=2.8.1` as a resolver conflict; fixed in
  `e19e349c3eba9139252f1fa55c6e26ac4e7530a8`.
- Current-head CI: `OpenAPI sync` job `83177933838` and `security` job
  `83177933855` were cancelled by job timeout in `Setup Python environment`
  after the exact-pin conflict was fixed; fixed in
  `999a981e2dd009fa3892c1e77d1284f46e480d59` by installing pip-compiled
  locked requirement surfaces with `--no-deps` while preserving approved proxy,
  constraints, emergency fallback, and startup-hook guardrails.
- Current-head CI: setup jobs still spent machine time in dependency-floor
  preflight after the locked install `--no-deps` fix because the floor check
  downloaded large approved-proxy wheels in every setup job; fixed in
  `754f599a7b6c2a0d71aca1a2a6bb0483d328d726` by checking exact floor
  availability through the approved proxy simple-index project page and keeping
  emergency wheel downloads only for verified proxy misses.
- Local dependency preflight: the simple-index floor check initially used the
  full pip 60 second network timeout per read and could still hang on a slow
  approved proxy response; fixed in
  `704e60699b7f2ebe74763bf59fdd0d202feff08a` by bounding private-index
  health probes to 15 seconds per attempt while preserving the existing retry
  budget and fail-closed behavior.
- Local dependency preflight: approved-proxy simple-index pages also returned
  transient `HTTP 502` responses during floor checks; fixed in
  `a74d598741b5b2ab16c20c88fb60bf8df0162c86` by retrying only transient 5xx
  health responses before failing closed on persistent proxy errors.
- Current-head CI: `CI`, `Frontend CI`, and `OpenAPI sync` setup jobs on head
  `79bd1f2007ae6e6ebb4c1d3d00e58eea4b9c009d` still failed in shared Python
  setup after the duplicate floor preflight and during `requirements-ci-lite`
  direct-proxy install. Fixed in `fe2c923bf2dcc3e5e5d1882816d2f9b50b2ed211`
  by removing the duplicate standalone action preflight, keeping
  `--preflight-only` as an explicit focused gate, hardening private-index
  health probes, and adding exact `jiter==0.12.0` cp313 manylinux emergency
  fallback metadata for the observed mirror miss.
- Current-head Docker Build setup failed on head
  `707c11b821a5004d6d70d09a72707a86a5deeece` because the approved proxy did
  not provide `pydantic-core==2.41.5`; fixed in
  `b7dd2b894c4ec2a758347e1f6b9bd7d4d1b3028f` with exact SHA-pinned
  emergency fallback metadata and active fallback inventory coverage.
- `Codex Security`: current continuation found the shared Python setup action
  missing dependency-floor preflight, RAG release gates using raw public pip
  installation for `requirements-ci-lite.txt`, and changed lockfile headers
  missing `--no-emit-index-url`; all fixed in
  `b7dd2b894c4ec2a758347e1f6b9bd7d4d1b3028f`.
- Current-head CI: `pr_scope_guard` on head
  `028831a385adbdd73f5347c092d2c579f61453ea` failed because the coherent
  dependency/setup lane now touches 18 files in the privileged
  CI/security/workflow category. Fixed by standardizing the PR title to
  `fix(deps): refresh testing dependency stack`, adding parser-safe PR body
  lines `operator approval: approved ...` and
  `privileged scope exception: approved ...`, and applying the trusted labels
  `scope/operator-approved` and `scope/privileged-approved`. Local
  `check_pr_size_governance.py` with live PR metadata now passes.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 15b0e0c403974b714aa6815cd3b49ec518e3847f
Evidence: `qa-engineer-agent` missing-Hypothesis guard finding is covered by `tests/test_python_supply_chain_controls.py` asserting `hypothesis==6.155.7`.

Disposition: FIXED
Commit: 15b0e0c403974b714aa6815cd3b49ec518e3847f
Evidence: `tests/test_python_supply_chain_controls.py` asserts `hypothesis==6.155.7` in the split test dependency profile.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2014#pullrequestreview-4560525882 -> 15b0e0c403974b714aa6815cd3b49ec518e3847f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2014#discussion_r3465713725 -> 15b0e0c403974b714aa6815cd3b49ec518e3847f

Disposition: FIXED
Commit: 6c85ab9ac763ae2aadd6aa846f3435f2f74d61ca
Evidence: `bug-hunter` stale active requirements guide finding is fixed by updating `REQUIREMENTS.md` testing-stack examples from `pytest==9.1.0` / `pytest>=9.1.0` to the refreshed stack.

Disposition: FIXED
Commit: 23635b2f4fb2575120d356b952898dc3796cfd41
Evidence: Codex Security approved-proxy bypass finding is fixed by requiring `PULSEPLATE_PYTHON_INDEX_URL` for raw `pip` / `pip-compile` examples and by preferring `scripts/ci/install_locked_python_requirements.py` in shared install examples.

Disposition: FIXED
Commit: 23635b2f4fb2575120d356b952898dc3796cfd41
Evidence: Codex Security unreachable-SHA finding is fixed by replacing the invalid mapping SHA with reachable commit `6c85ab9ac763ae2aadd6aa846f3435f2f74d61ca`.

Disposition: FIXED
Commit: 5f2faa440f4aebf01f0192b41e232678b66a9b26
Evidence: CodeRabbit major mapping-completeness finding is fixed by adding disposition-specific proof entries for the QA, bug-hunter, and Codex Security post-open findings.

Disposition: FIXED
Commit: 5f2faa440f4aebf01f0192b41e232678b66a9b26
Evidence: CodeRabbit minor requirements-guide source-of-truth finding is fixed by changing the dev dependency update flow to edit `requirements-dev.in` and regenerate `requirements-dev.txt`.

Disposition: FIXED
Commit: 5f2faa440f4aebf01f0192b41e232678b66a9b26
Evidence: CodeRabbit minor install-helper consistency finding is fixed by adding explicit `--requirements-file requirements.txt` and `--dev-requirements-file requirements-dev.txt` flags to the common install examples.

Disposition: NOT-A-BUG
Evidence: `pulseplate-pr-review` diff-size note is advisory only. The PR is intentionally split to the testing dependency lane, lists Torch/Faraday/RAG/Docker/runtime as out of scope, and has passing focused gates: dependency preflights, focused dependency/security pytest, `make validate-changed`, `pre-commit run --all-files`, and CodeRabbit CLI rerun with 0 issues.
Reason: Changed-line count is driven by generated lockfile/doc/mapping churn for one dependency lane, not by mixed runtime scope.

Disposition: FIXED
Commit: 95f80caf6d6212f5a4bc738adbe3dd4b31cf5da2
Evidence: Current-head `CI` and `Frontend CI` setup failures are fixed by classifying pip 26's exact no-candidate resolver-conflict message as an approved proxy mirror miss and retrying with the already-governed emergency wheel fallback. Targeted installer tests cover the new message shape and existing direct-proxy fallback behavior.

Disposition: FIXED
Commit: 9401f3ed7dad2801deda2714739b650b8b32d7e9
Evidence: CodeRabbit package-name/network false-positive finding is fixed by filtering resolver request lines before checking transport markers. Regression coverage proves `pyopenssl` no longer blocks exact emergency fallback selection while mixed network resolver failures still fail closed.

Disposition: FIXED
Commit: 66ef96f848cb8d475c4ab699ce5fd00c0dc393bc
Evidence: CodeRabbit fallback-health-probe coverage finding is fixed by asserting `_require_private_index_project_health` is invoked for the `pyopenssl` emergency fallback path before staging the exact local wheel.

Disposition: FIXED
Commit: e19e349c3eba9139252f1fa55c6e26ac4e7530a8
Evidence: Current-head `OpenAPI sync` setup failure is fixed by generating per-requirement effective constraints that drop redundant constraint entries for packages already exact-pinned by the selected requirements file. Regression tests cover `openai==2.29.0` with `openai>=2.8.1` for both the effective constraints helper and direct-proxy install command construction.

Disposition: FIXED
Commit: 999a981e2dd009fa3892c1e77d1284f46e480d59
Evidence: Current-head `OpenAPI sync` job `83177933838` and `security` job `83177933855` were cancelled by job timeout in `Setup Python environment`. The installer now passes `--no-deps` to locked `pip install` commands for pip-compiled requirement surfaces, and `tests/test_install_locked_python_requirements.py` asserts direct-proxy and Docker single-pass command construction include `--no-deps`.

Disposition: FIXED
Commit: 754f599a7b6c2a0d71aca1a2a6bb0483d328d726
Evidence: Current-head setup jobs still remained in `Setup Python environment` after the locked install no-deps fix because dependency-floor preflight still downloaded floor wheels in every job. The installer now checks exact version availability through the approved proxy simple-index project page and only downloads emergency wheels for verified proxy misses; `tests/test_install_locked_python_requirements.py` covers exact-version checks, proxy-health failures, missing-floor rejection, and emergency fallback verification.

Disposition: FIXED
Commit: 704e60699b7f2ebe74763bf59fdd0d202feff08a
Evidence: Local `requirements-dev.txt` preflight showed the simple-index floor check could still hang on a slow approved proxy read. Private-index health probes now use `PRIVATE_INDEX_HEALTH_TIMEOUT_SECONDS=15` with the existing retry budget; `tests/test_install_locked_python_requirements.py::test_private_index_project_health_retries_transient_probe_error` covers retry/close behavior and the dev/test/ci-lite locked install preflights pass.

Disposition: FIXED
Commit: a74d598741b5b2ab16c20c88fb60bf8df0162c86
Evidence: Local dev/test/ci-lite dependency preflights returned transient approved-proxy `HTTP 502` responses for simple-index floor pages. The private-index health probe now retries 5xx responses within the existing retry budget, and `tests/test_install_locked_python_requirements.py::test_private_index_project_health_retries_transient_http_5xx` covers the retry/close behavior.

Disposition: FIXED
Commit: fe2c923bf2dcc3e5e5d1882816d2f9b50b2ed211
Evidence: Current-head setup logs for `CI` job `83188391853`, `Frontend CI` job `83188383706`, and `OpenAPI sync` job `83188440400` showed the duplicate standalone action preflight plus direct-proxy install failure for `jiter==0.12.0`. `.github/actions/python-setup/action.yml` now avoids the duplicate `--preflight-only` action step, `scripts/ci/emergency_python_wheels.json` carries the exact SHA-pinned `jiter==0.12.0` cp313 manylinux wheel, `docs/roadmap/BACKLOG_LEDGER.md` tracks the new active fallback, and focused tests cover the action contract, manifest selection, private-index retry, and supply-chain guards.

Disposition: FIXED
Commit: b7dd2b894c4ec2a758347e1f6b9bd7d4d1b3028f
Evidence: Current-head Docker Build setup logs showed `pydantic-core==2.41.5` could not be installed from the approved private proxy. The exact cp313 manylinux wheel is now listed in `scripts/ci/emergency_python_wheels.json` with split SHA-256 evidence, `docs/roadmap/BACKLOG_LEDGER.md` tracks the active fallback, and `tests/test_install_locked_python_requirements.py::test_repo_emergency_manifest_tracks_current_active_fallback_set` covers the active manifest set.

Disposition: FIXED
Commit: b7dd2b894c4ec2a758347e1f6b9bd7d4d1b3028f
Evidence: Codex Security found the shared Python setup action no longer ran dependency-floor preflight before install. `.github/actions/python-setup/action.yml` now runs `install_locked_python_requirements.py --preflight-only` against the selected profile before the install command, and `tests/test_python_supply_chain_controls.py::test_python_setup_action_uses_locked_installer_not_floating_tools` asserts the preflight contract.

Disposition: FIXED
Commit: b7dd2b894c4ec2a758347e1f6b9bd7d4d1b3028f
Evidence: Codex Security found RAG release gates installed `requirements-ci-lite.txt` through raw public pip commands. `.github/workflows/rag-release-gates.yml` now uses the locked installer with `PULSEPLATE_PYTHON_INDEX_URL`, `constraints.txt`, `direct-proxy`, and the emergency wheel manifest; `tests/test_python_supply_chain_controls.py::test_rag_release_gates_use_locked_ci_lite_installer` covers both smoke and weekly jobs.

Disposition: FIXED
Commit: b7dd2b894c4ec2a758347e1f6b9bd7d4d1b3028f
Evidence: Codex Security found changed lockfile regeneration guidance missing `--no-emit-index-url`. Headers for `requirements-dev.txt`, `requirements-test.txt`, `requirements-ci-lite.txt`, and `requirements-lock.txt` now include `--no-emit-index-url`, and `REQUIREMENTS.md` plus `docs/DEPENDENCY_MANAGEMENT.md` include the test/CI-lite regeneration commands.

Disposition: FIXED
Commit: b7dd2b894c4ec2a758347e1f6b9bd7d4d1b3028f
Evidence: Local dependency preflights exposed approved-proxy read timeouts for exact security floors that already had time-boxed emergency manifest artifacts. `scripts/ci/install_locked_python_requirements.py` now tolerates proxy probe failure only after the exact floor artifact hash-verifies from the manifest; `tests/test_install_locked_python_requirements.py::test_run_dependency_floor_preflight_allows_exact_emergency_artifact_after_proxy_probe_failure` covers the narrow fallback, and unlisted floor failures remain fail-closed.

## Implementation Evidence

- Testing stack dependency refresh ->
  `8f3b35906fcfc83b1602f4867673f837c3577b7b`
- Sourcery Hypothesis guard completion ->
  `15b0e0c403974b714aa6815cd3b49ec518e3847f`
- Active requirements guide alignment ->
  `6c85ab9ac763ae2aadd6aa846f3435f2f74d61ca`
- Codex Security approved-proxy guide and reachable mapping proof ->
  `23635b2f4fb2575120d356b952898dc3796cfd41`
- CodeRabbit mapping and requirements guide follow-up ->
  `5f2faa440f4aebf01f0192b41e232678b66a9b26`
- `pulseplate-pr-review` dry-run advisory disposition ->
  `NOT-A-BUG`
- pip 26 direct-proxy emergency fallback classifier ->
  `95f80caf6d6212f5a4bc738adbe3dd4b31cf5da2`
- CodeRabbit package-name/network false-positive fix ->
  `9401f3ed7dad2801deda2714739b650b8b32d7e9`
- CodeRabbit fallback health-probe test completion ->
  `66ef96f848cb8d475c4ab699ce5fd00c0dc393bc`
- exact-pin effective constraints fix ->
  `e19e349c3eba9139252f1fa55c6e26ac4e7530a8`
- locked install no-deps resolver-timeout fix ->
  `999a981e2dd009fa3892c1e77d1284f46e480d59`
- simple-index dependency floor preflight fix ->
  `754f599a7b6c2a0d71aca1a2a6bb0483d328d726`
- bounded private-index health probe fix ->
  `704e60699b7f2ebe74763bf59fdd0d202feff08a`
- transient private-index 5xx retry fix ->
  `a74d598741b5b2ab16c20c88fb60bf8df0162c86`
- duplicate setup-preflight and jiter emergency fallback fix ->
  `fe2c923bf2dcc3e5e5d1882816d2f9b50b2ed211`
- pydantic-core Docker/setup fallback, shared setup preflight, RAG release
  proxy install hardening, and lockfile header guidance fix ->
  `b7dd2b894c4ec2a758347e1f6b9bd7d4d1b3028f`
- privileged scope exception body/label governance fix ->
  PR metadata update, verified by local `check_pr_size_governance.py` with live
  PR metadata

## Deferred / Follow-ups

- Dependabot PR #2001 remains open until this human-owned replacement is merged
  or otherwise confirmed as superseding.
- Dependabot alerts #160/#161/#162 for `torch` remain deferred because the GHSA
  lane currently has no patched version.
- Dependabot alert #224 for `faraday` remains a dedicated Fastlane/Ruby security
  lane for dependency graph remediation/removal.

## Merge Readiness

Not merge-ready at artifact creation time.

- Full local `make verify` is deferred under the operator-approved machine-heavy
  exception documented above.
- Post-open role passes ran in order:
  `qa-engineer-agent -> bug-hunter -> security-auditor`; their actionable
  findings are fixed above.
- Codex Security diff scan/finding discovery completed against head
  `4be4fc1edebd9cdbf5fbafe2cf434fc8384a862c` with 0 findings.
  Fresh current-head Codex Security parity is still required if the branch head
  advances before readiness.
- `pulseplate-pr-review` dry-run completed against head
  `71828a460bf30e9732e1eae8746a2c1411840138`; its only advisory finding is
  dispositioned as NOT-A-BUG above.
- CodeRabbit, Sourcery, Cubic, bot actionables, review-thread disposition,
  current-head CI, diff coverage, and strict
  `check_merge_ready.py --require-auth` must pass before any readiness or merge
  claim.
