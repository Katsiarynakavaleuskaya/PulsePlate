# PR 1739 Fixed in Commit Mapping

## PR
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739

## Scope
- Recover PR #1739 after main Docker/CD/security stabilization.
- Preserve fail-closed current-head fallback behavior for canonical PR checks.
- Keep external bot status contexts advisory unless GitHub marks them required.
- Preserve touched-surface gating for specialized Docker, frontend, and iOS workflows.

## Coordinator Packet
- Post-open packet: `artifacts/orchestration/task_packets/f0b7158469f5.json` (local, gitignored)
- Canonical restart packet: `artifacts/orchestration/task_packets/1eb2fe0337b1.json` (local, gitignored)
- Role order: `agent-coordinator -> architecture-specialist -> security-auditor -> dev-operator -> qa-engineer-agent -> bug-hunter`

## Implementing Commits
- `b4f7fd390` - `fix(ci): bound fallback current-head blockers`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Known post-open role findings have been dispositioned:
- PR review dry-run: missing fixed-mapping artifact - FIXED by this artifact.
- Premortem/security: over-broad fallback blocking could convert advisory bot statuses or unattached specialized lanes into hard blockers - FIXED by `b4f7fd390`.
- QA/bug-hunter: focused fallback semantics needed deterministic tests for external bot status contexts, attached Docker checks, unattached specialized checks, and optional lanes - FIXED by `b4f7fd390`.

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3224388167 -> b4f7fd390
Disposition: FIXED
Commit: b4f7fd390
Evidence: scripts/ci/check_current_head_pr_checks.py (`CANONICAL_FALLBACK_STATUS_CONTEXT_NAMES`, `_is_blocking_fallback_advisory`); tests/test_current_head_pr_checks.py (`CodeRabbit` status context case).
Reason: Fallback mode blocks canonical `CI` status contexts only; external bot status contexts remain advisory unless branch protection marks them required.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3224388187 -> b4f7fd390
Disposition: FIXED
Commit: b4f7fd390
Evidence: scripts/ci/check_current_head_pr_checks.py (`DOCKER_SURFACE_PREFIXES`, `FRONTEND_SURFACE_PREFIXES`, `IOS_SURFACE_PREFIXES`); tests/test_current_head_pr_checks.py (attached and unattached specialized-check cases).
Reason: Specialized workflow checks block fallback only when changed files attach the corresponding surface.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3224388191 -> b4f7fd390
Disposition: FIXED
Commit: b4f7fd390
Evidence: scripts/ci/check_current_head_pr_checks.py (`CANONICAL_FALLBACK_CI_CHECK_NAMES` excludes push-only feature/main lanes); tests/test_current_head_pr_checks.py (optional lane remains advisory in fallback).
Reason: Push-only or optional current-head checks stay advisory in fallback unless they are canonical PR checks or attached specialized-surface checks.

## Validation
- `python3 scripts/orchestration/check_preflight.py --path scripts/ci/check_current_head_pr_checks.py --path tests/test_current_head_pr_checks.py --path docs/review/PR_1739_FIXED_MAPPING.md` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/orchestration/task_bootstrap.py --goal "Recover PR 1739 fail-closed current-head CI fallback after main stabilization" --task-class infra --path scripts/ci/check_current_head_pr_checks.py --path tests/test_current_head_pr_checks.py --path docs/review/PR_1739_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent security-auditor --requested-agent dev-operator --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase post_open_review` - PASS, packet `f0b7158469f5`
- `python3 scripts/orchestration/task_bootstrap.py --goal "PR 1739 canonical restart: recover fail-closed current-head CI fallback after main stabilization" --task-class infra --path scripts/ci/check_current_head_pr_checks.py --path tests/test_current_head_pr_checks.py --path docs/review/PR_1739_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent security-auditor --requested-agent dev-operator --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase post_open_review` - PASS, packet `1eb2fe0337b1`
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_current_head_pr_checks.py` - PASS
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_repo_policy_guards.py` - PASS

## Security Notes
- This change does not weaken required branch-protection checks.
- Fallback remains fail-closed for canonical PR checks and attached specialized workflow surfaces.
- External bot statuses remain advisory status checks; actionable bot review comments still block through review-governance mapping.

## Risks / Rollback
- Risk: touched-surface classification may need future expansion as workflow surfaces evolve.
- Rollback: revert `b4f7fd390` to return to the previous PR behavior, or revert PR #1739 after merge.
