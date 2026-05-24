# PR 1802 Fixed in Commit Mapping

## PR

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1802

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/b5504bcb1893.json`
- Preflight: `python3 scripts/orchestration/check_preflight.py` passed.
- Agent consistency: `python3 scripts/orchestration/check_agent_consistency.py` passed.
- Dispatch bridge: `python3 scripts/orchestration/qoder_dispatch_bridge.py --packet artifacts/orchestration/task_packets/b5504bcb1893.json --pretty`
- Required role order: `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> pulseplate-premortem-risk-review -> pulseplate-pr-review -> pulseplate-gates`

## Agent Execution Log

- `agent-coordinator`
  - Disposition: FIXED
  - Evidence: Coordinator locked the expanded #1802 scope and required role order before implementation.
- `architecture-specialist`
  - Disposition: FIXED
  - Evidence: `scripts/orchestration/task_bootstrap.py`, `scripts/orchestration/native_subagent_bridge.py`, and `scripts/orchestration/experiment_runner.py` were updated to preserve transport selection, required role execution, and repo-Python oracle context.
- `security-auditor`
  - Disposition: FIXED
  - Evidence: `ORACLE_BINARY_ALLOWLIST` remains enforced; Python oracle resolution prepends a repo-approved Python directory instead of substituting arbitrary absolute commands.
- `qa-engineer-agent`
  - Disposition: FIXED
  - Evidence: Focused transport, advisory-role, qoder-dispatch, and oracle-env tests passed under repo `.venv`.
- `bug-hunter`
  - Disposition: FIXED
  - Evidence: Requested-role dispatch order and advisory required role passes are covered by `tests/test_qoder_dispatch_bridge.py`.

## Skill Execution Log

- `pulseplate-premortem-risk-review`
  - Disposition: FIXED
  - Evidence: Premortem was run against the actual diff. Blocking findings were addressed by this mapping, PR body expansion, accepted Experiment Runner evidence, and bounded gate reruns.
- `pulseplate-pr-review`
  - Disposition: FIXED
  - Evidence: `python3 scripts/orchestration/pr_review_context.py --pr 1802 --repo Katsiarynakavaleuskaya/PulsePlate --base origin/main --head HEAD --repo-root . --output /tmp/pulseplate_pr1802_review_context_current.json` plus `python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr1802_review_context_current.json --format markdown --packet-id b5504bcb1893 --packet-path artifacts/orchestration/task_packets/b5504bcb1893.json`.
  - Finding: Advisory large-diff-risk note.
  - Disposition reason: The expanded diff is a coherent orchestration-layer fix, bounded to task bootstrap, native bridge, qoder dispatch, Experiment Runner, protocol docs, and tests. FastAPI/Starlette, #1800, #1801, runtime app code, dependency files, OpenAPI, and CI workflow YAML remain out of scope. Targeted deterministic gates passed.
- `pulseplate-gates`
  - Disposition: FIXED
  - Evidence: Bounded local gates passed with repo `.venv` after the host-Python failure was reproduced and rerun correctly.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1802#discussion_r3293225158 -> 983c675555
Disposition: FIXED
Commit: 983c675555
Evidence: `tests/test_task_bootstrap.py` annotates `test_main_passes_native_bridge_transport_flag` fixtures with `pytest.MonkeyPatch` and `pytest.CaptureFixture[str]`.
Reason: CodeRabbit requested complete type hints for the test fixtures.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1802#pullrequestreview-4351193876
Disposition: NOT-A-BUG
Evidence: The sole actionable CodeRabbit review comment is mapped as FIXED in `discussion_r3293225158`.
Reason: Aggregate review record; no separate code finding beyond the mapped discussion thread.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1802#issuecomment-4526058312
Disposition: NOT-A-BUG
Evidence: The prior transport-only summary is superseded by this expanded mapping and the upgraded PR body.
Reason: The comment is an aggregate walkthrough, not a separate actionable code finding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1802#issuecomment-4526073390
Disposition: NOT-A-BUG
Evidence: Codecov reported all modified coverable lines covered on the original diff; expanded local tests cover the new scope.
Reason: No actionable failure was reported.

## Role-Agent Findings

- Finding: Requested agents classified as advisory could be emitted as no-spawn and skipped.
  - Disposition: FIXED
  - Commit: 983c675555
  - Evidence: `scripts/orchestration/native_subagent_bridge.py` emits `execution_mode: advisory_review`, `spawn_with_native_subagent: True`, `advisory_only: False`, and `required_role_pass: True`.
- Finding: Requested reviewers displaced by post-open QA routing could be absent from executable bridge output.
  - Disposition: FIXED
  - Commit: 983c675555
  - Evidence: `scripts/orchestration/task_bootstrap.py` appends missing known requested role passes after secondary partitioning.
- Finding: Dispatch bridge did not preserve the coordinator-required requested role order.
  - Disposition: FIXED
  - Commit: 983c675555
  - Evidence: `scripts/orchestration/qoder_dispatch_bridge.py` preserves requested role order and keeps `qa-engineer-agent -> bug-hunter` as mandatory post-open order.
- Finding: Experiment Runner bare `python` oracle commands could resolve through host Python.
  - Disposition: FIXED
  - Commit: 983c675555, 6aa57c5a37
  - Evidence: `scripts/orchestration/experiment_runner.py` selects repo-approved Python from absolute executable `VENV_PYTHON`, absolute executable `DEV_PYTHON`, or repo `.venv/bin/python`, then prepends its parent directory to sandbox `PATH`.
- Finding: Pre-push mypy hook flagged changed-file type issues not caught by the earlier explicit-package-bases command.
  - Disposition: FIXED
  - Commit: 6aa57c5a37
  - Evidence: `scripts/orchestration/qoder_dispatch_bridge.py` imports optional PyYAML through `importlib.import_module`; `scripts/orchestration/experiment_runner.py` normalizes `REPO_ROOT` through `Path(...)` before resolving repo `.venv`.

## Premortem Risk Fix Matrix

| Risk ID | Failure mode | Fix | Regression test | Evidence command | Disposition |
| --- | --- | --- | --- | --- | --- |
| PM-1802-001 | Kimi transport becomes default. | Default remains `codex-native-subagents`. | Default CLI/build packet emits Codex transport. | `.venv/bin/python -m pytest -q tests/test_task_bootstrap.py -k "native_bridge_transport"` | FIXED |
| PM-1802-002 | Explicit Kimi transport flag is ignored. | CLI flag propagates into packet builder/native bridge. | Explicit Kimi transport observed in packet. | `.venv/bin/python -m pytest -q tests/test_task_bootstrap.py -k "native_bridge_transport"` | FIXED |
| PM-1802-003 | Invalid transport label accepted. | Argparse choices and builder validation restrict allowed transports. | Invalid label fails. | `.venv/bin/python -m pytest -q tests/test_task_bootstrap.py -k "native_bridge_transport"` | FIXED |
| PM-1802-004 | Requested subagents are marked `advisory_no_spawn` and skipped. | Known requested advisory/domain-mismatch agents become required advisory-review role passes. | Advisory requested agent has spawn and required role flags. | `.venv/bin/python -m pytest -q tests/test_native_subagent_bridge.py` | FIXED |
| PM-1802-005 | Unknown agents accidentally become executable. | Unknown agents remain rejected and absent from executable bridge output. | Unknown requested agent remains rejected. | `.venv/bin/python -m pytest -q tests/test_task_bootstrap.py -k "requested_agent"` | FIXED |
| PM-1802-006 | All advisory agents become write-capable. | Advisory-review role passes keep write capability disabled. | Review/advisory roles remain non-write. | `.venv/bin/python -m pytest -q tests/test_native_subagent_bridge.py` | FIXED |
| PM-1802-007 | Experiment Runner oracle uses host Python and misses repo dependencies. | Repo Python bin dir is prepended via `VENV_PYTHON`, `DEV_PYTHON`, or repo `.venv`. | Bare python oracle resolves to controlled repo Python. | `.venv/bin/python -m pytest -q tests/test_experiment_runner.py -k "python or oracle or sandbox or env"` | FIXED |
| PM-1802-008 | Missing repo Python silently falls back to host Python. | Python oracle commands fail closed when no repo Python is available. | Missing repo Python plus python oracle raises infra failure. | `.venv/bin/python -m pytest -q tests/test_experiment_runner.py -k "python or oracle or sandbox or env"` | FIXED |
| PM-1802-009 | Sandbox allowlist bypassed by absolute Python substitution. | Sandbox binary remains bare `python` or `python3`; allowlist still gates execution. | Non-allowlisted binary remains rejected. | `.venv/bin/python -m pytest -q tests/test_experiment_runner.py -k "sandbox or oracle"` | FIXED |
| PM-1802-010 | Env mutation leaks across runner runs. | Temporary sandbox env restores previous env. | PATH/VENV_PYTHON/DEV_PYTHON restoration covered. | `.venv/bin/python -m pytest -q tests/test_experiment_runner.py -k "env"` | FIXED |
| PM-1802-011 | #1802 scope drifts into #1800/#1801/FastAPI/runtime/dependency/CI workflow work. | Changed files are limited to orchestration scripts, tests, protocol docs, and this mapping. | Changed-file scope guard by review. | `git diff --name-only origin/main...HEAD` | FIXED |

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/pr1802-oracle-result-v3.json`
- Packet: `artifacts/orchestration/experiments/pr1802-oracle-packet-v3.json`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Co-author required: `true`
- Trailer used in fix commit: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
- Diagnostic rejected artifact: `artifacts/orchestration/experiments/results/pr1802-oracle-result-v2.json`
  - Failure class: `guard_failure`
  - Raw failure class observed: isolated checkout oracle hit `ModuleNotFoundError: No module named 'fastapi'`.
  - Disposition: NOT-A-BUG for the implementation; this reproduced the repo-Python context problem class and was superseded by accepted source-contract oracle evidence.

## Bounded Local Checks

- `python3 scripts/orchestration/check_preflight.py` -> PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS.
- `.venv/bin/python -m pytest -q tests/test_task_bootstrap.py -k "native_bridge_transport or advisory or requested_agent or pr_phase or displaced_requested_reviewer"` -> 20 passed.
- `.venv/bin/python -m pytest -q tests/test_native_subagent_bridge.py` -> 8 passed.
- `.venv/bin/python -m pytest -q tests/test_experiment_runner.py -k "python or oracle or sandbox or env"` -> 41 passed.
- `.venv/bin/python -m pytest -q tests/test_qoder_dispatch_bridge.py -k "advisory or requested_role_order or no_spawn or coordinator_first or mandatory_post_open"` -> 10 passed.
- `.venv/bin/python -m pytest -q tests/test_task_bootstrap.py tests/test_native_subagent_bridge.py tests/test_experiment_runner.py tests/test_experiment_runner_identity_policy.py tests/test_qoder_dispatch_bridge.py` -> PASS.
- Exact mypy command without package-base normalization failed with duplicate module mapping:
  - `scripts/orchestration/native_subagent_bridge.py: error: Source file found twice under different module names: "native_subagent_bridge" and "scripts.orchestration.native_subagent_bridge"`
- `.venv/bin/python -m mypy --explicit-package-bases --no-incremental --cache-dir=/dev/null scripts/orchestration/task_bootstrap.py scripts/orchestration/native_subagent_bridge.py scripts/orchestration/experiment_runner.py scripts/orchestration/qoder_dispatch_bridge.py tests/test_task_bootstrap.py tests/test_native_subagent_bridge.py tests/test_experiment_runner.py tests/test_qoder_dispatch_bridge.py` -> PASS.
- Initial `make validate-changed` in this worktree failed through host Python:
  - `ModuleNotFoundError: No module named 'fastapi'`
- `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` -> PASS.
- First `pre-commit run --all-files` reformatted Python files with `black`.
- Second `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python pre-commit run --all-files` -> PASS.
- `pulseplate-pr-review` dry-run on current rebased diff -> one advisory large-diff-risk note, dispositioned as NOT-A-BUG for split rationale because all changed files are in the coherent orchestration scope and bounded gates passed.
- Initial pre-push attempt failed in `mypy (type-check, changed files)`:
  - `scripts/orchestration/qoder_dispatch_bridge.py:225: error: Library stubs not installed for "yaml" [import-untyped]`
  - `scripts/orchestration/experiment_runner.py:291: error: Returning Any from function declared to return "Path | None" [no-any-return]`
- `PATH=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin:$PATH VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python pre-commit run mypy --hook-stage pre-push --files scripts/orchestration/qoder_dispatch_bridge.py scripts/orchestration/experiment_runner.py` -> PASS.

## Scope Guard

Changed files are limited to:

- `scripts/orchestration/task_bootstrap.py`
- `scripts/orchestration/native_subagent_bridge.py`
- `scripts/orchestration/experiment_runner.py`
- `scripts/orchestration/qoder_dispatch_bridge.py`
- `tests/test_task_bootstrap.py`
- `tests/test_native_subagent_bridge.py`
- `tests/test_experiment_runner.py`
- `tests/test_qoder_dispatch_bridge.py`
- `docs/orchestration/KIMI_NATIVE_SUBAGENT_BRIDGE_PROTOCOL.md`
- `docs/orchestration/NATIVE_SUBAGENT_BRIDGE_PROTOCOL.md`
- `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
- `docs/review/PR_1802_FIXED_MAPPING.md`

Out of scope and untouched: FastAPI/Starlette fix, #1800 Phase2 evidence semantics, #1801 design validator logic, runtime app code, dependency files, OpenAPI, and CI workflow YAML.

## Merge Readiness

- [ ] Current-head CI is terminal and passing.
- [ ] No unresolved review threads remain.
- [ ] No actionable bot comments remain after current-head review.
- [ ] PR body Phase2 gates pass.
- [ ] Review-thread disposition guard passes with auth.
- [ ] Strict merge-readiness wrapper passes with auth.
- [ ] Mandatory wait-window completed.
- [ ] Operator confirms FastAPI fix is not required inside #1802.

This PR must not be called merge-ready until every item above is satisfied.
