# PR #1946 Fixed in Commit Mapping

## Scope

This PR closes the Docker provenance/private package-index lane by keeping
private Python index inputs out of pushed-image Docker `build-args`, passing
them through BuildKit secret envs, capping BuildKit in-action provenance at
`mode=min`, and preserving `sbom: true` plus GitHub-signed provenance/SBOM
attestation verification. It does not change backend runtime behavior,
OpenAPI/client contracts, database schemas, web, iOS, product AI, billing,
auth, entitlement, or public client behavior.

## Lane Start Provenance

- Packet: artifacts/orchestration/task_packets/51b010298b3f.json
- Earlier inherited packet: artifacts/orchestration/task_packets/a8e92e24ad56.json
- Branch: `codex/fix-docker-provenance-secret-exposure`
- Worktree: `worktrees/pr-1946-docker-provenance`
- Base sync: `git merge --no-edit origin/main` into the existing PR branch;
  refreshed again after `origin/main` advanced to `794011a5e38019f9699e20141c92088e3776db51`
- Latest base-sync merge commit before this evidence update:
  `91eebaf64f905a3db401c98c0cd31c3c0cacf587`
- PR phase: `post_open_review`
- Machine-heavy exception: operator approved not running full local `make verify`;
  narrow local gates plus current-head CI parity are required instead.
- Declared role order:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> dev-operator -> qa-engineer-agent -> bug-hunter -> security-auditor`
- Dispatch manifest:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/51b010298b3f.json --mode runtime --pretty`
- Dispatch result: every declared role pass completed before mapping or thread
  resolution. Post-open Codex Security diff scan / finding discovery and
  `pulseplate-pr-review` also completed before thread resolution or merge
  readiness.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Review threads: one Sourcery thread mapped below.
- Bot reviews/actionables: Codex/CodeRabbit rate-limit notices, Sourcery guide,
  Cubic no-issues review, and Codecov coverage notice are classified below.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1946#pullrequestreview-4479346159 -> 3968118468bd6c226cdc6823f0bce57a398a8be3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1946#discussion_r3398112629 -> 3968118468bd6c226cdc6823f0bce57a398a8be3
Disposition: FIXED
Commit: 3968118468bd6c226cdc6823f0bce57a398a8be3
Evidence: Added `_pushed_docker_steps_with_secret_index_args()` and reused it in both pushed-image Docker tests; removed the redundant `provenance != "mode=max"` assertion; aligned the tests with private index inputs in `secret-envs`, not `build-args`. Focused pytest and `make validate-changed` passed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1946#issuecomment-4683574067
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1946#issuecomment-4683574367
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1946#issuecomment-4683575626
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1946#pullrequestreview-4479380469
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1946#issuecomment-4683756657
Disposition: NOT-A-BUG
Evidence: These are non-actionable automation surfaces: Codex usage limit notice, CodeRabbit rate-limit notice, Sourcery generated reviewer guide, Cubic "No issues found", and Codecov "All modified and coverable lines are covered by tests".
Reason: No code, docs, tests, security, or governance change is requested by these comments beyond the already fixed Sourcery review thread.

## Role-Agent Findings

- Role: `agent-coordinator`
  - Disposition: FIXED
  - Commit: `3968118468bd6c226cdc6823f0bce57a398a8be3`
  - Evidence: Confirmed PR scope is Docker workflow/docs/test governance only,
    then fixed the red focused test contract and added this mapping artifact
    after the real code/docs fix commit.
- Role: `architecture-specialist`
  - Disposition: FIXED
  - Commit: `3968118468bd6c226cdc6823f0bce57a398a8be3`
  - Evidence: Policy/docs now state pushed lanes with private package-index
    secret env inputs use `provenance: mode=min`; tests assert secrets are
    absent from `build-args` and present in `secret-envs`.
- Role: `backend-engineer`
  - Disposition: NOT-A-BUG
  - Evidence: Diff has no backend runtime, OpenAPI, DB, route, generated
    client, frontend, iOS, or public contract changes.
  - Reason: The branch remains a CI/Docker/docs/test governance slice.
- Role: `dev-operator`
  - Disposition: FIXED
  - Commit: `3968118468bd6c226cdc6823f0bce57a398a8be3`
  - Evidence: Docker docs validation command now uses BuildKit
    `--secret id=pp_py_index,env=PULSEPLATE_PYTHON_INDEX_URL` and
    `--secret id=pp_py_host,env=PULSEPLATE_PYTHON_TRUSTED_HOST`.
- Role: `qa-engineer-agent`
  - Disposition: FIXED
  - Commit: `3968118468bd6c226cdc6823f0bce57a398a8be3`
  - Evidence: Focused pytest passed for
    `provenance_enabled_docker_builds_keep_private_index_out_of_build_args`,
    `pushed_docker_builds_do_not_use_max_provenance_with_secret_index_args`,
    and `push_to_registry_workflows_restore_signed_attestations_on_publish_lanes`.
- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `3968118468bd6c226cdc6823f0bce57a398a8be3`
  - Evidence: Active security policy, ADR, backlog DoD, deployment docs, and
    tests now align on the `mode=min` private-index secret-env exception while
    preserving SBOM and signed attestation verification.
- Role: `security-auditor`
  - Disposition: FIXED
  - Commit: `3968118468bd6c226cdc6823f0bce57a398a8be3`
  - Evidence: Private index values remain out of pushed-image `build-args`,
    BuildKit secret env wiring is asserted, `sbom: true` remains asserted, and
    CD attestation verification remains in place.
- Role: `Codex Security`
  - Disposition: NOT-A-BUG
  - Evidence: Current-head diff scan completed at
    `/tmp/codex-security-scans/BMI-App_2025_clean/91eebaf64f90_20260612T123822Z`.
    The scan reviewed 8/8 diff worklist rows, validated `report.md`, rendered
    `report.html`, and emitted zero reportable findings.
  - Reason: No plausible security candidate survived discovery for the current
    Docker provenance/private-index diff.
- Role: `pulseplate-pr-review`
  - Disposition: NOT-A-BUG
  - Evidence: Current-head dry-run report
    `artifacts/agent_runs/pr1946/pr_review_report_current.md` reviewed the
    exact 8-file `origin/main...HEAD` diff and returned no deterministic
    findings.
  - Reason: The report is advisory and side-effect free; it produced no
    actionables to fix or defer.

## Premortem Evidence

- Target mode: `pr-premortem`
- Frame: It is 48 hours from now. This inherited-open Docker provenance closeout
  made things worse. We are looking backward to understand why.
- Most likely failure: policy/docs drift left `mode=max` as canonical truth while
  workflows/tests moved to `mode=min`.
  - Disposition: FIXED
  - Evidence: `docs/security/TOOLING_SURFACE_POLICY.md`,
    `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md`,
    `docs/roadmap/BACKLOG_LEDGER.md`, `docs/deploy/DOCKER.md`, and
    `tests/test_python_supply_chain_controls.py` now align.
- Most dangerous failure: the PR resolves Sourcery's thread and claims readiness
  before current-head CI validates the pushed branch.
  - Disposition: NOT-A-BUG
  - Evidence: This artifact keeps thread resolution and merge readiness gated on
    a fresh push, current-head CI parity, review disposition guard, and strict
    `check_merge_ready.py --require-auth`.
  - Reason: The merge process explicitly requires current-head evidence after
    the local fix is pushed.
- Hidden assumption: moving private index values to BuildKit secret envs alone
  would make every existing provenance policy statement correct.
  - Disposition: FIXED
  - Evidence: The policy/docs update records the explicit `mode=min` exception
    for private package-index secret env lanes.
- Decision: proceed with changes.

## Experiment Runner Evidence

- Artifact: artifacts/orchestration/experiments/results/pr1946_docker_provenance_oracle_v3_result.json
- Status: accepted
- Contribution kind: fixed_mapping_review
- Co-author required: yes, for the governance/mapping commit only.
- Evidence: The current post-merge-head oracle ran preflight, agent
  consistency, and focused pytest in an isolated checkout and returned zero for
  all configured oracle commands.

## Validation

- `python3 scripts/orchestration/check_preflight.py --mode analyze --path .github/workflows/build.yml --path .github/workflows/cd.yml --path docs/deploy/DOCKER.md --path docs/security/TOOLING_SURFACE_POLICY.md --path docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md --path docs/roadmap/BACKLOG_LEDGER.md --path tests/test_python_supply_chain_controls.py --path docs/review/PR_1946_FIXED_MAPPING.md` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `PYTHONDONTWRITEBYTECODE=1 ../../.venv/bin/python -m pytest -q tests/test_python_supply_chain_controls.py -k "provenance_enabled_docker_builds_keep_private_index_out_of_build_args or pushed_docker_builds_do_not_use_max_provenance_with_secret_index_args or push_to_registry_workflows_restore_signed_attestations_on_publish_lanes" -o cache_dir=/tmp/pulseplate-pr1946-pytest-cache` - PASS
- `PYTHONDONTWRITEBYTECODE=1 ../../.venv/bin/python -m py_compile tests/test_python_supply_chain_controls.py scripts/ci/check_docker_provenance_attestation.py` - PASS
- `make validate-changed` - PASS, 47 selected supply-chain tests
- `PRE_COMMIT_HOME=/tmp/pre-commit-pr1946 pre-commit run --all-files` - PASS
- `git diff --check` - PASS
- `python3 scripts/orchestration/pr_review_context.py --pr 1946 --repo Katsiarynakavaleuskaya/PulsePlate --base origin/main --head HEAD --repo-root . --output artifacts/agent_runs/pr1946/pr_review_context_current.json` - PASS
- `python3 scripts/orchestration/pr_review_report.py --context artifacts/agent_runs/pr1946/pr_review_context_current.json --format markdown --packet-path artifacts/orchestration/task_packets/51b010298b3f.json --output artifacts/agent_runs/pr1946/pr_review_report_current.md` - PASS, no deterministic findings
- Codex Security current-head diff scan - PASS, zero reportable findings,
  report: `/tmp/codex-security-scans/BMI-App_2025_clean/91eebaf64f90_20260612T123822Z/report.md`

## Merge Readiness

- Full local `make verify`: not run under the operator-approved machine-heavy
  exception.
- Current-head CI: pending fresh push of this local head.
- Review threads: Sourcery thread must be resolved only after this artifact is
  committed and pushed.
- Required before merge: PR body Phase2 gates, review-thread disposition guard,
  Codex Security diff scan / finding discovery, `pulseplate-pr-review`,
  strict `check_merge_ready.py --require-auth`, current-head CI parity, bot
  disposition pass, and mandatory review-cycle wait window.
