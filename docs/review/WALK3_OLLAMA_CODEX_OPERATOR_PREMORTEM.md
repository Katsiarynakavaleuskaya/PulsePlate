# Walk3 Ollama-Codex Operator Workflow Premortem

Status: pre-open closure artifact for `codex/walk3-ollama-codex-operator-workflow`.

Failure frame: it is 6 months from now and the operator workflow failed because
host-only Codex/Ollama guidance was mistaken for product runtime truth or
because the diagnostic script created new local security/tooling risk.

## Findings And Closure

| Finding | Disposition | Closure |
| --- | --- | --- |
| Doctor mutates host config or shell state. | FIXED | `scripts/orchestration/check_codex_ollama_operator.py` is read-only, uses `shutil.which()` for local binaries, and has no file write path. |
| Stale Ollama versions produce confusing `ollama launch codex-app` failures. | FIXED | The doctor now separates Codex CLI (`ollama launch codex`, v0.15+) from desktop Codex App (`ollama launch codex-app`, v0.24+) and docs name both paths. |
| Operator docs blur host Codex setup with PulsePlate backend LLM runtime. | FIXED | `docs/dev/CODEX_SKILLS.md` separates host-only Codex/Ollama workflow from `LLM_PROVIDER=ollama` runtime validation. |
| Doctor tests accidentally depend on real network or installed tools. | FIXED | `tests/test_codex_ollama_operator_doctor.py` monkeypatches binary/version/server behavior and covers missing/stale/unavailable paths. |
| MCP or backend provider integration expands V1 scope. | NOT-A-BUG | This PR explicitly leaves `llm.py`, `providers/ollama.py`, and `mcp_pulseplate_server.py` out of scope; MCP/provider work needs a separate coordinator packet. |

## Pre-Open Checklist

- Run focused doctor/template tests.
- Run repo policy guards.
- Run `make validate-changed`.
- Run `pre-commit run --all-files` before push.
- Open non-draft PR only after local narrow gates pass.
- After PR open, run `security-auditor`, `qa-engineer-agent`, `bug-hunter`,
  `pulseplate-pr-review`, and Codex Security plugin review where available.
