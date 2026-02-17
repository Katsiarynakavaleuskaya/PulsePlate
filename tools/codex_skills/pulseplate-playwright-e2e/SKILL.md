---
name: pulseplate-playwright-e2e
description: Execute controlled Playwright browser E2E checks for PulsePlate web flows with deterministic evidence output.
---

# PulsePlate Playwright E2E

## When to use
- Step 3 extension after core productivity pack is in place.
- Validating key browser flows in `frontend/` (login, onboarding, premium gates, exports).
- Reproducing UI bugs that are hard to isolate with unit tests only.

## Inputs required
- Target environment URL (local or preview).
- Flow list (1-3 user journeys to validate).
- Expected pass criteria per journey.

## Procedure (commands)
1. Ensure frontend dependencies are ready:
   ```bash
   cd frontend
   npm install
   cd ..
   ```
2. Use Playwright skill/tooling to run browser automation against selected flows.
3. Capture deterministic artifacts:
   - command and config used
   - failing step and selector/action
   - screenshot path or trace path when available
4. Re-run only failing flow after fix.

## Output format
- `Flow matrix`: flow name + pass/fail.
- `Failure evidence`: raw failing lines and failing step.
- `Pointers`: file references for impacted UI/API contracts.
- `Fix plan`: minimal changes to restore flow.
- `Rerun`: exact command sequence.

## Guardrails
- Scope is browser E2E only; no desktop RPA.
- Do not use Playwright to bypass thin-client policy or API contracts.
- Keep runs targeted; avoid broad unstable suites without need.
- Do not claim release readiness solely from E2E; keep hard backend gates mandatory.

## SoT links
- `frontend/AGENTS.md`
- `tools/codex_skills/pulseplate-frontend-ui/SKILL.md`
- `.cursor/agents/dev-operator.md`
- `AGENTS.md`
