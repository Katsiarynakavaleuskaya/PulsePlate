# PR #1875 - Fixed in Commit Mapping

**Title:** `chore(ci): migrate Node baseline to 24`
**Branch:** `codex/node24-runtime-baseline`
**Scope:** CI/tooling/runtime baseline migration to Node `24.16.0` plus active
GitHub Actions JavaScript action-runtime cleanup. This PR does not change
backend behavior, OpenAPI/product API contracts, Python dependencies,
private-index policy, release authority, disabled workflow activation, or
operator override behavior.
**Primary implementation commit:** `5eafeacaf1aa8c23f685af3b535b49c2209ec6e4`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Initial post-open snapshot:

- No human or bot review threads were present when this canonical mapping
  artifact was added.
- Mandatory post-open QA, bug-hunter, security, Codex Security, and
  `pulseplate-pr-review` passes remain required before merge readiness.
- Current-head CI remains required before merge readiness.

## Fixed in Commit Mapping

- No actionable review comments

## Dependency Scope / Private-Index Notes

- `requirements*.txt`, `constraints.txt`, `.github/actions/python-setup`, and
  `scripts/ci/install_locked_python_requirements.py` are unchanged.
- Python private-index validation remains explicit:
  `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json`.
- No public-PyPI bypass, ambient `PIP_INDEX_URL` /
  `PIP_EXTRA_INDEX_URL` override, or emergency-wheel widening was introduced.
- No `CI_ALLOW_MERGE_OVERRIDE`, `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24`,
  `ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION`, or docs-only merge bypass was
  introduced.

## Implementation Evidence

Disposition: FIXED
Commit: `5eafeacaf1aa8c23f685af3b535b49c2209ec6e4`
Evidence: `.nvmrc`, `frontend/package.json`, `frontend/package-lock.json`,
`.devcontainer/devcontainer.json`, `frontend/Dockerfile.caddy-spa`,
`frontend/AGENTS.md`, `README_V2_PUBLIC_DRAFT.md`,
`scripts/playwright_mcp.py`, and related tests/docs now use Node `24.16.0` /
Node 24 wording. Active workflow `actions/upload-artifact` refs and
`.github/workflows/actionlint.yml` checkout are normalized to verified Node 24
full commit SHAs.

Disposition: FIXED
Commit: `5eafeacaf1aa8c23f685af3b535b49c2209ec6e4`
Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` adds a Node
baseline coherence guard for `.nvmrc`, frontend engines, lockfile override
truth, devcontainer Node major, and frontend Docker builder. It also adds
positive active-workflow enumeration for every `actions/upload-artifact` use and
rejects old Node20-era checkout/upload SHAs plus insecure override env literals.

Disposition: FIXED
Commit: `5eafeacaf1aa8c23f685af3b535b49c2209ec6e4`
Evidence: Node 24/npm validation surfaced frontend dev transitive audit
findings in `brace-expansion` and `ws`. The PR keeps remediation narrow through
`frontend/package.json` overrides for `minimatch@10` -> `brace-expansion@5.0.6`
and `ws@8.20.1`, with lockfile truth guarded by the Node baseline test.

Disposition: FIXED
Commit: `5eafeacaf1aa8c23f685af3b535b49c2209ec6e4`
Evidence: `docs/ENGINEERING_LESSONS.md` records the recurring stale-SHA cleanup
loop pattern and requires positive workflow reference enumeration when fixing
action-runtime warnings. `docs/roadmap/BACKLOG_LEDGER.md` records PR #1871 plus
this Node 24 runtime-baseline lane without prematurely closing the cache-warning
DoD.

## Role-Agent / Premortem Pass

Pre-open role order completed from packet
`artifacts/orchestration/task_packets/a62ff713bc2f.json`:

- `agent-coordinator` - PASS; scope locked to Node 24 runtime baseline and
  active action-runtime cleanup, excluding backend/OpenAPI/Python/private-index
  and operator override changes.
- `architecture-specialist` - PASS; required one Node baseline source of truth,
  workflow `.nvmrc` usage preservation, devcontainer major 24, Docker builder
  exact Node 24 image, and no disabled workflow activation.
- `frontend-engineer` - PASS; required frontend Node 24 validation and no
  package upgrades unless validation proved them necessary.
- `qa-engineer-agent` - PASS; required frontend coverage/build/smoke/audit plus
  workflow/runtime guard coverage.
- `security-auditor` - PASS; required no permission/secret widening, no insecure
  Node fallback env vars, no Python private-index drift, and full SHA pins.
- `bug-hunter` - PASS; required positive enumeration of active
  `upload-artifact` refs and an engineering lesson for the repeated stale-SHA
  cleanup loop.
- `creative-designer` - PASS; no UI/browser visual design hold because the lane
  touches runtime/docs/CI only.

Premortem:

- Skill: `pulseplate-premortem-risk-review`.
- Frame: 48 hours from now this Node 24 CI/tooling migration made things worse.
- Decision: proceed with narrow changes.
- Closed as FIXED: active workflow stale-SHA miss risk, runtime baseline drift
  risk, audit-remediation scope risk, and Docker/local-machine proof gap.
- Remaining merge-time condition: current-head CI must prove the Docker and
  workflow lanes on GitHub runners before any merge-readiness claim.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-31f9c1047963.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-31f9c1047963.json`
- Result: accepted.
- Mode: `oracle_only_governance_reviewer`.
- Oracles: `python3 scripts/ci/guard_actions_pin.py --root .`;
  `python3 -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_devcontainer_foundation.py tests/test_playwright_mcp.py`;
  `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md README_V2_PUBLIC_DRAFT.md docs/ENGINEERING_LESSONS.md docs/security/CVE-2025-62718-axios.md docs/security/CVE-2026-4926-path-to-regexp-and-CVE-2026-33750-brace-expansion.md docs/security/GHSA-f886-m6hf-6m8v-brace-expansion.md`.
- Evidence: 3/3 immutable oracles passed, 29 source diff paths stayed inside
  packet context, and `shared_tree_untouched=true`.
- Attribution: `coauthor_required=true`; commit
  `5eafeacaf1aa8c23f685af3b535b49c2209ec6e4` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --mode analyze ...` passed.
- `python3 scripts/orchestration/check_agent_consistency.py` passed.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json` passed.
- `node -v` reported `v24.16.0`; `npm -v` reported `11.13.0`.
- `cd frontend && npm ci` passed.
- `cd frontend && npm audit --json` passed with zero vulnerabilities after the
  narrow overrides.
- `cd frontend && npm run build` passed.
- `cd frontend && npm run smoke:css` passed after build output existed.
- `cd frontend && npm run test -- --coverage` passed: 91 files passed, 765
  tests passed, 1 skipped.
- `cd frontend && npm run lint --if-present -- --max-warnings=0` exited 0; no
  lint script is currently present.
- `.venv/bin/python -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_devcontainer_foundation.py tests/test_playwright_mcp.py tests/test_openapi_determinism.py` passed: 52 passed, 1 skipped.
- `python3 scripts/ci/guard_actions_pin.py --root .` passed.
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/roadmap/BACKLOG_LEDGER.md README_V2_PUBLIC_DRAFT.md docs/ENGINEERING_LESSONS.md docs/security/CVE-2025-62718-axios.md docs/security/CVE-2026-4926-path-to-regexp-and-CVE-2026-33750-brace-expansion.md docs/security/GHSA-f886-m6hf-6m8v-brace-expansion.md` passed.
- `PATH=<Node24 bin> make DEV_PYTHON=../../.venv/bin/python openapi` passed
  with no generated API diff.
- `make validate-changed` passed.
- `pre-commit run --all-files` passed after Black's first-run formatting change
  was committed.
- Pre-push hooks passed on push after rerunning with the repo `.venv/bin`
  first in `PATH`: yaml, whitespace, workflow, black, ruff, mypy, pip-audit,
  backend pytest, Bandit full repo, and docker build test.

## Full Verify / Machine-Heavy Disposition

- Full local `make verify` was attempted.
- First result: failed immediately because the worktree had no local `.venv`.
- Second result: after a temporary gitignored `.venv` symlink, `verify-env`
  hung and was terminated.
- Operator direction for this CI/tooling lane is to use PR-scoped local gates,
  `make validate-changed`, and current-head/sharded GitHub CI rather than
  blocking on full local `make verify`.
- No merge-readiness claim is made from local gates alone.

## Current CI / Merge Readiness

- Current-head CI is pending for PR #1875.
- Docker Build and Push, CI, Frontend CI, Actionlint, and governance/security
  checks must pass on the latest pushed head before any merge-readiness claim.
- Strict `check_merge_ready.py --require-auth`, unresolved review-thread
  checks, bot actionable disposition, and the mandatory wait-window remain
  pending.
