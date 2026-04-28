# PR #1565 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565>
Branch: `codex/pulseplate-skills-wave2-3`
Date: 2026-04-28

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e06dd686d
Evidence: tools/codex_skills/pulseplate-web-launch-site/SKILL.md uses `lead-capture` consistently in the launch-site usage bullets.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565#discussion_r3156979727 -> e06dd686d

Disposition: FIXED
Commit: e06dd686d
Evidence: scripts/orchestration/skill_router.py narrows agent-product path/keyword triggers and removes the broad `public website` launch keyword to reduce over-trigger risk.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565#pullrequestreview-4192161038 -> e06dd686d

Disposition: FIXED
Commit: e06dd686d
Evidence: scripts/orchestration/skill_router.py keeps `pulseplate-web-launch-site` available in docs-only envelope, and tests/test_skill_router.py covers docs-only launch planning routing.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565#discussion_r3156986579 -> e06dd686d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565#pullrequestreview-4192168608 -> e06dd686d

Disposition: FIXED
Commit: c2765b8c0
Evidence: scripts/orchestration/skill_router.py defines `LAUNCH_SITE_CONDITIONAL_SKILLS`, removes `pulseplate-web-launch-site` from the research conditional bucket, and tests/test_skill_router.py verifies launch-specific conditional guidance.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565#pullrequestreview-4192211556 -> c2765b8c0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565#pullrequestreview-4192269599 -> c2765b8c0

Disposition: FIXED
Commit: c2765b8c0
Evidence: docs/roadmap/BACKLOG_LEDGER.md keeps `pulseplate-web-launch-site` and `pulseplate-agent-product` open as pending merge items for PR #1565 instead of marking unmerged work complete.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565#pullrequestreview-4192211556 -> c2765b8c0

Disposition: FIXED
Commit: c2765b8c0
Evidence: tools/codex_skills/pulseplate-web-launch-site/SKILL.md and tools/codex_skills/pulseplate-agent-product/SKILL.md explicitly include docs/ENGINEERING_LESSONS.md, RUNBOOK_AGENT.md, and nearest scoped AGENTS.md in required reading.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565#pullrequestreview-4192211556 -> c2765b8c0

Disposition: FIXED
Commit: c2765b8c0
Evidence: docs/dev/CODEX_SKILLS.md adds SKILL/test evidence anchors for `pulseplate-web-launch-site` and `pulseplate-agent-product` in both inventory sections.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565#pullrequestreview-4192211556 -> c2765b8c0

Disposition: NOT-A-BUG
Evidence: Commit subjects are conventional and scoped to the actual changes (`feat(codex-skills)`, `docs(review)`, and `fix(codex-skills)`); no `docs/orchestration/AGENTS.md` update exists in this PR, and rewriting already-pushed history only for a subjective docs scope would add governance risk without changing repo behavior.
Reason: The packet is part of the skills lane, not an agent behavior contract change requiring a `docs(agents)` commit subject.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1565#pullrequestreview-4192211556

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `python3 scripts/orchestration/task_bootstrap.py ... --requested-agent agent-coordinator ...` generated coordinator packet `acc91e19d4ef` with primary `agent-coordinator`.
- `python3 -m pytest tests/test_install_codex_skills.py tests/test_skill_router.py -q` PASS.
- `pre-commit run --all-files` PASS.
- `make validate-changed VENV_PYTHON=$(command -v python3)` PASS.
- Push pre-push hooks PASS: changed-file mypy, pip-audit, backend pre-push pytest, full-repo bandit, and docker build test.

## External Bot Status

- CodeRabbit: actionable feedback mapped above; pending latest pushed head after review-fix commit.
- Sourcery: actionable feedback mapped above.
- Cubic: pending on latest pushed head.

## Deferred Follow-up

- Full local `make verify` is deferred under the machine-heavy PR exception for
  this docs/skills/router lane. GitHub current-head CI is the heavy signal.

## Merge Readiness

- [ ] Current-head GitHub CI green.
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed.
- [ ] CodeRabbit, Sourcery, and Cubic actionables are mapped or explicitly marked non-actionable for the reviewed head.
- [ ] Final check pass completed after latest bot/review activity.
- [ ] Waited at least one review cycle before merge.
- [ ] `GH_TOKEN=$(gh auth token) python3 scripts/orchestration/check_merge_ready.py --pr-number 1565 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth` PASS.
