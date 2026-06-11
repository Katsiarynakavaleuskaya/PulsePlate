# PR #1954 Fixed in Commit Mapping

## Scope

This PR locks the legacy compatibility seam and local artifact validation
boundary with documentation, fail-closed static guards, and deterministic tests.
It does not change runtime behavior, OpenAPI/client contracts,
semantic-cache serving, FoodDB cutover policy, provider/LLM paths, auth,
entitlement, billing, or broad architecture ownership.

## Lane Start Provenance

- Packet: artifacts/orchestration/task_packets/9dfc444f9c68.json
- Starter: scripts/orchestration/start_pr_lane.sh
- Branch: `codex/legacy-seam-artifact-validation-boundary`
- Worktree: `worktrees/legacy-seam-artifact-validation-boundary`
- Base: `origin/main`
- Operator override: lane start was explicitly approved while current-head
  `main` CI was pending. This is a start override only, not a
  merge-readiness override.
- Declared pre-open role order:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> cursor-specialist-agent -> web-research-agent`
- Dispatch manifest:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/9dfc444f9c68.json --mode runtime --implementation-owner qa-engineer-agent --implementation-owner security-auditor --pretty`
- Dispatch result: every declared pre-open role pass completed before
  implementation/push.
- Mandatory post-open role order:
  `qa-engineer-agent -> bug-hunter -> security-auditor`, then Codex Security
  diff scan / finding discovery, then `pulseplate-pr-review`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Review threads: none resolved by this artifact at PR open.
- Bot reviews/actionables: Cubic findings mapped below; current-head
  CodeRabbit/Cubic reruns remain external review signals until they complete.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#pullrequestreview-4480675325 -> bedb6afa40ea27fc9958db020e12321b79d1680f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399233363 -> e351c7202f3e680de2a13458255519b2b57c0661
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399233367 -> bedb6afa40ea27fc9958db020e12321b79d1680f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399233369 -> e351c7202f3e680de2a13458255519b2b57c0661
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#pullrequestreview-4481237491 -> b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399699625 -> b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399699634 -> b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399699635 -> b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399699636 -> b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399699641 -> b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399714388 -> b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399714391 -> b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1954#discussion_r3399714393 -> b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7

Disposition: FIXED
Commit: `e351c7202f3e680de2a13458255519b2b57c0661`
Commit: `bedb6afa40ea27fc9958db020e12321b79d1680f`
Commit: `b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7`
Evidence: Cubic's keyword-only path-argument and empty-doc findings were fixed in `e351c7202`; Cubic's prefix-semantics finding was fixed in `bedb6afa40` by requiring forbidden artifact roots at the path prefix and adding `test_artifact_guard_does_not_match_non_root_artifact_path`.
Evidence: CodeRabbit/Cubic alias findings were fixed in `b4a8e8dc2` by resolving `os.path.join` aliases, `app`/`app.router` aliases, and sensitive local assignment aliases; CodeRabbit capsys typing findings were fixed in the same commit.

## Post-open Role Findings

- Role: `agent-coordinator`
  - Disposition: FIXED
  - Commit: `e351c7202`
  - Evidence: `scripts/ci/check_legacy_growth_guard.py` now freezes existing
    `@app.middleware("http")` facts, rejects new `app.add_middleware(...)` and
    `@app.middleware(...)` growth, preserves current `api_key` baseline, and
    adds `auth` / `api_key` sensitive-family limits. Covered by
    `tests/test_legacy_growth_guard.py`.
- Role: `agent-coordinator`
  - Disposition: FIXED
  - Commit: `e351c7202`
  - Evidence: `scripts/ci/check_artifact_reader_contracts.py` now handles
    keyword-only path arguments for `open(file=...)`, `os.listdir(path=...)`,
    `os.scandir(path=...)`, `glob.glob(pathname=...)`, and
    `glob.iglob(pathname=...)`, and covers these with
    `tests/test_artifact_validation_boundary.py`.
- Role: `agent-coordinator`
  - Disposition: FIXED
  - Commit: `e351c7202`
  - Evidence: `scripts/ci/check_artifact_reader_contracts.py` now rejects
    `os.path.exists(...)`, `os.path.isfile(...)`, `os.path.isdir(...)`, and
    related `os.path` existence checks against forbidden local artifact roots.
    Covered by `tests/test_artifact_validation_boundary.py`.
- Role: `agent-coordinator`
  - Disposition: FIXED
  - Commit: `e351c7202`
  - Evidence: both repo-level validators now run architecture-doc validation
    when the doc file exists even if it is empty, so empty docs fail closed.
    Covered by repo-level empty-doc tests in both focused test files.
- Role: `qa-engineer-agent`
  - Disposition: FIXED
  - Commit: `e351c7202`
  - Evidence: deterministic tests were added for middleware growth, direct
    `add_api_route(...)`, auth/API-key/provider/LLM/entitlement/quota sensitive
    call-family growth, keyword artifact paths, `os.path` existence checks, and
    empty-doc repo validation.
- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `2f3722e89`
  - Evidence: `scripts/ci/check_legacy_growth_guard.py` now records app
    registrations from any call context, rejects sensitive terms on app
    route/router registration calls, and detects normal `import app.routers.*`
    growth. `tests/test_legacy_growth_guard.py` covers assigned
    `add_api_route`, assigned `add_middleware`, assigned `include_router`,
    allowed-route/allowed-router auth dependency growth, current-baseline
    API-key surface growth, and normal router imports.
- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `2f3722e89`
  - Evidence: `scripts/ci/check_artifact_reader_contracts.py` now resolves
    `pathlib.Path(...)`, `from pathlib import Path as P`, and
    `Path(...).joinpath(...)` literal paths before read/enumeration checks.
    `tests/test_artifact_validation_boundary.py` covers all three variants.
- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `1bf3f5712`
  - Evidence: `scripts/ci/check_legacy_growth_guard.py` now blocks
    `app.add_route(...)`, `app.router.add_api_route(...)`, and sensitive
    dependency aliases assigned to neutral variables before use on allowed
    route/router calls. `tests/test_legacy_growth_guard.py` covers these
    bypasses.
- Role: `bug-hunter`
  - Disposition: FIXED
  - Commit: `1bf3f5712`
  - Evidence: `scripts/ci/check_artifact_reader_contracts.py` now joins all
    literal `Path(...)` constructor arguments and detects imported stdlib
    artifact readers, including `from os import listdir`, `from os.path import
    exists`, `from glob import glob`, and `io.open(...)`.
    `tests/test_artifact_validation_boundary.py` covers these bypasses.
- Role: `security-auditor`
  - Disposition: FIXED
  - Commit: `88696ef9a`
  - Evidence: `scripts/ci/check_legacy_growth_guard.py` now blocks
    `app.route(...)`, `app.websocket_route(...)`, `app.add_websocket_route(...)`,
    and provider/LLM behavior introduced through neutral import aliases such as
    `from providers.openai import client` and `from core.llm import model as m`.
    `tests/test_legacy_growth_guard.py` covers these bypasses.
- Role: `security-auditor`
  - Disposition: FIXED
  - Commit: `88696ef9a`
  - Evidence: `scripts/ci/check_artifact_reader_contracts.py` now resolves
    string `+`, f-string, `Path.cwd() / ...`, `Path.cwd().joinpath(...)`,
    `from os import path as osp`, `builtins.open(...)`, and
    `from builtins import open as bopen` artifact-read shapes.
    `tests/test_artifact_validation_boundary.py` covers these bypasses.
- Role: `security-auditor`
  - Disposition: FIXED
  - Commit: `1f434117b`
  - Evidence: `scripts/ci/check_legacy_growth_guard.py` now inspects imported
    symbol names for sensitive aliases, blocking cases such as
    `from core import llm as l; l.model.generate(...)`.
    `tests/test_legacy_growth_guard.py` covers this bypass.
- Role: `Codex Security`
  - Disposition: NOT-A-BUG
  - Evidence: local Codex Security diff scan completed at
    `/tmp/codex-security-scans/PulsePlate/ed89aacbebcb_20260611T230404Z`.
    The scan wrote 7/7 work-ledger receipts, validated and rendered
    `report.md` / `report.html`, and emitted no reportable findings.
- Role: `pulseplate-pr-review`
  - Disposition: NOT-A-BUG
  - Evidence: local dry-run report
    `/tmp/pulseplate_pr_1954_review_report_current.md` flagged only an advisory
    large-diff review-planning note. The scope is the operator-approved narrow
    architecture slice, and the proving gate
    `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed`
    passed with 75 selected tests.
- Role: `cubic-dev-ai[bot]`
  - Disposition: FIXED
  - Commit: `e351c7202` and `bedb6afa40ea27fc9958db020e12321b79d1680f`
  - Evidence: `e351c7202` fixed Cubic's keyword-only artifact path reader
    bypass and empty-doc seam validation bypass. `bedb6afa40` fixed Cubic's
    prefix-semantics finding by requiring forbidden artifact roots at the path
    prefix and adding
    `test_artifact_guard_does_not_match_non_root_artifact_path`.

## Implementation Evidence

- `49dff74637a247cdfdb2930ee6be6ca0c8b80747` - documents the accepted
  legacy compatibility seam and artifact validation boundary, adds
  fail-closed AST guards for `legacy_app.py` growth and runtime local artifact
  reads, and covers both guard contracts with deterministic tests.
- This commit includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because
  the accepted oracle-only Experiment Runner result shaped the commit decision.
- `a2b29adb515ac84a2a8be35bbd38eda4389220c8` - adds the PR #1954 fixed
  mapping artifact with lane provenance and initial validation evidence.
- `e351c7202` - closes post-open coordinator and QA findings by expanding the
  guard surface for middleware/API-route growth, auth/API-key sensitive-family
  growth, keyword artifact path arguments, `os.path` existence checks, and
  empty-doc fail-closed validation.
- `2f3722e89` - closes post-open bug-hunter false-green findings by scanning
  non-expression app registration calls, sensitive app-surface dependency
  terms, normal `import app.routers.*` growth, and `pathlib.Path` alias /
  `joinpath` artifact-read variants.
- `1bf3f5712` - closes the remaining post-open bug-hunter false-green findings
  by scanning `app.add_route`, `app.router.add_api_route`, neutral dependency
  aliases, multi-argument `Path(...)`, imported stdlib artifact readers, and
  `io.open(...)`.
- `88696ef9a` - closes post-open security-auditor bypass findings by scanning
  route decorator aliases, provider/LLM import aliases, dynamic literal
  artifact paths, `os.path` aliases, and `builtins.open(...)`.
- `1f434117b` - closes the remaining post-open security-auditor alias finding
  by detecting sensitive terms in `ImportFrom` imported symbol names, not only
  module paths.
- `ed89aacbe` - fixes the final pre-push changed-file mypy failure in
  `scripts/ci/check_artifact_reader_contracts.py` by removing duplicate local
  variable type redeclarations without changing guard behavior.
- `bedb6afa40ea27fc9958db020e12321b79d1680f` - closes Cubic's remaining
  prefix-semantics finding by matching only repo-root artifact prefixes and
  adding a deterministic non-root path regression test.
- `b4a8e8dc2326a5bd0a097ef93bcf74676aed77a7` - closes current-head
  CodeRabbit/Cubic alias findings by resolving `os.path.join` aliases,
  `app`/`app.router` aliases, and sensitive local assignment aliases, and
  annotates the two `capsys` fixtures requested by CodeRabbit.

## Premortem Evidence

- Skill: `pulseplate-premortem-risk-review`
- Mode: `pr-premortem`
- Artifact: `artifacts/orchestration/premortem/legacy-seam-artifact-validation-boundary-premortem.md`
- Decision: proceed with changes.
- Closure: findings are closed by the current docs, static guards,
  deterministic tests, semantic-cache gate evidence, and the explicit
  pending-main merge-readiness block.
- Closed risks: legacy guard false-green, runtime artifact back door, scope
  drift into runtime/semantic-cache/FoodDB behavior, and confusing a pending
  main start override with merge readiness.

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/exp-ef7d993bc3c7.json

- Mode: `oracle_only_governance_reviewer`
- Packet: `artifacts/orchestration/experiments/exp-ef7d993bc3c7.json`
- Result: `artifacts/orchestration/experiments/results/exp-ef7d993bc3c7.json`
- Status: accepted.
- Evidence: `mutated_paths=[]`, `shared_tree_untouched=true`,
  `source_diff_applied=true`, and 4/4 configured oracles returned `0`.
- Attribution: commit `49dff74637a247cdfdb2930ee6be6ca0c8b80747` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because
  the oracle review shaped validation and the commit decision.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_artifact_validation_boundary.py` - PASS, 24 tests.
- `.venv/bin/python scripts/ci/check_legacy_growth_guard.py` - PASS.
- `.venv/bin/python scripts/ci/check_artifact_reader_contracts.py` - PASS.
- `.venv/bin/python scripts/ci/check_semantic_cache_gate.py` - PASS; all
  semantic-cache contracts remain closed.
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS after rebase; selected
  `tests/test_artifact_validation_boundary.py tests/test_legacy_growth_guard.py`.
- `pre-commit run --all-files` - PASS after rebase.
- Push pre-hook - PASS: mypy changed files, pip-audit, backend pre-push pytest,
  full-repo Bandit, and Docker build test.
- After `e351c7202`: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_artifact_validation_boundary.py` - PASS, 43 tests.
- After `e351c7202`: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py` - PASS.
- After `e351c7202`: `.venv/bin/python scripts/ci/check_artifact_reader_contracts.py` - PASS.
- After `e351c7202`: `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS, 43 tests selected.
- After `e351c7202`: `pre-commit run --all-files` - PASS.
- After `2f3722e89`: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_artifact_validation_boundary.py` - PASS, 53 tests.
- After `2f3722e89`: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py` - PASS.
- After `2f3722e89`: `.venv/bin/python scripts/ci/check_artifact_reader_contracts.py` - PASS.
- After `2f3722e89`: `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS, 53 tests selected.
- After `2f3722e89`: `pre-commit run --all-files` - PASS.
- After `1bf3f5712`: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_artifact_validation_boundary.py` - PASS, 62 tests.
- After `1bf3f5712`: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py` - PASS.
- After `1bf3f5712`: `.venv/bin/python scripts/ci/check_artifact_reader_contracts.py` - PASS.
- After `1bf3f5712`: `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS, 62 tests selected.
- After `1bf3f5712`: `pre-commit run --all-files` - PASS.
- After `88696ef9a`: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_artifact_validation_boundary.py` - PASS, 74 tests.
- After `88696ef9a`: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py` - PASS.
- After `88696ef9a`: `.venv/bin/python scripts/ci/check_artifact_reader_contracts.py` - PASS.
- After `88696ef9a`: `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS, 74 tests selected.
- After `88696ef9a`: `pre-commit run --all-files` - PASS.
- After `1f434117b`: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_artifact_validation_boundary.py` - PASS, 75 tests.
- After `1f434117b`: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py` - PASS.
- After `1f434117b`: `.venv/bin/python scripts/ci/check_artifact_reader_contracts.py` - PASS.
- After `1f434117b`: `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS, 75 tests selected.
- After `1f434117b`: `pre-commit run --all-files` - PASS.
- First push attempt after post-open fixes: pre-push hook FAILED on changed-file
  mypy with `scripts/ci/check_artifact_reader_contracts.py:158` and `:173`
  `Name "parts" already defined`. Root cause fixed in `ed89aacbe`.
- After `ed89aacbe`: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_artifact_validation_boundary.py` - PASS, 75 tests.
- After `ed89aacbe`: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py` - PASS.
- After `ed89aacbe`: `.venv/bin/python scripts/ci/check_artifact_reader_contracts.py` - PASS.
- After `ed89aacbe`: `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS, 75 tests selected.
- After `ed89aacbe`: `pre-commit run --all-files` - PASS.
- After `ed89aacbe`: push pre-hook - PASS: changed-file mypy, pip-audit,
  backend pre-push pytest, full-repo Bandit, and Docker build test.
- After `bedb6afa40`: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_artifact_validation_boundary.py` - PASS, 76 tests.
- After `bedb6afa40`: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py` - PASS.
- After `bedb6afa40`: `.venv/bin/python scripts/ci/check_artifact_reader_contracts.py` - PASS.
- After `bedb6afa40`: `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS, 76 tests selected.
- After `bedb6afa40`: `pre-commit run --all-files` - PASS.
- After `b4a8e8dc2`: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_artifact_validation_boundary.py` - PASS, 83 tests.
- After `b4a8e8dc2`: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py` - PASS.
- After `b4a8e8dc2`: `.venv/bin/python scripts/ci/check_artifact_reader_contracts.py` - PASS.
- After `b4a8e8dc2`: `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS, 83 tests selected.
- After `b4a8e8dc2`: `pre-commit run --all-files` - PASS after Black hook formatting was committed.
- Codex Security diff scan / finding discovery - PASS, no reportable
  findings. Report:
  `/tmp/codex-security-scans/PulsePlate/ed89aacbebcb_20260611T230404Z/report.md`;
  HTML:
  `/tmp/codex-security-scans/PulsePlate/ed89aacbebcb_20260611T230404Z/report.html`;
  work ledger:
  `/tmp/codex-security-scans/PulsePlate/ed89aacbebcb_20260611T230404Z/artifacts/02_discovery/work_ledger.jsonl`.
- `pulseplate-pr-review` local dry-run - PASS with one advisory large-diff
  planning note dispositioned as NOT-A-BUG for this operator-approved narrow
  architecture slice. Report:
  `/tmp/pulseplate_pr_1954_review_report_current.md`.
- `python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q` - PASS, 13 tests.

## Current Main / Merge Readiness

- Current `origin/main` at PR open:
  `1090ae112b87a13448e71961d2ee582c1ef6b23e`.
- Main CI at PR open: `CI` run `27375084223` was still `in_progress`.
- Merge readiness remains blocked until current-head `main` is healthy, this
  PR's current-head CI is healthy, all review/bot actionables are dispositioned,
  this mapping artifact and the PR body mirror are current, strict
  merge-readiness passes, and the wait-window elapses.

## Post-open Role Findings

- `agent-coordinator`: FIXED in `e351c7202`; see Fixed in Commit Mapping.
- `qa-engineer-agent`: FIXED in `e351c7202`; see Fixed in Commit Mapping.
- `bug-hunter`: FIXED in `2f3722e89` and `1bf3f5712`.
- `bug-hunter` rerun: PASS at head `e7af479b99cb23df97f404915523d2818662845e`.
  Evidence: previous false-green classes now return guard errors; focused
  tests passed with 62 tests; both guard CLIs passed; `git diff --check
  origin/main...HEAD` passed.
- `security-auditor`: FIXED in `88696ef9a` and `1f434117b`.
- `security-auditor` rerun: PASS at head `03840c09557f2e7e7531548410f3ae7865e661f2`.
  Evidence: focused tests passed with 75 tests; both guard CLIs passed;
  targeted probes blocked for route aliases, provider/LLM aliases, dynamic
  artifact paths, stdlib aliases, and `from core import llm as l`; no runtime,
  OpenAPI/client, semantic-cache serving, FoodDB, local absolute path, secret,
  suppression, subprocess, `eval`, or `exec` changes found.
- Codex Security diff scan / finding discovery: PASS, no reportable findings.
  Evidence: scan report
  `/tmp/codex-security-scans/PulsePlate/ed89aacbebcb_20260611T230404Z/report.md`;
  7/7 diff files have `work_ledger.jsonl` completion receipts; final report
  validated and rendered to HTML.
- `pulseplate-pr-review`: PASS with advisory note dispositioned.
  Evidence: `/tmp/pulseplate_pr_1954_review_report_current.md`; the only finding
  was a large-diff review-planning note, addressed by the explicit narrow scope
  and passing `make validate-changed` evidence.
- `cubic-dev-ai[bot]`: FIXED in `e351c7202` and `bedb6afa40`; see Cubic Bot
  Review Mapping above.
- Current-head CodeRabbit/Cubic alias and fixture findings: FIXED in
  `b4a8e8dc2`; see Fixed in Commit Mapping above.
