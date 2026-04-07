# Meili zero-downtime swap PR — readiness checklist

Use this checklist before calling a PR merge-ready for the Meilisearch swap orchestration lane.

## Scope

- [ ] `app/services/meili_swap_orchestration.py` — distinct primary/candidate guard, safe unreachable
      messages (no secrets), swap-indexes + task polling.
- [ ] `scripts/meili_food_index_swap.py` — subcommands `build`, `validate`, `warm`, `swap`, `pipeline`;
      `--verbose` limits DEBUG to the swap logger namespaces.
- [ ] `tests/test_meili_swap_orchestration.py` — `httpx.MockTransport` coverage (no live Meili in CI).
- [ ] `docs/deploy/MEILISEARCH_ZERO_DOWNTIME_SWAP_RUNBOOK.md` — operator steps + `file:line` anchors.
- [ ] `docs/roadmap/BACKLOG_LEDGER.md` — `ledger-p2-search-zero-downtime-swap-orchestration` updated with
      target PR and links.

## Quality gates (local)

```bash
python3 scripts/orchestration/check_preflight.py
pre-commit run --all-files
make verify
```

## Coordinator / bug-hunter notes

- Confirm `.env.example` already documents Meili + swap env keys (no silent new required vars without
  example + compose sync per `AGENTS.md`).
- After PR number is known, rename/update `docs/review/PR_<N>_FIXED_MAPPING.md` and align ledger
  `Target PR`.
