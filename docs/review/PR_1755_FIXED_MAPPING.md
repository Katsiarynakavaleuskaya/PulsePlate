# PR #1755 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1755
- Branch: `codex/walk3-ollama-codex-operator-workflow`
- Base: `main`
- Evidence head at latest mapping update: `8a4d1af0f75425b6647201b9907b5dbfd7b59d15`
- Note: later mapping-only or review-fix commits may advance the branch head; use GitHub PR current-head checks for live merge-readiness truth.

## Scope

Walk3: add operator-only Ollama-Codex workflow support through repo docs, a host-only Codex config template, and a read-only doctor script. This PR does not change PulsePlate backend runtime, MCP behavior, product LLM contracts, OpenAPI, or provider code.

## Discussion Thread Pass

- [x] Initial discussion-thread pass completed at PR open.
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Fixed in commit mapping created after PR open.
- [x] No human, CodeRabbit, Sourcery, or Cubic actionable comments were present when this mapping was created.
- [ ] Re-run discussion-thread pass after each new review cycle before merge readiness.

## Coordinator / Premortem / Agent Findings

- Coordinator scope lock: FIXED by `064cb8f0fca606178e58868d424d5213ea2b653d`
  - Evidence: `docs/templates/codex.config.example.toml`, `docs/dev/CODEX_SKILLS.md`, `scripts/orchestration/check_codex_ollama_operator.py`, and `tests/test_codex_ollama_operator_doctor.py` are the implementation surface.
  - Evidence: no changes were made to `llm.py`, `providers/ollama.py`, `mcp_pulseplate_server.py`, OpenAPI, backend routes, or product runtime contracts.
- Premortem finding 1: FIXED by `064cb8f0fca606178e58868d424d5213ea2b653d`
  - Finding: operator tooling could accidentally write host config such as `~/.codex/config.toml`.
  - Evidence: `scripts/orchestration/check_codex_ollama_operator.py` is diagnostic-only and reports `host_config_write_guard` without reading or writing host config.
  - Evidence: `tests/test_codex_ollama_operator_doctor.py` asserts JSON output includes the host-write guard.
- Premortem finding 2: FIXED by `064cb8f0fca606178e58868d424d5213ea2b653d`
  - Finding: stale guidance for `ollama launch codex-app` could keep failing.
  - Evidence: `b22efdab36355f5f068e63a8598d7a37f76d5673` corrects this to split Codex App and Codex CLI paths: `ollama launch codex-app` requires Ollama v0.24+, while `ollama launch codex` / `codex --oss` / profile setup remain CLI paths.
  - Evidence: the doctor now reports the Codex CLI and Codex App version gates separately.
- Premortem finding 3: FIXED by `064cb8f0fca606178e58868d424d5213ea2b653d`
  - Finding: host Codex/Ollama workflow could be confused with PulsePlate runtime `LLM_PROVIDER=ollama`.
  - Evidence: `docs/dev/CODEX_SKILLS.md` separates host operator setup from runtime `LLM_PROVIDER=ollama` / `OLLAMA_ENDPOINT=http://localhost:11434`.
  - Evidence: `docs/review/WALK3_OLLAMA_CODEX_OPERATOR_PREMORTEM.md` records MCP/backend integration as out of V1.
- Premortem finding 4: FIXED by `064cb8f0fca606178e58868d424d5213ea2b653d`
  - Finding: doctor tests could depend on local tools or real network state.
  - Evidence: `tests/test_codex_ollama_operator_doctor.py` uses fakes/mocks for binaries and HTTP probes.
- Premortem finding 5: NOT-A-BUG
  - Evidence: V1 has no MCP/backend provider runtime changes; the changed files are docs, template, doctor script, tests, and review artifact only.
  - Reason: MCP/Ollama server integration is explicitly out of scope for this PR and requires a separate contract-bearing lane.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1755 -> 064cb8f0fca606178e58868d424d5213ea2b653d
Disposition: FIXED
Commit: 064cb8f0fca606178e58868d424d5213ea2b653d
Evidence: initial implementation commit added the host-only Ollama-Codex template/profile guidance, read-only doctor script, deterministic tests, and premortem closure artifact.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1755#discussion_r3248128051 -> 5c296d7562676b5494c512c25b943886b9d5488d
Disposition: FIXED
Commit: 5c296d7562676b5494c512c25b943886b9d5488d
Evidence: `_run_version(...)` now catches `subprocess.TimeoutExpired` and returns exit code `124` with a diagnostic message; `tests/test_codex_ollama_operator_doctor.py` covers the timeout path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1755#discussion_r3248130605 -> 5c296d7562676b5494c512c25b943886b9d5488d
Disposition: FIXED
Commit: 5c296d7562676b5494c512c25b943886b9d5488d
Evidence: `_run_version(...)` now returns a structured timeout failure instead of raising a traceback; focused doctor tests pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1755#discussion_r3248128038 -> 5c296d7562676b5494c512c25b943886b9d5488d
Disposition: FIXED
Commit: 5c296d7562676b5494c512c25b943886b9d5488d
Evidence: `--timeout` now uses `_positive_timeout(...)`, which rejects non-positive values during argument parsing; `tests/test_codex_ollama_operator_doctor.py` covers this parser failure.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1755#discussion_r3248131779 -> 5c296d7562676b5494c512c25b943886b9d5488d
Disposition: FIXED
Commit: 5c296d7562676b5494c512c25b943886b9d5488d
Evidence: `--timeout` validation fails fast before the network probe and focused tests pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1755#discussion_r3248130616 -> b22efdab36355f5f068e63a8598d7a37f76d5673
Disposition: FIXED
Commit: b22efdab36355f5f068e63a8598d7a37f76d5673
Evidence: `/v1` provider URLs are normalized back to the Ollama root before probing `/api/version`; `tests/test_codex_ollama_operator_doctor.py` asserts `http://127.0.0.1:11434/v1` probes `http://127.0.0.1:11434/api/version`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1755#discussion_r3248130620 -> b22efdab36355f5f068e63a8598d7a37f76d5673
Disposition: FIXED
Commit: b22efdab36355f5f068e63a8598d7a37f76d5673
Evidence: `_parse_ollama_binary_version(...)` now prefers explicit client-version output before server-version output; `tests/test_codex_ollama_operator_doctor.py` covers mixed server/client output.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1755#discussion_r3248131771 -> b22efdab36355f5f068e63a8598d7a37f76d5673
Disposition: FIXED
Commit: b22efdab36355f5f068e63a8598d7a37f76d5673
Evidence: the localhost probe now uses a no-redirect opener and reports redirect HTTP responses as blocked; `tests/test_codex_ollama_operator_doctor.py` covers redirect blocking.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path docs/dev/CODEX_SKILLS.md --path docs/templates/codex.config.example.toml --path scripts/orchestration/check_codex_ollama_operator.py --path tests/test_codex_ollama_operator_doctor.py --path docs/review/PR_1755_FIXED_MAPPING.md` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` OK.
- `../../.venv/bin/python -m pytest -q tests/test_codex_ollama_operator_doctor.py` PASS, 16 tests.
- `../../.venv/bin/python -m py_compile scripts/orchestration/check_codex_ollama_operator.py` PASS.
- `git diff --check` PASS.
- `../../.venv/bin/python -m pytest -q tests/test_repo_policy_guards.py` PASS.
- `../../.venv/bin/python -m pytest -q tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_codex_ollama_operator_doctor.py` PASS, 21 tests.
- `../../.venv/bin/python -m flake8 scripts/orchestration/check_codex_ollama_operator.py tests/test_codex_ollama_operator_doctor.py` PASS.
- `../../.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null scripts/orchestration/check_codex_ollama_operator.py` PASS after typing the no-redirect opener.
- `../../.venv/bin/python -m ruff check scripts/orchestration/check_codex_ollama_operator.py tests/test_codex_ollama_operator_doctor.py` PASS.
- `../../.venv/bin/python -m black --check scripts/orchestration/check_codex_ollama_operator.py tests/test_codex_ollama_operator_doctor.py` PASS.
- `../../.venv/bin/python -m bandit -q -r scripts/orchestration/check_codex_ollama_operator.py` PASS.
- `VENV_PYTHON=../../.venv/bin/python make validate-changed` PASS after post-open fixes.
- `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1755` PASS after parser-safe mapping update.
- `VENV_PYTHON=../../.venv/bin/python pre-commit run --all-files` PASS.
- `VENV_PYTHON=../../.venv/bin/python git push -u origin codex/walk3-ollama-codex-operator-workflow` pre-push hooks PASS.

## Deferred Heavy Gate

- Full local `make verify` is deferred by operator choice for this machine-heavy lane.
- This deferral is not a merge-readiness claim.
- Before merge readiness, current-head CI must provide heavy parity and all review threads/bot comments must be dispositioned.

## Post-Open Review Lane

- [x] `security-auditor`
  - Finding: version-command timeout crashed the doctor instead of returning a diagnostic failure.
  - Disposition: FIXED by `5c296d7562676b5494c512c25b943886b9d5488d`.
- [x] `qa-engineer-agent`
  - Finding: aggregate CLI/text path and template contract were undercovered.
  - Disposition: FIXED by `b22efdab36355f5f068e63a8598d7a37f76d5673`.
- [x] `bug-hunter`
  - Findings: Codex App guidance/version gate was stale and localhost HTTP errors were misclassified.
  - Disposition: FIXED by `b22efdab36355f5f068e63a8598d7a37f76d5673`.
- [x] `pulseplate-pr-review`
  - Findings: parser-safe Phase2 labels were missing, post-open thread disposition was incomplete, redirects could escape localhost validation, `/v1` provider URLs false-failed, and mixed Ollama client/server versions could be parsed incorrectly.
  - Disposition: FIXED through the mapping labels in this artifact and code/docs/tests commits `5c296d7562676b5494c512c25b943886b9d5488d` and `b22efdab36355f5f068e63a8598d7a37f76d5673`.
- [x] Codex Security plugin/local security scan
  - Finding: version-command timeout robustness.
  - Disposition: FIXED by `5c296d7562676b5494c512c25b943886b9d5488d`; no secrets, host config writes, backend/MCP/runtime drift, OpenAPI drift, or non-local probing remained after the redirect fix.
