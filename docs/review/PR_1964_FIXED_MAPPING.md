# PR 1964 Fixed in Commit Mapping

## Scope

This PR is a governance closeout for PR #1964. It corrects the PR #1954
fixed-mapping artifact so every mapped reference to the alias-guard fix commit
uses the real full commit SHA.

It does not change runtime behavior, OpenAPI/client contracts, application
logic, tests, CI workflows, security policy, entitlement, billing, LLM/RAG
runtime behavior, or iOS/web release surfaces.

## Lane Start Provenance

- Packet: artifacts/orchestration/task_packets/e759441f5e21.json
- Branch: `codex/fix-invalid-commit-sha-in-pr-mapping`
- Local recovery branch: `codex/pr-1964-governance-closeout`
- PR head at recovery start: `0330edb4bb191af5e2a48c503cd293e6ac74fc82`
- Phase: `post_open_review`
- Scope: `docs/review/PR_1954_FIXED_MAPPING.md`, `docs/review/PR_1964_FIXED_MAPPING.md`, and the PR body mirror only.
- Full local `make verify`: operator-deferred for this machine-heavy repository; not run and not claimed. Narrow changed-surface gates plus current-head CI are the validation authority for this closeout.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Review threads: none open or resolved for this PR at closeout start.
- Bot reviews/actionables: Codex, CodeRabbit, and Sourcery service-capacity notices are mapped below as non-actionable governance evidence.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1964#issuecomment-4688689046
Disposition: NOT-A-BUG
Evidence: The Codex connector comment reports code-review usage limits only; it does not request a repository code, docs, test, security, or governance change.
Reason: External service quota exhaustion is a capacity signal, not a PR defect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1964#issuecomment-4688689688
Disposition: NOT-A-BUG
Evidence: The CodeRabbit comment is an auto-generated rate-limit notice and contains no actionable finding against the PR diff.
Reason: Rate-limit notices do not require a code or fixed-mapping fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1964#pullrequestreview-4483497332
Disposition: NOT-A-BUG
Evidence: The Sourcery review body reports weekly diff-character rate-limit exhaustion only and contains no actionable repository finding.
Reason: Sourcery quota exhaustion is external reviewer capacity state, not a PR defect.

## Role Dispatch Evidence

- Startup preflight: PASS for `docs/review/PR_1954_FIXED_MAPPING.md` and `docs/review/PR_1964_FIXED_MAPPING.md`.
- Agent consistency: PASS.
- Bootstrap packet: `artifacts/orchestration/task_packets/e759441f5e21.json`.
- Role dispatch manifest: generated with `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/e759441f5e21.json --pretty`.
- Declared order followed for manual readonly role-pass synthesis: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> architecture-specialist`.
- `agent-coordinator`: scope remains limited to PR #1964 governance artifact, PR body mirror, and the existing PR #1954 SHA correction.
- `qa-engineer-agent`: acceptance gates are artifact/body validation, `git diff --check`, `make validate-changed`, pre-commit, current-head CI, and strict merge wrapper.
- `bug-hunter`: primary false-green risks are missing PR #1964 canonical artifact, stale PR body sections, and accidentally treating quota comments as unresolved code findings.
- `security-auditor`: no runtime surface, subprocess behavior, secret handling, auth, quota, CI workflow, or fail-closed security gate is changed.
- `cursor-specialist-agent`: bootstrap packet creation is recorded separately from role execution, and artifact paths stay gitignored/local where required.
- `architecture-specialist`: this closeout does not move product truth, contract truth, or governance authority out of existing repo SoT files.

## Premortem Evidence

- Skill: `pulseplate-premortem-risk-review`.
- Mode: `post_open_review`.
- Frame: 48 hours from now, this governance closeout made PR #1964 or PR #1954 merge-readiness worse.
- Risk: The PR #1964 artifact is missing, so Phase2 and merge-readiness continue to fail. Disposition: FIXED by this canonical artifact.
- Risk: The PR body omits required micro governance sections, so `pr_scope_guard` remains red. Disposition: FIXED by the refreshed PR body mirror.
- Risk: Bot quota comments are hidden under `No actionable review comments`, causing reviewer-governance drift. Disposition: FIXED by explicit `NOT-A-BUG` mappings above.
- Risk: Full local `make verify` is deferred but later described as green. Disposition: FIXED by documenting operator deferral and using narrow local gates plus current-head CI instead.
- Decision: proceed with changes, subject to final narrow local gates, current-head CI parity, strict merge-readiness wrapper, and the mandatory review wait-window.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-321a2f26cda8.json`
- Experiment id: `exp-321a2f26cda8`
- Runner mode: `oracle_only_governance_reviewer`
- Status: accepted.
- Material contribution: `fixed_mapping_review`
- Co-author trailer required: yes, because the accepted oracle result shaped this fixed-mapping and PR-body closeout evidence.
- Oracles: canonical PR #1964 mapping artifact validation returned 0; staged diff whitespace check returned 0.
- Non-authoritative rejected attempt: earlier oracle packet `exp-104b4037c74d` rejected because the multiline PR body command could not be represented safely as a shell-free oracle argv. That rejected artifact is not used as readiness evidence.

## Codex Security Diff Scan / Finding Discovery

- Skill: `codex-security:security-diff-scan`.
- Scope: PR diff for `docs/review/PR_1954_FIXED_MAPPING.md` and `docs/review/PR_1964_FIXED_MAPPING.md`.
- Report: `/tmp/codex-security-scans/pr-1964-governance/0330edb4_20260612T095153Z/report.md`.
- HTML report: `/tmp/codex-security-scans/pr-1964-governance/0330edb4_20260612T095153Z/report.html`.
- Result: PASS, no reportable findings. Manual receipts reviewed both documentation-governance surfaces; no runtime, auth, secret, CI, LLM, export, billing, entitlement, or release surface changed.

## PulsePlate PR Review

- Skill: `pulseplate-pr-review`.
- Mode: `post-open-review`.
- Direct current PR file truth: GitHub PR files API and exact `git diff` scoped PR #1964 to `docs/review/PR_1954_FIXED_MAPPING.md` before this closeout commit.
- Advisory tool limitation: `pr_review_context.py` produced a stale/mismatched changed-file list despite explicit base/head arguments, so that generated report is not used as merge-readiness proof.
- Result: no deterministic code, security, API, runtime, or governance defect found beyond the missing PR #1964 artifact and PR body sections fixed in this closeout.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path docs/review/PR_1954_FIXED_MAPPING.md --path docs/review/PR_1964_FIXED_MAPPING.md`: PASS.
- `python3 scripts/orchestration/check_agent_consistency.py`: PASS.
- `python3 scripts/orchestration/task_bootstrap.py --goal "Close PR #1964 governance artifact and body gaps for PR 1954 mapping SHA repair" --task-class Orchestration --path docs/review/PR_1954_FIXED_MAPPING.md --path docs/review/PR_1964_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent security-auditor --pr-phase post_open_review`: PASS.
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/e759441f5e21.json --pretty`: PASS.
- `git show -s --format=%H b4a8e8dc23357a8b394bbd5db933f03f349c6a91`: PASS.
- `git show -s --format=%H 0330edb4bb191af5e2a48c503cd293e6ac74fc82`: PASS.
- `python3 -c 'from scripts.orchestration.review_mapping_artifact import read_mapping_artifact, validate_mapping_artifact_text; errors=validate_mapping_artifact_text(read_mapping_artifact(1964)); print("errors", errors); raise SystemExit(1 if errors else 0)'`: PASS.
- `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1964 --body "$(cat /tmp/pr1964_body.md)"`: PASS before commit, with expected advisory warning that the Experiment Runner co-author trailer was not yet present on branch commits.
- `git diff --check`: PASS.
- `git diff --cached --check`: PASS.
- `make validate-changed`: PASS, no Python files changed on the current branch.
- `PRE_COMMIT_HOME=/tmp/pre-commit-pr1964 pre-commit run --all-files`: PASS.

## Current Non-Ready Gates

- Current-head CI after the next push is pending.
- Strict merge-readiness wrapper with `--require-auth` is pending.
- Mandatory review wait-window after latest bot/review activity is pending.
