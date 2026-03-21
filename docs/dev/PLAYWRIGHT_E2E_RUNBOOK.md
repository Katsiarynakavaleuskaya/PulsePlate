# Playwright E2E Runbook (Step 3 Extension)

<!-- markdownlint-disable MD013 -->

This runbook defines the Step 3 browser E2E extension for the PulsePlate productivity pack.

## Scope guard

- This runbook is browser E2E only.
- No desktop RPA, Accessibility automation, or app-driving outside the browser.
- No runtime backend policy changes are introduced by this runbook.
- Hard backend gates remain mandatory (`make verify` is not replaced by E2E).

## Source of truth

- Skill entrypoint: `tools/codex_skills/pulseplate-playwright-e2e/SKILL.md`
- Frontend policy: `frontend/AGENTS.md`
- Operator policy: `.cursor/agents/dev-operator.md`
- Global policy: `AGENTS.md`

## Prerequisites (local)

1. Ensure Node toolchain is available:

   ```bash
   command -v npx >/dev/null 2>&1
   node --version
   npm --version
   ```

2. Resolve Playwright CLI wrapper path:

   ```bash
   export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
   export PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"
   "$PWCLI" --help
   ```

3. Prepare frontend dependencies:

   ```bash
   cd frontend
   npm ci
   cd ..
   ```

## Local execution profile

1. Start frontend in deterministic local mode:

   ```bash
   cd frontend
   npm run dev -- --host 127.0.0.1 --port 4173
   ```

2. Execute flows in a second terminal with Playwright CLI wrapper.
3. Re-snapshot after each navigation or major DOM mutation.

### npm-first fast lane (preferred for frontend contributors)

From `frontend/`:

```bash
npm run test:e2e
```

Headed debug mode:

```bash
npm run test:e2e:headed
```

Storybook visual sanity check:

```bash
npm run storybook
```

## Scenario matrix (baseline)

| ID | Flow | Start URL | Expected outcome | Artifacts |
| --- | --- | --- | --- | --- |
| `E2E-01` | Home smoke | `http://127.0.0.1:4173/` | App shell renders without fatal UI errors | Screenshot + snapshot log |
| `E2E-02` | Plate route smoke | `http://127.0.0.1:4173/plate` | Plate screen (or auth prompt) renders with deterministic shell checks | Screenshot + step log |
| `E2E-03` | Progress route smoke | `http://127.0.0.1:4173/progress` | Progress screen (or auth prompt) renders with deterministic shell checks | Screenshot + snapshot log |
| `E2E-04` | Pro paywall route smoke | `http://127.0.0.1:4173/pro` | Paywall page renders and primary CTA is visible | Screenshot + step log |

## Command pattern (CLI-first)

Use element references from the latest snapshot only. Do not hardcode `e*` ids.

```bash
"$PWCLI" open http://127.0.0.1:4173/plate --headed
"$PWCLI" snapshot
"$PWCLI" click eX
"$PWCLI" snapshot
"$PWCLI" screenshot
```

## Evidence format (required)

For each executed flow, report:

1. exact command
2. 1-3 raw output lines
3. exit code
4. `file:line` anchor for impacted code (if failure maps to repo code)
5. decision (`pass`, `actionable`, `blocked`)

## CI job template (not enabled by default)

Use this template only after `@playwright/test` and `frontend/e2e` specs are added.

```yaml
name: Frontend Playwright E2E (Template)

permissions:
  contents: read

on:
  workflow_dispatch:
  pull_request:
    branches: [main, feat/**, fix/**]
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend-playwright-e2e.yml'

jobs:
  playwright-e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    defaults:
      run:
        working-directory: frontend
    steps:
      - name: Checkout code
        uses: actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955

      - name: Set up Node.js
        uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        uses: ./.github/actions/npm-ci-with-retry
        with:
          working-directory: frontend

      - name: Install Playwright browser
        run: npx playwright install --with-deps chromium

      - name: Start frontend app
        run: npm run dev -- --host 127.0.0.1 --port 4173 > /tmp/frontend-dev.log 2>&1 &

      - name: Wait for frontend readiness
        run: |
          for i in {1..60}; do
            if curl -fsS http://127.0.0.1:4173/ >/dev/null; then
              exit 0
            fi
            sleep 1
          done
          echo "Frontend did not start in time"
          exit 1

      - name: Run Playwright E2E
        run: npx playwright test e2e --project=chromium

      - name: Upload Playwright artifacts
        if: always()
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: playwright-artifacts
          path: |
            frontend/playwright-report
            frontend/test-results
            /tmp/frontend-dev.log
          if-no-files-found: ignore
          retention-days: 7
```

## Promotion criteria from template to active CI

- `frontend/e2e` scenarios exist and are deterministic.
- Flows map to owned product routes and stable selectors.
- At least one PR cycle with artifact review is completed.
- No policy conflict with existing frontend CI gates.
