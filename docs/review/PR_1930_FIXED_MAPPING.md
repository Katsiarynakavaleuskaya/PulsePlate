# PR #1930 Fixed in Commit Mapping

## Summary

PR #1930 keeps the Codex prompt renderer from crashing when task packets provide malformed `native_subagent_bridge.secondary` or `native_subagent_bridge.advisory` fields. The implementation fails closed with `PromptError` and the regression tests assert no traceback and no misleading prompt output.

## Scope

- In scope: `scripts/orchestration/render_codex_start_prompt.py`, `tests/test_render_codex_start_prompt.py`, and this governance artifact.
- Out of scope: backend runtime, OpenAPI, web, iOS, nutrition data, LLM runtime, billing, release, and external dependency changes.
- Public API impact: none.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/920fad84299c.json`
- Dispatch manifest command: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/920fad84299c.json --pretty`
- Dispatch sequence executed in order: `agent-coordinator -> architecture-specialist -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> web-research-agent`.
- Note: PR #1930 was already open before this closeout pass; this artifact records post-open governance recovery and does not claim pre-open role execution.

## Role Review Evidence

- `agent-coordinator`: BLOCKED only on missing `docs/review/PR_1930_FIXED_MAPPING.md`; confirmed scope is narrow, no review threads exist, and implementation can stay governance-only unless later roles find a code/test issue.
- `architecture-specialist`: PASS; validation helper is renderer-local, does not duplicate canonical role-order semantics, and still delegates parsed role order to `qoder_dispatch_bridge`.
- `qa-engineer-agent`: PASS for implementation/test adequacy; blocker remains missing mapping artifact. Focused renderer tests passed with the repo venv.
- `bug-hunter`: PASS for implementation; no traceback or false-green bug found. Noted stale/cancelled CI rows must not be used for current-head readiness and CodeRabbit skipped/rate-limited must not be counted as substantive review.
- `security-auditor`: PASS for implementation security; no new command execution, auth, secret, nosec, type-ignore, network, persistence, or production runtime boundary was introduced.
- `cursor-specialist-agent`: PASS for tooling semantics; prompt field escaping, shell quoting, packet-provided dispatch commands, and runtime-owner flag preservation remain intact.
- `web-research-agent`: PASS / NOT-APPLICABLE for external web research; this repo-local prompt-renderer validation introduces no external standard, dependency, CVE, public product, legal, medical, or research claim.

## Premortem Closure

Frame: 48 hours after closeout, this PR made governance worse because the mapping/body evidence claimed more than the current head proved.

| Failure mode | Closure | Evidence |
| --- | --- | --- |
| Missing canonical mapping artifact keeps Phase 2 and merge readiness red. | FIXED by this artifact. | `scripts/orchestration/review_mapping_artifact.py` defines the artifact as source of truth; current CI failure named `docs/review/PR_1930_FIXED_MAPPING.md` as missing. |
| CodeRabbit skipped/rate-limited status is misread as substantive no-actionable review. | NOT-A-BUG for implementation; must stay documented as skipped/rate-limited until rerun or separately dispositioned. | CodeRabbit comment `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1930#issuecomment-4659766825`; `gh pr checks` row says `Review skipped`. |
| Local isolated worktree uses system Python and falsely reports missing dependencies. | NOT-A-BUG for PR code; validation uses `VENV_PYTHON` pointed at the repo-approved root venv for focused Python gates. | `$VENV_PYTHON -m pytest -q -p no:cacheprovider tests/test_render_codex_start_prompt.py` -> `20 passed`. |
| A stale cancelled `test-pr` row is treated as current-head failure. | NOT-A-BUG; use strict current-head merge wrapper and targeted run inspection, not raw mixed diagnostic rows. | Bug-hunter pass and `gh pr checks` diagnostic output identified the stale cancelled row separately from current-head code checks. |

Decision: proceed with governance closeout only; do not change implementation unless fresh current-head checks or review comments produce a concrete actionable issue.

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/exp-11a5ebbb17dc.json

Mode: `oracle_only_governance_reviewer`.

Contribution: `fixed_mapping_review`; accepted result with three passing immutable oracles. The closeout commit includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because the oracle result shapes this mapping and commit decision.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- GitHub review-thread check found zero review threads on PR #1930.
- No human review-thread entries were available to resolve or map.
- Sourcery review commented that the changes look good.
- Cubic reported no issues across the two changed files.
- Codecov reported all modified and coverable lines are covered by tests.
- CodeRabbit posted a rate-limit / usage-credits skip notice. This artifact does not claim CodeRabbit completed a substantive no-actionable review.

## Fixed in Commit Mapping
- No actionable review comments

## Bot Review Summary

- CodeRabbit: skipped/rate-limited at head `d6ace99e`; not counted as substantive PASS. Must be rerun or explicitly dispositioned before any final merge-readiness claim if repo policy requires a real CodeRabbit signal.
- Sourcery: COMMENTED at head `d6ace99e` with no actionable findings.
- Cubic: COMMENTED at head `d6ace99e` with "No issues found" across two files.
- Codecov: patch comment says all modified and coverable lines are covered by tests.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path scripts/orchestration/render_codex_start_prompt.py --path tests/test_render_codex_start_prompt.py --path docs/review/PR_1930_FIXED_MAPPING.md` -> PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS.
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/920fad84299c.json --pretty` -> PASS; manifest produced the executed role order above.
- `$VENV_PYTHON -m py_compile scripts/orchestration/render_codex_start_prompt.py tests/test_render_codex_start_prompt.py` -> PASS, with `VENV_PYTHON` set to the repo-approved root virtualenv interpreter.
- `$VENV_PYTHON -m pytest -q -p no:cacheprovider tests/test_render_codex_start_prompt.py` -> `20 passed`, with `VENV_PYTHON` set to the repo-approved root virtualenv interpreter.
- `git diff --check origin/main...HEAD` -> PASS with no output.
- Codex Security diff scan / finding discovery: local scan id `d6ace99e61b2_20260611T000000Z`; no plausible security findings; worklist and ledger closure were written under the Codex Security `/tmp/codex-security-scans` artifact tree.
- `pulseplate-pr-review`: dry-run report generated under `/tmp/pulseplate_pr_1930_review_report.md`; no code findings. One advisory large-diff note is NOT-A-BUG for PR #1930 because GitHub `files` and local `origin/main...HEAD` diff both show only `scripts/orchestration/render_codex_start_prompt.py` and `tests/test_render_codex_start_prompt.py`; the helper's broader list came from a double-dot comparison against the PR creation-time base SHA.
- `make validate-changed` with `VENV_PYTHON` set to the repo-approved root venv -> PASS; selected `tests/test_render_codex_start_prompt.py`.
- `pre-commit run --all-files` -> first run failed in `backend-tests` because the isolated worktree could not auto-discover the shared/root `.venv`; rerun with absolute `VENV_PYTHON` override -> PASS.
- `make verify` -> FAIL in full-repo `make typecheck` on unrelated semantic-cache mypy errors in `core/ai/semantic_cache_offline_admission_runner.py` and `core/ai/semantic_cache_shadow_admission_harness.py`. These files are outside the PR #1930 diff; do not claim merge readiness until full verify passes, CI/current-head parity plus an approved exception is documented, or the unrelated typecheck failure is resolved in the owning lane.

## Merge Readiness

- [ ] Current-head PR Body Phase2 gates pass after the closeout commit.
- [ ] Current-head Merge readiness gate passes after the closeout commit.
- [ ] Required current-head code/governance/security checks pass after the closeout commit.
- [ ] `GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_merge_ready.py --pr-number 1930 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth` passes after current-head checks settle.
- [ ] No unresolved review threads or actionable bot comments remain.
- [ ] CodeRabbit receives a substantive rerun/no-actionable signal or an approved repo-governance disposition is recorded.
- [ ] Mandatory wait-window after latest bot/review activity has elapsed.

## Deferred / Follow-ups

- None for implementation. Merge remains blocked until the post-closeout current-head gates and bot-review governance requirements above are satisfied.
