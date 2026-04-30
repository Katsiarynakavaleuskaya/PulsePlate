# Local Ollama Nemotron Runtime Runbook

**Status:** local/operator runbook; not a PR-open packet.
**Last updated:** 2026-04-30.

This runbook documents the narrow local profile for validating PulsePlate with
Ollama and `nemotron-mini`. It does not open a PR, change provider runtime code,
or widen the food-data updater scope.

## Coordinator Start

Run coordinator bootstrap before editing this lane:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py \
  --goal "Document and validate local Ollama Nemotron runtime profile without opening a PR" \
  --task-class "AI / ML" \
  --pr-phase pre_open
```

Operator-declared role order for this no-PR local slice:

1. `agent-coordinator` - scope lock, no-PR/no-full-verify constraints, final DoD.
2. `ai-innovation-specialist` - Ollama/Nemotron local AI runtime profile.
3. `backend-engineer` - provider/env contract compatibility.
4. `architecture-specialist` - no provider/schema/runtime scope drift.
5. `security-auditor` - `SERVER_SALT`, local secret posture, no new exposure.
6. `cursor-specialist-agent` - runbook/docs consistency.
7. `qa-engineer-agent` - narrow validation plan.
8. `bug-hunter` - false-green startup/provider edge cases.

Skills and plugins are bounded:

- Use `pulseplate-agent-product` for operator workflow and governance boundaries.
- Use `pulseplate-pr-review` only in dry-run/pre-open mode.
- Browser Use and Computer Use are optional local evidence helpers.
- GitHub and CodeRabbit are post-PR tools only; they are not required here.

## Local Environment

The PulsePlate runtime reads `OLLAMA_ENDPOINT`, not `OLLAMA_HOST`.

```bash
export SERVER_SALT="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"

export APP_ENV=local
export ENVIRONMENT=local
export LLM_PROVIDER=ollama
export OLLAMA_ENDPOINT=http://localhost:11434
export OLLAMA_MODEL=nemotron-mini
export OLLAMA_TIMEOUT=120
export DISABLE_BACKGROUND_UPDATES=1
```

`DISABLE_BACKGROUND_UPDATES=1` is optional for AI runtime smoke tests. It keeps
Open Food Facts/background updater noise out of the local Ollama validation path.

Start the backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Smoke Checks

Backend readiness:

```bash
curl http://127.0.0.1:8000/ready
```

Direct Ollama chat:

```bash
curl http://localhost:11434/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nemotron-mini",
    "messages": [
      {
        "role": "user",
        "content": "Give one short wellness meal-planning tip."
      }
    ],
    "stream": false
  }'
```

Expected local evidence:

- `/ready` returns `200 OK`.
- `/ready` reports `primary_provider` as `ollama` when the Ollama env is active.
- Ollama `/api/chat` returns `200 OK` and a non-empty assistant message.

## Narrow Gates

Do not run full `make verify` for this local no-PR slice unless the operator
explicitly approves the CPU cost.

Allowed focused gates:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pytest tests/test_llm.py tests/test_llm_extras.py tests/test_llm_lite_providers.py tests/test_providers_unit.py
pytest tests/test_lifespan_background_updates.py
```

If this later becomes a PR, run `pre-commit run --all-files` before any push and
use the PR-governance gates from `AGENTS.md` and `RUNBOOK_AGENT.md`.

## Out Of Scope

Do not mix these issues into the Ollama/Nemotron slice:

- Open Food Facts `503` responses from the background updater.
- Corrupted food cache JSON under `core.food_apis.unified_db`.
- Mineral-water foods without protein/fat/carbs.

Those belong in separate food-data/cache bugfix lanes if they become product
blockers.
