# PR #1576 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1576>
Branch: `codex/cloudflare-static-assets-tailwind-css`
Date: 2026-04-29

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1576#pullrequestreview-4198402760 -> 164959779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1576#discussion_r3162190364 -> 164959779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1576#pullrequestreview-4198416972 -> 164959779
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1576#discussion_r3162202726 -> 164959779

Disposition: FIXED
Commit: 164959779
Evidence: `frontend/scripts/check-tailwind-utilities.mjs` now uses `fileURLToPath(...)` before joining the built CSS bundle path, making the smoke script cross-platform.

Disposition: FIXED
Commit: 164959779
Evidence: `scripts/diagnose_web.sh` now probes root HTML and `/assets/*.css` with `--no-access-headers`, preserving anonymous public CSS validation even when private Cloudflare Access service-token env vars are present; `tests/test_deploy_contract_scripts.py` asserts CSS probes do not receive `CF-Access-Client-*` headers.

## Implementation Evidence

Disposition: FIXED
Commit: 65285f1b8
Evidence: `frontend/src/index.css` and `frontend/postcss.config.cjs` restore Tailwind/PostCSS utility generation; `frontend/scripts/check-tailwind-utilities.mjs` and `.github/workflows/frontend-ci.yml` lock the CSS bundle smoke after build.

Disposition: FIXED
Commit: 65285f1b8
Evidence: `scripts/diagnose_web.sh` now probes the hashed `/assets/*.css` bundle and fails on Cloudflare Access redirects or non-`text/css`; `tests/test_deploy_contract_scripts.py` covers the new static CSS diagnostic path.

Disposition: FIXED
Commit: 65285f1b8
Evidence: `docs/deploy/CLOUDFLARE.md`, `docs/deploy/SPA_APEX_ROUTING_CONTRACT.md`, `deploy/WORKFLOW.md`, and `deploy/PRODUCTION.md` document the narrow public GET/HEAD shell/static bypass while keeping `/api*`, `/admin*`, and private probe surfaces out of scope.

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `python3 scripts/orchestration/task_bootstrap.py --goal "Recover public static asset delivery and Tailwind CSS pipeline for pulseplate.app" --task-class "Design" --pr-phase pre_open` (PASS; packet `75e3d405a59d`)
- `python3 scripts/orchestration/task_bootstrap.py --goal "Post-open review lane for PR 1576 Cloudflare static assets and Tailwind CSS pipeline" --task-class "Design" --pr-phase post_open_review` (PASS; packet `f162f381fb48`)
- `cd frontend && npm run build` (PASS)
- `cd frontend && npm run smoke:css` (PASS)
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/pytest -q tests/test_deploy_contract_scripts.py -k 'diagnose_web'` (PASS; 8 passed)
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` (PASS; no Python files changed)
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/pre-commit run --all-files` (PASS)
- Pre-push hooks: backend pre-push pytest, full-repo Bandit, docker build test (PASS)
- Local preview static CSS: `http://127.0.0.1:4174/assets/index-D42ApsRM.css` returned `200` with `Content-Type: text/css`
- Live baseline before operator Access bypass: `curl -I https://pulseplate.app/assets/index-BN60ERUL.css` returned `302` to `pulseplate.cloudflareaccess.com`
- `cd frontend && npm run build && npm run smoke:css` after review fixes (PASS)
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/pytest -q tests/test_deploy_contract_scripts.py -k 'diagnose_web'` after review fixes (PASS; 8 passed)
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` after review fixes (PASS)
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/pre-commit run --all-files` after review fixes (PASS after Black hook formatting was committed)

## Merge Readiness

- [ ] CI green on current head
- [ ] No unresolved actionable review threads
- [ ] CodeRabbit/Sourcery/Cubic statuses reviewed and mapped
- [ ] Fixed-mapping artifact and PR body mirror aligned
- [ ] `check_merge_ready.py --require-auth` PASS
