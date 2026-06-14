# PR #1915 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1915>

## Summary

This PR hardens the Experiment Runner Slack live-smoke workflow so live Slack
runtime values are only reachable from the trusted `refs/heads/main` workflow
ref, and it locks that behavior with deterministic workflow tests. It also
records the PulsePlate repo-local skill mirror verification requested for this
lane: `tools/codex_skills/` remains the source of truth, `.agents/skills/`
contains every PulsePlate skill source entry including
`pulseplate-premortem-risk-review`, the managed copied
`pulseplate-pr-review` entry is preserved, and Vercel entries remain untouched.

## Scope

- `.github/workflows/experiment-runner-slack-socket-smoke.yml`
- `tests/test_experiment_slack_socket_bridge.py`
- `docs/review/PR_1915_FIXED_MAPPING.md`
- Verification-only coverage of `.agents/skills/` against `tools/codex_skills/`

## Out of Scope

- No backend API, OpenAPI, web, iOS, product runtime, wellness copy, semantic
  cache, billing, or food-data behavior changes.
- No live Slack dispatch from local validation.
- No `$HOME`, `$AGENTS_HOME`, or `$CODEX_HOME` skill installation.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/e1e7431d37fd.json`
- PR phase: `post_open_review`
- Branch: `codex/fix-slack-secrets-exposure-in-workflow`
- Role dispatch: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/e1e7431d37fd.json --pretty`
- Coordinator-declared role order executed: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist`
- Role-pass summary:
  - `agent-coordinator`: locked scope to Slack live-smoke hardening, workflow
    test coverage, skill mirror proof, and PR governance artifact/body mirror.
  - `qa-engineer-agent`: found missing dynamic scan/order coverage and missing
    mapping artifact; focused mirror/workflow tests passed after the fix.
  - `bug-hunter`: found checkout-before-block ordering, unparenthesized checkout
    expression, detect-secrets wording, dynamic scan gap, and missing mapping.
  - `security-auditor`: found no remaining auth/ref blocker after the workflow
    plan, with mapping artifact still required.
  - `architecture-specialist`: found no product-runtime or mirror-boundary
    architecture blocker; confirmed the mirror is passive and
    `tools/codex_skills/` remains the source of truth.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Notes: three Sourcery threads remain unresolved until the fix commit and this
  artifact are pushed. They are mapped below to the post-comment fix commit.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1915#pullrequestreview-4453459698 -> 5553234dbab4d39118d3b2393c7a93e9fd662bc2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1915#discussion_r3376378172 -> 5553234dbab4d39118d3b2393c7a93e9fd662bc2
Disposition: FIXED
Commit: 5553234dbab4d39118d3b2393c7a93e9fd662bc2
Evidence: `.github/workflows/experiment-runner-slack-socket-smoke.yml` now blocks non-main live-smoke workflow refs before checkout and uses `${{ (inputs.dry_run == 'false' && 'refs/heads/main') || github.ref }}` for the checkout ref; `tests/test_experiment_slack_socket_bridge.py` asserts that exact expression.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1915#discussion_r3376378188 -> 5553234dbab4d39118d3b2393c7a93e9fd662bc2
Disposition: FIXED
Commit: 5553234dbab4d39118d3b2393c7a93e9fd662bc2
Evidence: `tests/test_experiment_slack_socket_bridge.py` now dynamically scans all workflow steps for live Slack secret and allowlist carriers and requires the trusted main-ref condition for each carrier.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1915#discussion_r3376378201 -> 5553234dbab4d39118d3b2393c7a93e9fd662bc2
Disposition: FIXED
Commit: 5553234dbab4d39118d3b2393c7a93e9fd662bc2
Evidence: `tests/test_experiment_slack_socket_bridge.py` now asserts the untrusted-ref block step precedes every dynamically detected live Slack secret or allowlist carrier, and also precedes the live evidence summary step.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1915#issuecomment-4653550870
Disposition: NOT-A-BUG
Evidence: This Codex connector comment reports review usage limits and does not identify a PR-scoped code, security, test, or governance defect.
Reason: No actionable repository change is requested by the comment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1915#issuecomment-4653551229
Disposition: NOT-A-BUG
Evidence: The CodeRabbit comment is a rate-limit/status note rather than a concrete PR finding; no unresolved CodeRabbit review thread or actionable code request is present.
Reason: There is no repository change to make unless a later CodeRabbit pass posts a concrete actionable item.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1915#issuecomment-4653551852
Disposition: NOT-A-BUG
Evidence: The Sourcery issue comment is a generated review guide; the actionable Sourcery findings are the three discussion threads mapped above.
Reason: The guide itself does not require an additional code change beyond the mapped discussion fixes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1915#pullrequestreview-4453475886
Disposition: NOT-A-BUG
Evidence: Cubic posted no actionable review thread for this PR at the checked GitHub pass.
Reason: No repository change is requested by the Cubic review.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1915#issuecomment-4653691285
Disposition: NOT-A-BUG
Evidence: The Codecov report is a coverage status comment. Local focused tests for the changed workflow/test surface passed, and no concrete uncovered line action was reported in the PR comment.
Reason: Coverage status remains current-head CI evidence, not a standalone code-review actionable.

## Premortem Findings

- PM-001 Most likely failure: CI is mechanically fixed but Sourcery concerns
  stay unresolved.
  - Disposition: FIXED
  - Evidence: the three Sourcery discussion URLs are mapped to
    `5553234dbab4d39118d3b2393c7a93e9fd662bc2`, which was committed after the
    2026-06-08 Sourcery comments.
- PM-002 Most dangerous failure: future live Slack secret-bearing steps bypass
  trusted-ref gating.
  - Disposition: FIXED
  - Evidence: `tests/test_experiment_slack_socket_bridge.py` dynamically scans
    all Slack secret/allowlist carrier steps and asserts both trusted-ref gating
    and block-step ordering.
- PM-003 Hidden assumption: repo-local PulsePlate skills are discoverable just
  because source files exist.
  - Disposition: NOT-A-BUG
  - Evidence: `.agents/skills/pulseplate-premortem-risk-review` resolves to
    `tools/codex_skills/pulseplate-premortem-risk-review`, `.agents/skills`
    contains every `tools/codex_skills/pulseplate-*` entry, and
    `tests/test_install_codex_skills.py::test_repo_agents_skills_mirror_points_to_codex_skill_sources`
    plus `tests/guards/test_symlink_integrity.py` passed.
  - Reason: the current PR branch and `origin/main` already contain the complete
    repo-local mirror; this lane records proof rather than adding redundant
    mirror churn.
- PM-004 Suppression risk: detect-secrets is silenced instead of fixed.
  - Disposition: FIXED
  - Evidence: the triggering `secret_exposure` wording was replaced with
    `sensitive_value_exposure`; no allowlist or suppression was added; focused
    `detect-secrets scan` returned zero findings.
- PM-005 Governance risk: mapping is updated before fixes.
  - Disposition: FIXED
  - Evidence: code/test fix commit
    `5553234dbab4d39118d3b2393c7a93e9fd662bc2` was created before this mapping
    artifact.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/pr1915-slack-skill-governance-packet.json`
- Artifact: `artifacts/orchestration/experiments/results/pr1915-slack-skill-governance-result.json`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution: `fixed_mapping_review`
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- `promotion_ready=false`
- `coauthor_required=true`
- Co-author trailer present in commit `5553234dbab4d39118d3b2393c7a93e9fd662bc2`.
- Oracle commands:
  - `python3 -m pytest -q tests/test_experiment_slack_socket_bridge.py::test_smoke_workflow_is_manual_only_and_secret_safe tests/test_install_codex_skills.py::test_repo_agents_skills_mirror_points_to_codex_skill_sources tests/guards/test_symlink_integrity.py::test_all_skill_symlinks_resolve`
  - `python3 -m black --check tests/test_experiment_slack_socket_bridge.py`

## Codex Security Diff Scan

- Scan directory: `/tmp/codex-security-scans/PulsePlate-pr-1915/pr1915_20260612T160837Z`
- Result: no reportable findings.
- Coverage: `artifacts/02_discovery/deep_review_input.csv` contains two
  PR-scoped rows, `.github/workflows/experiment-runner-slack-socket-smoke.yml`
  and `tests/test_experiment_slack_socket_bridge.py`.
- Receipts: `artifacts/02_discovery/work_ledger.jsonl` contains completion
  receipts for both rows.
- Candidates: `artifacts/02_discovery/raw_candidates.jsonl` is zero bytes.
- Reports: `report.md` and `report.html` are present.

## pulseplate-pr-review

- Disposition: NOT-A-BUG
- Evidence: `scripts/orchestration/pr_review_context.py --pr 1915 --output /tmp/pr1915_pr_review_context.json` and `scripts/orchestration/pr_review_report.py --context /tmp/pr1915_pr_review_context.json --format json` completed after this artifact was present; the rendered report contained `findings_count=0`.
- Reason: The repo-local self-review found no additional PR-scoped findings beyond the already-mapped Sourcery fixes and governance evidence.

## Skill Mirror Evidence

- `tools/codex_skills/` PulsePlate sources counted: 17.
- `.agents/skills/` PulsePlate mirror includes all 17 source entries plus the
  separate repo-native `pulseplate-orchestration-dispatch` and
  `pulseplate-security-guardrail` entries.
- `.agents/skills/pulseplate-premortem-risk-review` resolves to
  `../../tools/codex_skills/pulseplate-premortem-risk-review`.
- `.agents/skills/pulseplate-pr-review` remains a managed copied directory with
  `.pulseplate_codex_skill_source` set to
  `tools/codex_skills/pulseplate-pr-review`.
- Vercel skill entries are unchanged.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --path .github/workflows/experiment-runner-slack-socket-smoke.yml --path tests/test_experiment_slack_socket_bridge.py --path docs/review/PR_1915_FIXED_MAPPING.md --path .agents/skills`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/e1e7431d37fd.json --pretty`
- PASS: `.venv/bin/python -m black --check tests/test_experiment_slack_socket_bridge.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_experiment_slack_socket_bridge.py::test_smoke_workflow_is_manual_only_and_secret_safe`
- PASS: `.venv/bin/python -m pytest -q tests/test_install_codex_skills.py::test_repo_agents_skills_mirror_points_to_codex_skill_sources tests/guards/test_symlink_integrity.py::test_all_skill_symlinks_resolve`
- PASS: `.venv/bin/python -m pytest -q tests/test_experiment_slack_socket_bridge.py tests/test_sync_skill_mirror.py tests/test_install_codex_skills.py::test_repo_agents_skills_mirror_points_to_codex_skill_sources tests/guards/test_symlink_integrity.py`
- PASS: `detect-secrets scan .github/workflows/experiment-runner-slack-socket-smoke.yml tests/test_experiment_slack_socket_bridge.py`
- PASS: `scripts/orchestration/pr_review_context.py --pr 1915 --output /tmp/pr1915_pr_review_context.json`
- PASS: `scripts/orchestration/pr_review_report.py --context /tmp/pr1915_pr_review_context.json --format json` (`findings_count=0`)
- PASS: `git diff --check`
- PASS: pre-commit hooks during fix commit with `VENV_PYTHON` exported.
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PENDING: PR body Phase2 gate after PR body mirror update.
- PENDING: strict merge-readiness wrapper after push/current-head CI.

## Machine-Heavy Verify Exception

Full local `make verify` is operator-deferred for this PR because the project
has a machine-heavy test surface. This lane uses the operator-approved bounded
path: startup gates, role passes, focused tests, skill mirror guards,
Experiment Runner oracle-only evidence, Codex Security diff scan,
`make validate-changed`, `pre-commit run --all-files`, PR body/mapping gates,
strict merge-readiness wrapper, and current-head GitHub CI before any
merge-readiness claim.

## Risks / Rollback

- Risk: a future workflow step adds Slack credentials without the trusted-ref
  condition. Rollback/control: the dynamic workflow test fails when any Slack
  secret or allowlist carrier lacks the main-ref gate or appears before the
  untrusted-ref block.
- Risk: non-main manual live dispatch tries to reach secret-bearing steps.
  Rollback/control: the block step exits before checkout and before live
  credential env attachment.
- Rollback: revert commit `5553234dbab4d39118d3b2393c7a93e9fd662bc2` to restore
  the prior workflow/test behavior if this hardening causes CI regressions.

## Deferred / Follow-ups

- None.

## Merge Readiness

Not claimed.

Required before merge:

- Push the fix and mapping commits.
- Update the PR body mirror from this canonical artifact.
- Resolve the three mapped Sourcery threads only after the mapping commit is
  visible on GitHub.
- Run `make validate-changed` and `pre-commit run --all-files`.
- Run PR body Phase2 validation with Experiment Runner evidence required.
- Run strict merge-readiness with auth.
- Confirm current-head required checks pass with no pending required jobs.
- Confirm CodeRabbit, Sourcery, Cubic, Codecov, and Codex connector comments
  have no unresolved actionable items.
- Observe the mandatory wait-window after the latest review/bot activity.
