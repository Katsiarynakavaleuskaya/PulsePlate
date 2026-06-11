# PR #1920 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1920
Branch: `codex/fix-pr-smoke-workflow-token-exposure`
Title: `fix(ci): avoid persisting devcontainer checkout token`

## Scope

Harden the devcontainer smoke workflow checkout step so PR-controlled
devcontainer build/smoke inputs cannot read persisted checkout credentials from
the runner git config.

In scope:

- `.github/workflows/devcontainer-smoke.yml`
- `tests/test_devcontainer_smoke_workflow.py`
- `docs/review/PR_1920_FIXED_MAPPING.md`

Out of scope:

- unrelated CI workflow consolidation
- devcontainer image/package changes
- application runtime, frontend, iOS, nutrition, or release-surface changes
- PR #1930 or other active lanes

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/eddf928d9b97.json`
- Starter: direct post-open coordinator bootstrap in isolated PR #1920 worktree.
- Preflight: `python3 scripts/orchestration/check_preflight.py --mode analyze --path .github/workflows/devcontainer-smoke.yml --path tests/test_devcontainer_smoke_workflow.py --path docs/review/PR_1920_FIXED_MAPPING.md` PASS.
- Agent consistency: `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- Role dispatch bridge: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/eddf928d9b97.json --pretty --pr-phase post_open_review` PASS.
- Declared role order completed:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> web-research-agent`.

## Implementation Commits

- `a9c3c97a66d93257fc2fc36d0058ee74c1f428af` - `fix(ci): avoid persisting devcontainer checkout token`
- `35e605ca9578936bbed6324ce6d6d70753fa307b` - `test(ci): harden devcontainer checkout guard`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- GitHub GraphQL review-thread check reported `totalCount: 0`.
- Sourcery aggregate review feedback is fixed below.
- CodeRabbit walkthrough/pre-merge comment, Sourcery reviewer guide comment,
  Cubic review, and Codecov coverage comment are non-actionable and
  dispositioned below.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1920#pullrequestreview-4458544061 -> 35e605ca9578936bbed6324ce6d6d70753fa307b
Disposition: FIXED
Commit: 35e605ca9578936bbed6324ce6d6d70753fa307b
Evidence: `tests/test_devcontainer_smoke_workflow.py` now parses workflow YAML with explicit mapping/job/steps assertions, requires at least one `actions/checkout@*` step, and verifies every checkout step sets `with.persist-credentials` to `false`; focused pytest passes with `10 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1920#issuecomment-4659741542
Disposition: NOT-A-BUG
Evidence: CodeRabbit's walkthrough/pre-merge comment reports passed pre-merge checks and contains finishing-touch options only; no required code or governance change is requested.
Reason: Informational bot summary, not an actionable review finding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1920#issuecomment-4659741647
Disposition: NOT-A-BUG
Evidence: Sourcery's reviewer-guide issue comment summarizes the PR diff and reviewer workflow; the actionable Sourcery review is mapped separately to `35e605ca9578936bbed6324ce6d6d70753fa307b`.
Reason: Informational reviewer guide, not a distinct actionable finding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1920#pullrequestreview-4458554784
Disposition: NOT-A-BUG
Evidence: Cubic review states "No issues found" across the two changed files.
Reason: No Cubic-requested code, test, or documentation change exists to fix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1920#issuecomment-4659928178
Disposition: NOT-A-BUG
Evidence: Codecov reports all modified and coverable lines are covered by tests.
Reason: Coverage status comment only; no actionable finding.

## Role-Agent Evidence

- `agent-coordinator`: PASS. Scope locked to the workflow, workflow contract
  test, and mapping artifact; Sourcery review should be FIXED after the test
  contract change.
- `qa-engineer-agent`: PASS after fix plan. Required behavior is explicit
  workflow-structure assertions, at least one checkout step, and every checkout
  step setting `persist-credentials: false`.
- `bug-hunter`: FIXED. Black formatting and brittle exact-one-checkout contract
  were addressed by `35e605ca9578936bbed6324ce6d6d70753fa307b`.
- `security-auditor`: PASS for credential handling. Workflow uses
  `permissions.contents: read`, pinned `actions/checkout`, and
  `persist-credentials: false`; no additional security code edit required.
- `cursor-specialist-agent`: FIXED by completing order 6, adding this canonical
  mapping artifact, and recording post-open governance evidence.
- `web-research-agent`: NOT-A-BUG. External research is not required because the
  PR sets an explicit workflow input on an already pinned action and repo-local
  tests enforce the exact credential-handling declaration.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-9d45f3c08260.json`

- Packet: `artifacts/orchestration/experiments/exp-9d45f3c08260.json`
- Status: accepted.
- Runner mode: `oracle_only_governance_reviewer`.
- Contribution kind: `none`.
- Co-author required: false.
- Shared tree untouched: true.
- Oracle results:
  - `python -m py_compile tests/test_devcontainer_smoke_workflow.py` PASS.
  - `python -m pytest -q tests/test_devcontainer_smoke_workflow.py` PASS.

## Security Notes

- `.github/workflows/devcontainer-smoke.yml` keeps `permissions: contents: read`.
- The checkout step remains pinned to
  `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd`.
- `with.persist-credentials: false` prevents the checkout token from being
  written into local git config before the devcontainer build and smoke run.
- The workflow text still contains no `secrets.`, package proxy, dependency
  bootstrap, `continue-on-error: true`, or `|| true`.

## Local Validation

- `python3 -m py_compile tests/test_devcontainer_smoke_workflow.py` PASS.
- `$ROOT_VENV_PYTHON -m pytest -q tests/test_devcontainer_smoke_workflow.py` PASS: `10 passed`.
- `$ROOT_VENV_PYTHON -m black --check tests/test_devcontainer_smoke_workflow.py` PASS.
- `$ROOT_VENV_PYTHON` resolves to the repo root `.venv/bin/python` for this
  isolated worktree.
- `python3 scripts/orchestration/check_agent_consistency.py --json` PASS.
- `make validate-changed` PASS: selected
  `tests/test_devcontainer_smoke_workflow.py`, `10 passed`.
- `pre-commit run --all-files` PASS after merging `origin/main`.
- Full local `make verify` is operator-deferred for this narrow CI/tooling PR;
  an in-progress run was terminated on operator instruction and is not used as
  readiness evidence. Current-head GitHub CI remains the heavy validation
  signal for merge readiness.

## Merge Readiness

Not claimed. Required before merge:

- Current-head GitHub CI parity after push because full local `make verify` is
  operator-deferred for this machine-heavy CI/tooling lane.
- Codex Security diff scan / finding discovery
- `pulseplate-pr-review` post-open review
- strict review-thread disposition guard with auth
- strict merge-readiness guard with auth
- current-head CI pass after push
- mandatory wait-window after the latest bot/review activity
