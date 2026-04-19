---
name: pulseplate-playwright-e2e
description: Execute controlled Playwright browser E2E checks for PulsePlate web flows with deterministic evidence output.
---

# PulsePlate Playwright E2E

<!-- markdownlint-disable MD013 -->

## When to use

- Step 3 extension after core productivity pack is in place.
- Validating key browser flows in `frontend/` (login, onboarding, premium gates, exports).
- Reproducing UI bugs that are hard to isolate with unit tests only.
- Running predefined Step 3 smoke scenarios from the runbook.

## Inputs required

- Target environment URL (local or preview).
- Flow list (1-3 user journeys to validate).
- Expected pass criteria per journey.
- Scenario IDs (from runbook matrix, e.g. `E2E-01` ... `E2E-04`).

## Procedure (commands)

1. Ensure frontend dependencies are ready:

   ```bash
   cd frontend
   npm ci
   cd ..
   ```

2. Run the repo-owned Playwright MCP doctor before any browser flow:

   ```bash
   python3 scripts/playwright_mcp.py doctor
   ```

3. Install the local Chromium payload via the repo-owned helper:

   ```bash
   cd frontend
   npm run test:e2e:install
   cd ..
   ```

4. Use Playwright skill/tooling to run browser automation against selected flows.
5. Capture deterministic artifacts:
   - command and config used
   - failing step and selector/action
   - screenshot path or trace path when available
6. Re-run only failing flow after fix.
7. Follow the runbook evidence contract for every flow.

## Output format

- `Flow matrix`: flow name + pass/fail.
- `Scenario IDs`: include exact executed scenario IDs.
- `Failure evidence`: raw failing lines and failing step.
- `Pointers`: file references for impacted UI/API contracts.
- `Fix plan`: minimal changes to restore flow.
- `Rerun`: exact command sequence.

## Guardrails

- Scope is browser E2E only; no desktop RPA.
- Do not use Playwright to bypass thin-client policy or API contracts.
- Keep runs targeted; avoid broad unstable suites without need.
- Do not claim release readiness solely from E2E; keep hard backend gates mandatory.
- Treat doctor failures as blocking: do not continue with Playwright MCP runs on a
  mismatched Node runtime or missing browser payloads.

## SoT links

- `frontend/AGENTS.md`
- `tools/codex_skills/pulseplate-frontend-ui/SKILL.md`
- `docs/dev/PLAYWRIGHT_E2E_RUNBOOK.md`
- `.cursor/agents/dev-operator.md`
- `AGENTS.md`
