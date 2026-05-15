# PR #1755 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1755
- Branch: `codex/walk3-ollama-codex-operator-workflow`
- Base: `main`
- Evidence head at mapping creation: `064cb8f0fca606178e58868d424d5213ea2b653d`
- Note: later mapping-only or review-fix commits may advance the branch head; use GitHub PR current-head checks for live merge-readiness truth.

## Scope

Walk3: add operator-only Ollama-Codex workflow support through repo docs, a host-only Codex config template, and a read-only doctor script. This PR does not change PulsePlate backend runtime, MCP behavior, product LLM contracts, OpenAPI, or provider code.

## Discussion Thread Pass

- [x] Initial discussion-thread pass completed at PR open.
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
  - Evidence: `docs/dev/CODEX_SKILLS.md` explains that `codex-app` is not the launched CLI target and points to `ollama launch codex`, `codex --oss`, and `codex --profile ollama-launch`.
  - Evidence: the doctor enforces Ollama `0.15.0+` for `ollama launch` guidance.
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

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path docs/dev/CODEX_SKILLS.md --path docs/templates/codex.config.example.toml --path scripts/orchestration/check_codex_ollama_operator.py --path tests/test_codex_ollama_operator_doctor.py` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` OK.
- `../../.venv/bin/python -m pytest -q tests/test_codex_ollama_operator_doctor.py` PASS, 8 tests.
- `../../.venv/bin/python -m py_compile scripts/orchestration/check_codex_ollama_operator.py` PASS.
- `git diff --check` PASS.
- `../../.venv/bin/python -m pytest -q tests/test_repo_policy_guards.py` PASS.
- `../../.venv/bin/python -m pytest -q tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_codex_ollama_operator_doctor.py` PASS.
- `../../.venv/bin/python -m flake8 scripts/orchestration/check_codex_ollama_operator.py tests/test_codex_ollama_operator_doctor.py` PASS.
- `../../.venv/bin/python -m ruff check scripts/orchestration/check_codex_ollama_operator.py tests/test_codex_ollama_operator_doctor.py` PASS.
- `../../.venv/bin/python -m black --check scripts/orchestration/check_codex_ollama_operator.py tests/test_codex_ollama_operator_doctor.py` PASS.
- `../../.venv/bin/python -m bandit -q -r scripts/orchestration/check_codex_ollama_operator.py` PASS.
- `VENV_PYTHON=../../.venv/bin/python pre-commit run --all-files` PASS.
- `VENV_PYTHON=../../.venv/bin/python make validate-changed` PASS.
- `VENV_PYTHON=../../.venv/bin/python git push -u origin codex/walk3-ollama-codex-operator-workflow` pre-push hooks PASS.

## Deferred Heavy Gate

- Full local `make verify` is deferred by operator choice for this machine-heavy lane.
- This deferral is not a merge-readiness claim.
- Before merge readiness, current-head CI must provide heavy parity and all review threads/bot comments must be dispositioned.

## Post-Open Review Lane

- [ ] `security-auditor`
- [ ] `qa-engineer-agent`
- [ ] `bug-hunter`
- [ ] `pulseplate-pr-review`
- [ ] Codex Security plugin/local security scan
