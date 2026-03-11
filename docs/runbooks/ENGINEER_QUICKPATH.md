# Engineer Quick Path

Short canonical path for day-to-day engineering work.
Policy lives in [`AGENTS.md`](../../AGENTS.md); this file is execution-focused only.
Keep links in this runbook repository-relative so they work in every clone and rendered view.

## Start here

1. `git status --short`
2. `git log -1 --oneline`
3. `python3 scripts/orchestration/check_preflight.py`
4. For local API startup, use `uvicorn app.main:app --reload` as the canonical ASGI entrypoint.

If preflight fails, stop and fix that first.

## Daily path

1. Read the root [`AGENTS.md`](../../AGENTS.md), [`RUNBOOK_AGENT.md`](../../RUNBOOK_AGENT.md), and the nearest scoped `AGENTS.md` for the files you will touch.
2. Make the smallest scoped change that satisfies the task.
3. Run the cheapest relevant check first:
   - `pytest -q tests/test_repo_policy_guards.py` for guard-sensitive work
   - `make test-fast` for backend signal
   - targeted `pytest` for changed modules when narrowing a failure

## API / contract path

Use this when routers, schemas, route metadata, or generated client contracts change.

1. `make openapi`
2. `make openapi-check`
3. Review `frontend/src/api/openapi.json` and `frontend/src/api/schema.ts` diffs before finalizing
4. Update `docs/contracts/API_CANONICAL_MAP.md` if route surface or namespace semantics changed

Current note:
- `make openapi` is the canonical combined command.
- Backend/frontend split targets are still tracked as a workflow follow-up in `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-openapi-decoupling-split`.

## Before push

1. `pre-commit run --all-files`
2. `make verify`

Do not claim green or merge-ready without local evidence.

## Red CI triage

1. `pytest -q tests/test_repo_policy_guards.py`
2. `make test-fast`
3. `make lint`
4. Use [`RUNBOOK_AGENT.md`](../../RUNBOOK_AGENT.md) for deeper CI/debug procedures

## Deployment note

- Prefer `docker compose` in new or edited commands.
- Existing `docker-compose` references in repo command surfaces are a tracked migration seam, not the canonical target state. See `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-compose-v2-migration`.
