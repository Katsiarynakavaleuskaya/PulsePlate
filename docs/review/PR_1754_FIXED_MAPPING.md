# PR #1754 Fixed Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1754
- Branch: `codex/fix-gha-node24-artifact-script-cleanup`
- Implementation commits: `459038d99bb4a0ed4a3a9d255859e8ea215d367e`,
  `3b79f7669c857f42cd53853121f966409ed0bc1e`
- Governance artifact commits include: `f1e652604`, `0cf7965e6`,
  `e7ae5b552`, `c5fff3903`
- Backlog anchor: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-gha-node24-cache-warning-cleanup`

## Goal

Remove the remaining GitHub Actions Node 20 deprecation warnings for
`actions/download-artifact` and `actions/github-script` while preserving
existing artifact, permission, and workflow topology contracts.

## Business Reason

Keep CI annotations actionable and avoid future GitHub runner runtime churn
without widening this narrow tooling PR into cache cleanup, SQLite/SQLAlchemy
warning cleanup, runtime code, or CI topology rewrites.

## Scope

- Update `actions/download-artifact` to `v8.0.1` full commit SHA
  `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c`.
- Update `actions/github-script` to `v9.0.0` peeled commit SHA
  `3a2844b7e9c422d3c10d287c895573f7108da1b3`.
- Update `codecov/codecov-action` to `v6.0.0` full commit SHA
  `57e3a136b779b570ffcdbf80b3bdc90e7fab3de2` because `v5.5.1`
  transitively pulled old `actions/github-script@60a0...` and kept the
  Node 20 annotation alive.
- Add workflow contract tests for Node 24-compatible pins, comments, preserved
  artifact names/paths/merge behavior, preserved PR automation permissions, and
  preserved `dorny/paths-filter` and Codecov upload pins.

## Out of Scope

- No GitHub Actions cache topology rewrite.
- No SQLite/SQLAlchemy warning fix.
- No runtime/backend/frontend/iOS behavior changes.
- No package proxy, OpenAPI, deployment, or release-control-plane changes.

## Tests

- `.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_tooling_surface_guards.py`
  - Result after Codecov v6 follow-up: `31 passed`.
- `.venv/bin/python scripts/orchestration/check_preflight.py`
  - Result: PASS.
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py`
  - Result: PASS.
- `.venv/bin/python scripts/ci/guard_actions_pin.py --root .`
  - Result: PASS.
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed`
  - Result after Codecov v6 follow-up: PASS, changed workflow contract test
    `15 passed`.
- `PATH=.venv/bin:$PATH pre-commit run --all-files`
  - Result after Codecov v6 follow-up: PASS.
- Push hooks
  - Result: PASS, including backend tests, `pip-audit`, and full-repo `bandit`.

## Security Notes

- Full SHA pins are preserved.
- `actions/github-script` uses the peeled commit SHA for `v9.0.0`, not the
  annotated tag object SHA.
- `codecov/codecov-action` now uses `v6.0.0` full commit SHA
  `57e3a136b779b570ffcdbf80b3bdc90e7fab3de2`, whose composite action uses
  `actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd`
  (`v8.0.0`, `runs.using: node24`) for OIDC token retrieval.
- `pr-automation.yml` remains limited to `pull-requests: read` and keeps
  `github-token: ${{ secrets.GITHUB_TOKEN }}`.
- Artifact names, paths, `merge-multiple`, and `continue-on-error` behavior are
  regression-guarded unchanged.
- Codex Security diff-scoped scan completed with no surviving reportable
  findings. Local scan bundle:
  `/tmp/codex-security-scans/PulsePlate/ba103c3f_20260515T114752Z`.

## Risks / Rollback

- Risk: action runtime bump changes behavior despite stable workflow inputs.
- Mitigation: regression tests assert exact pins, comments, artifact contracts,
  and PR automation permissions; current-head PR CI remains required.
- Rollback: restore previous action SHAs/comments for `download-artifact`,
  direct `github-script`, and `codecov/codecov-action`.

## Premortem

Frame: 48 hours from now this CI/tooling PR made merge confidence worse.

| Finding | Disposition | Evidence |
| --- | --- | --- |
| Wrong runtime SHA | FIXED | `actions/github-script` plan SHA `d746ffe35508b1917358783b479e04febd2b8f71` was an annotated tag object. Commit `459038d99bb4a0ed4a3a9d255859e8ea215d367e` pins the peeled commit `3a2844b7e9c422d3c10d287c895573f7108da1b3` and rejects the tag-object SHA in tests. |
| Artifact names/paths drift | FIXED | Commit `459038d99bb4a0ed4a3a9d255859e8ea215d367e` adds exact artifact contract assertions for `name`, `pattern`, `path`, `merge-multiple`, and `continue-on-error`. |
| `github-script` permissions drift | FIXED | Commit `459038d99bb4a0ed4a3a9d255859e8ea215d367e` asserts `pull-requests: read`, `github-token`, and the PR read script contract. |
| Node 20 annotation remains | FIXED pending current-head runtime proof | Current-head run `25917162392` showed the warning survived through `codecov/codecov-action@v5.5.1`, which transitively downloaded `actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea`. Commit `3b79f7669c857f42cd53853121f966409ed0bc1e` updates Codecov uploads to `v6.0.0` SHA `57e3a136b779b570ffcdbf80b3bdc90e7fab3de2`, whose transitive `actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd` uses Node 24. Current-head PR CI must still confirm no Node 20 annotation before readiness. |
| Scope expands into cache topology | NOT-A-BUG | Diff has no cache topology changes; cache cleanup remains tracked by `ledger-p2-gha-node24-cache-warning-cleanup`. |
| Readiness before current-head proof | FIXED by governance | PR opened as draft and this mapping keeps merge readiness blocked until current-head CI, review disposition, and strict merge wrapper pass. |

## Codex Security

- Threat model: completed.
- Finding discovery: completed; candidates were wrong SHA type, artifact drift,
  and permission drift.
- Validation: completed; wrong SHA type fixed, artifact/permission drift guarded.
- Attack-path analysis: completed; no surviving reportable finding.
- Final report: no surviving reportable findings.

## Bug-Hunter

Pre-open `bug-hunter` pass found no blocking logical/regression issues. It
confirmed:

- all 9 `actions/download-artifact` occurrences use
  `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c`;
- `actions/github-script` uses the peeled commit
  `3a2844b7e9c422d3c10d287c895573f7108da1b3`;
- no stale old SHA or annotated tag-object SHA remains in scoped repo surfaces.

Follow-up investigation found the remaining Node 20 annotation came from
`codecov/codecov-action@v5.5.1` pulling `actions/github-script@60a0...`;
commit `3b79f7669c857f42cd53853121f966409ed0bc1e` moves those upload steps to
Codecov `v6.0.0`.

Post-open `qa-engineer-agent -> bug-hunter` pass is required before readiness.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Draft PR opened with no review threads at mapping creation time. Any future
CodeRabbit, Sourcery, Cubic, Codex, or human comments are blocking when
actionable and must be dispositioned here before resolution.

## Fixed in Commit Mapping

- No actionable review comments

## Premortem Fixed Evidence Mapping

- Wrong `actions/github-script` tag-object SHA:
  `459038d99bb4a0ed4a3a9d255859e8ea215d367e`
- Artifact contract drift risk:
  `459038d99bb4a0ed4a3a9d255859e8ea215d367e`
- PR automation permission drift risk:
  `459038d99bb4a0ed4a3a9d255859e8ea215d367e`
- `actions/download-artifact` Node 24 pin:
  `459038d99bb4a0ed4a3a9d255859e8ea215d367e`
- `actions/github-script` Node 24 pin:
  `459038d99bb4a0ed4a3a9d255859e8ea215d367e`
- `codecov/codecov-action` Node 24 transitive `github-script` pin:
  `3b79f7669c857f42cd53853121f966409ed0bc1e`

## Merge Readiness

Not ready at mapping creation time.

Required before readiness:

- Current-head PR CI terminal green, especially `CI`, workflow-change attached
  jobs, `lint`, `security`, `test-main`, iOS workflow-coupled jobs, and
  `diff-coverage`.
- Current-head run confirms no Node 20 annotations for `download-artifact`,
  `github-script`, or `dorny/paths-filter`.
- Post-open `qa-engineer-agent -> bug-hunter` pass complete.
- CodeRabbit, Sourcery, Cubic, Codex, and human comments checked and
  dispositioned.
- Strict wrapper passes:
  `GH_TOKEN=$(gh auth token) GITHUB_TOKEN=$(gh auth token) .venv/bin/python scripts/orchestration/check_merge_ready.py --pr-number 1754 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`.
