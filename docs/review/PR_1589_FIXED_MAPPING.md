# PR #1589 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1589>
Branch: `codex/prelaunch-access-smoke-contract`
Date: 2026-04-30

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1589#issuecomment-4350573854 -> 43f406399
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1589#pullrequestreview-4203332341 -> 43f406399
Disposition: FIXED
Commit: 43f406399
Evidence: `docs/deploy/CLOUDFLARE.md` now marks the prelaunch access smoke section as canonical, defines the launch gate as the operator-approved release decision, links the existing ledger automation anchor, and keeps supporting docs as references instead of separate sources of truth.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1589#discussion_r3166381960 -> 43f406399
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1589#discussion_r3166381972 -> 43f406399
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1589#discussion_r3166381979 -> 43f406399
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1589#pullrequestreview-4203352052 -> 43f406399
Disposition: FIXED
Commit: 43f406399
Evidence: `docs/deploy/CLOUDFLARE.md` adds the diagnostic pointer and service-token secrets hygiene; `docs/deploy/SPA_APEX_ROUTING_CONTRACT.md` clarifies the concrete CSS probe and protected `/health*` / `/ready` operator-probe contract; `scripts/QUICK_DIAGNOSTIC.md` clarifies `/legacy/bmi-calculator` as reopen-only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1589#discussion_r3164880000
Disposition: NOT-A-BUG
Evidence: `docs/deploy/SPA_APEX_ROUTING_CONTRACT.md` intentionally keeps `/health*` and `/ready` protected during closed prelaunch/reopen preparation, and now states that deployment/recovery checks must use authenticated/operator or Access service-token probes while the host is closed.
Reason: Making health/ready public would weaken the prelaunch security boundary and is outside this docs-only access-smoke contract.

## Implementation Evidence

Disposition: FIXED
Commit: 4a7975c8
Evidence: Initial docs-only contract added prelaunch Access expectations without runtime, Cloudflare dashboard/API, frontend, Caddy, deploy script, or security-policy code changes.

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `python3 scripts/orchestration/task_bootstrap.py --goal "Document prelaunch Cloudflare Access smoke contract without public reopen" --task-class "Design" --pr-phase pre_open` (PASS; packet `8a36f72d1c1f`)
- `python3 scripts/orchestration/task_bootstrap.py --goal "Review prelaunch Cloudflare Access smoke contract PR" --task-class "Design" --pr-phase post_open_review` (PASS; packet `c2f2bf9fda5d`)
- `pre-commit run --all-files` (PASS)
- `make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python` (PASS; no Python files changed)
- `rg -n "Prelaunch access smoke contract|launch gate|Cloudflare Access|pulseplate\\.cloudflareaccess\\.com" docs/deploy scripts/QUICK_DIAGNOSTIC.md` (PASS)
- Pre-push hooks: backend pre-push pytest, full-repo Bandit, docker build test (PASS)

## Merge Readiness

- [ ] CI green on current head
- [ ] No unresolved actionable review threads
- [ ] CodeRabbit/Sourcery/Cubic statuses reviewed
- [ ] Fixed-mapping artifact and PR body mirror aligned
- [ ] `check_merge_ready.py --require-auth` PASS
