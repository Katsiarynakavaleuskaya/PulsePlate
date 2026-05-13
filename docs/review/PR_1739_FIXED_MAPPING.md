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
- `4be17a1e6` - `fix(ci): refine fallback specialized surfaces`
- `50064a367` - `fix(ci): attach diagnostic fallback surfaces`
- `b06d905e6` - `fix(ci): keep soft fallback lanes advisory`

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#pullrequestreview-4269878518 -> b4f7fd390
Disposition: FIXED
Commit: b4f7fd390
Evidence: docs/review/PR_1739_FIXED_MAPPING.md maps all actionable review comments from that review; scripts/ci/check_current_head_pr_checks.py and tests/test_current_head_pr_checks.py contain the bounded fallback fix.
Reason: The Sourcery review summary pointed to the actionable review set, which is fully dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230113752 -> 4be17a1e6
Disposition: FIXED
Commit: 4be17a1e6
Evidence: scripts/ci/check_current_head_pr_checks.py checks iOS job-name prefixes before canonical CI fallback names; tests/test_current_head_pr_checks.py covers attached iOS CI blocking.
Reason: Attached iOS CI jobs from the canonical CI workflow now block fallback when iOS paths changed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230113754 -> 4be17a1e6
Disposition: FIXED
Commit: 4be17a1e6
Evidence: scripts/ci/check_current_head_pr_checks.py expands `FRONTEND_SURFACE_PREFIXES`; tests/test_current_head_pr_checks.py covers `.nvmrc` attaching Frontend CI.
Reason: Frontend fallback routing now includes the workflow trigger surfaces needed for frontend/design-token checks.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230113763 -> 4be17a1e6
Disposition: FIXED
Commit: 4be17a1e6
Evidence: scripts/ci/check_current_head_pr_checks.py no longer classifies `Greenlight iOS Preflight` as fallback-blocking; tests/test_current_head_pr_checks.py keeps Greenlight report-only checks advisory.
Reason: Greenlight is report-only and remains a soft/advisory signal in fallback mode.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230113767 -> 4be17a1e6
Disposition: FIXED
Commit: 4be17a1e6
Evidence: scripts/ci/check_current_head_pr_checks.py expands Docker runtime dependency surfaces; tests/test_current_head_pr_checks.py covers `requirements-docker-runtime.txt` attaching Docker fallback.
Reason: Docker fallback now blocks when runtime dependency files that feed the production image change.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#pullrequestreview-4276547815 -> 4be17a1e6
Disposition: FIXED
Commit: 4be17a1e6
Evidence: docs/review/PR_1739_FIXED_MAPPING.md uses repo-portable pytest commands in the Validation section; all actionable comments from the review are mapped above.
Reason: The CodeRabbit review summary contained a validation-record nitpick and referenced the latest actionable review set, both fixed in the mapped commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230169702
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1739_FIXED_MAPPING.md lists `4be17a1e6` under Implementing Commits.
Reason: The traceability issue was already corrected in this artifact before merge-readiness; no production code change is required for a review-artifact completeness comment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#pullrequestreview-4276615286
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1739_FIXED_MAPPING.md maps the actionable CodeRabbit inline comment from that review.
Reason: The review summary only reports the inline artifact-completeness comment, which is dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230186042 -> 50064a367
Disposition: FIXED
Commit: 50064a367
Evidence: scripts/ci/check_current_head_pr_checks.py expands `IOS_SURFACE_PREFIXES` to include workflow/action files; tests/test_current_head_pr_checks.py covers iOS fallback blocking for `.github/workflows/ci.yml` and `.github/actions/python-setup/action.yml`.
Reason: Attached iOS CI jobs now remain fallback-blocking when workflow/action edits attach the iOS lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230186050 -> 50064a367
Disposition: FIXED
Commit: 50064a367
Evidence: scripts/ci/check_current_head_pr_checks.py includes `.github/workflows/accessibility.yml` in `FRONTEND_SURFACE_PREFIXES`; tests/test_current_head_pr_checks.py covers `Accessibility Tests` fallback blocking for that workflow file.
Reason: Accessibility workflow edits now attach the frontend/accessibility fallback lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230186053
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor b4f7fd390 HEAD` and `git merge-base --is-ancestor 4be17a1e6 HEAD` both return `0` at current local head.
Reason: The mapped commits are ancestors of the current PR head; no remapping to a squashed synthetic head is needed for this branch.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230186062 -> 50064a367
Disposition: FIXED
Commit: 50064a367
Evidence: scripts/ci/check_current_head_pr_checks.py includes `test-main (3.11)`, `test-main (3.12)`, and `test-main (3.13)` in `CANONICAL_FALLBACK_CI_CHECK_NAMES`; tests/test_current_head_pr_checks.py covers a failed attached `test-main (3.11)` fallback blocker.
Reason: PR-triggered diagnostic `test-main` matrix jobs are now fallback-blocking when GitHub attaches them.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#pullrequestreview-4276633266 -> 50064a367
Disposition: FIXED
Commit: 50064a367
Evidence: docs/review/PR_1739_FIXED_MAPPING.md maps all actionable comments from that review; scripts/ci/check_current_head_pr_checks.py and tests/test_current_head_pr_checks.py contain the diagnostic fallback-surface fixes.
Reason: The Codex review summary pointed to the latest actionable review set, which is fully dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230239375
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1739_FIXED_MAPPING.md uses repo-portable validation commands.
Reason: The local absolute path was removed from validation evidence before merge-readiness; no production code change is required for this artifact hygiene finding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#pullrequestreview-4276694119
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1739_FIXED_MAPPING.md maps the actionable CodeRabbit inline comment from that review.
Reason: The review summary only reports the inline validation-path comment, which is dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230273033
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor 50064a367 HEAD` returns `0` at current local head.
Reason: The mapped commit is an ancestor of the current PR head; no squashed-head remapping is needed for this branch.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230273047 -> b06d905e6
Disposition: FIXED
Commit: b06d905e6
Evidence: scripts/ci/check_current_head_pr_checks.py keeps `Accessibility Tests` out of `FRONTEND_FALLBACK_WORKFLOW_NAMES`; tests/test_current_head_pr_checks.py covers accessibility workflow checks as advisory in fallback mode.
Reason: Accessibility remains a soft/advisory lane unless branch protection marks it required.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1739#discussion_r3230273049 -> b06d905e6
Disposition: FIXED
Commit: b06d905e6
Evidence: scripts/ci/check_current_head_pr_checks.py fetches PR changed paths only when required-check metadata is unavailable; tests/test_current_head_pr_checks.py covers the required-metadata path without fetching changed paths.
Reason: Required-check mode and draft skip no longer depend on unnecessary PR-files permissions.

## Validation
- `python3 scripts/orchestration/check_preflight.py --path scripts/ci/check_current_head_pr_checks.py --path tests/test_current_head_pr_checks.py --path docs/review/PR_1739_FIXED_MAPPING.md` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/orchestration/task_bootstrap.py --goal "Recover PR 1739 fail-closed current-head CI fallback after main stabilization" --task-class infra --path scripts/ci/check_current_head_pr_checks.py --path tests/test_current_head_pr_checks.py --path docs/review/PR_1739_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent security-auditor --requested-agent dev-operator --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase post_open_review` - PASS, packet `f0b7158469f5`
- `python3 scripts/orchestration/task_bootstrap.py --goal "PR 1739 canonical restart: recover fail-closed current-head CI fallback after main stabilization" --task-class infra --path scripts/ci/check_current_head_pr_checks.py --path tests/test_current_head_pr_checks.py --path docs/review/PR_1739_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent security-auditor --requested-agent dev-operator --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase post_open_review` - PASS, packet `1eb2fe0337b1`
- `python3 -m pytest -q tests/test_current_head_pr_checks.py` - PASS
- `python3 -m pytest -q tests/test_repo_policy_guards.py` - PASS
- `python3 -m pytest -q tests/test_current_head_pr_checks.py` - PASS
- `python3 -m pytest -q tests/test_current_head_pr_checks.py` - PASS

## Security Notes
- This change does not weaken required branch-protection checks.
- Fallback remains fail-closed for canonical PR checks and attached specialized workflow surfaces.
- External bot statuses remain advisory status checks; actionable bot review comments still block through review-governance mapping.

## Risks / Rollback
- Risk: touched-surface classification may need future expansion as workflow surfaces evolve.
- Rollback: revert `b4f7fd390` to return to the previous PR behavior, or revert PR #1739 after merge.
