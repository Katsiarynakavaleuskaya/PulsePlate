# Runbooks (CI / Debug / Ops)

Practical playbooks: how to run checks, diagnose failures, and perform safe
operational tasks.

## Start here

- Root triage: [`../../RUNBOOK_AGENT.md`](../../RUNBOOK_AGENT.md)

## CI / Testing

- [`CI.md`](CI.md) — how CI is set up and expected workflows
- [`CI_FIX_LOG.md`](CI_FIX_LOG.md) — history of CI fixes (reference)
- [`TEST_STATUS.md`](TEST_STATUS.md) — current test posture and expectations
- [`TEST_FIX_LOG.md`](TEST_FIX_LOG.md) — history of test fixes (reference)
- [`TESTING_BEST_PRACTICES.md`](TESTING_BEST_PRACTICES.md) — patterns to
  write stable tests
- [`LOCALE_TESTS.md`](LOCALE_TESTS.md) — localization test notes
- [`RATE_LIMIT_TESTS.md`](RATE_LIMIT_TESTS.md) — rate limit / throttling
  related test notes
- [`CACHE.md`](CACHE.md) — cache management guidance

## Ops / Scheduled jobs

- [`CRON.md`](CRON.md) — cron setup and operational notes

## Frontend CI (if applicable)

- [`FRONTEND_CI_STATUS.md`](FRONTEND_CI_STATUS.md)
- [`FRONTEND_CI_FIX_LOG.md`](FRONTEND_CI_FIX_LOG.md)
- [`FRONTEND_CI_IMPROVEMENTS.md`](FRONTEND_CI_IMPROVEMENTS.md)
- [`FRONTEND_CI_PR_NOTES.md`](FRONTEND_CI_PR_NOTES.md)
- [`FIGMA_MCP_CODEX.md`](FIGMA_MCP_CODEX.md) — Figma MCP setup and
  code-to-canvas flow for Codex/Claude
- [`FIGMA_MCP_RUNTIME_MATRIX.md`](FIGMA_MCP_RUNTIME_MATRIX.md) — runtime
  capability matrix (`generate_figma_design` availability by client)
- [`FIGMA_MCP_LIVE_ACTIVATION.md`](FIGMA_MCP_LIVE_ACTIVATION.md) —
  first-session live activation protocol
- [Figma Session Evidence Template](FIGMA_MCP_SESSION_EVIDENCE_TEMPLATE.md) —
  reproducible code-to-canvas evidence capture checklist

## Project maintenance

- [`PROJECT_UPDATES.md`](PROJECT_UPDATES.md) — how to maintain project updates

## Notes

Runbooks should be actionable. If a doc is mostly historical, move it to
[`../reports/`](../reports/) or [`../archive/`](../archive/).
