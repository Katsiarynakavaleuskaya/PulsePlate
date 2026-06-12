# PR #1945 Fixed in Commit Mapping

## Summary
- Scope: test-only CI supply-chain regression coverage for the `test-main` checkout pin.
- Branch: `codex/propose-fix-for-sha-pin-regression-test`.
- Pre-governance code commit: `60e5b91ddc29452f74d24f4541c41261279ad676`.
- Runtime/API/schema/client/workflow changes: none.

## Lane Start Provenance
- Packet: `artifacts/orchestration/task_packets/e4b6587c30a6.json`
- Branch: `codex/propose-fix-for-sha-pin-regression-test`
- Task class: `pr_governance`
- PR phase: `post_open_review`
- Declared role order: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> web-research-agent`
- Dispatch evidence: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/e4b6587c30a6.json --pretty --pr-phase post_open_review`

## Experiment Runner Evidence
- Artifact: `artifacts/orchestration/experiments/results/exp-aa771fb712c8.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Oracle commands: `git diff --check`; `python -m py_compile tests/test_python_supply_chain_controls.py`; `python -m pytest -q tests/test_python_supply_chain_controls.py::test_ci_main_full_suite_checkout_uses_pinned_checkout_action -p no:cacheprovider`; `python3 scripts/ci/guard_actions_pin.py --root .`
- Mutation boundary: `mutated_paths=[]`, `shared_tree_untouched=true`, `promotion_ready=false`
- Co-author: required (`contribution_kind=fixed_mapping_review`, `coauthor_required=true`)
- Authority: advisory evidence only; merge readiness remains owned by repo gates, current-head CI, review governance, and strict merge wrapper.

## Post-Open Role Review Evidence
- `agent-coordinator`: scope locked to the existing test diff plus governance artifact/body; no workflow/runtime/product code changes authorized unless focused validation proves the test change broken.
- `qa-engineer-agent`: no QA blocker; focused pytest, actions pin guard, py_compile, and diff check passed; regression test directly covers `ci.yml:test-main` `Checkout` pin.
- `bug-hunter`: no test-logic blocker; false-red risk for legitimate future checkout SHA upgrades is expected and must update the test with the workflow in the same PR.
- `security-auditor`: no auth, secrets, supply-chain, or governance fail-open blocker; diff is one test file and strengthens the pin guard.
- `cursor-specialist-agent`: no developer-workflow/editor blocker; root `.venv` is required in this temporary worktree for direct pytest/pre-commit-style execution.
- `web-research-agent`: no external/action-version blocker; no GitHub review threads exist; CodeRabbit quota skip is a governance caveat, not no-actionable review proof.

## Premortem Finding Closure
- PM-1945-001 missing mapping/body keeps Phase2 and merge-readiness red: FIXED by this artifact and the PR body mirror update.
Evidence: `docs/review/PR_1945_FIXED_MAPPING.md`; planned live PR body sections `## Lane Start Provenance`, `## Experiment Runner Evidence`, `## Discussion Thread Pass`, `### Fixed in Commit Mapping`, and `## Merge Readiness`.
- PM-1945-002 CodeRabbit skipped-review status could be mistaken for substantive no-actionable proof: NOT-A-BUG for code, governance caveat remains.
Evidence: GitHub PR comment from `coderabbitai` says review limit/rate limit was reached. This artifact does not claim CodeRabbit produced a substantive no-actionable review.
- PM-1945-003 stale/cancelled CI could be mistaken for current-head truth: FIXED by requiring current-head CI parity after the governance push.
Evidence: previous current-head failures were Phase2/mapping-only; stale cancelled runs are not used as readiness proof.
- PM-1945-004 local worktree `.venv` absence could produce false local failures: FIXED by running local gates through the root repo virtualenv with absolute `VENV_PYTHON` / `DEV_PYTHON`.
Evidence: focused pytest and `make validate-changed` passed through `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python`.
- PM-1945-005 full `make verify` could exceed operator machine budget or be misclaimed: NOT-A-BUG with operator-approved machine-heavy deferral.
Evidence: full `make verify` is intentionally not run for this PR; no full-suite local pass is claimed.

## Codex Security Diff Scan Evidence
- Report: `/tmp/codex-security-scans/pr-1945-sha-pin-governance/60e5b91ddc29_20260612T122434Z_mbase/report.md`
- HTML: `/tmp/codex-security-scans/pr-1945-sha-pin-governance/60e5b91ddc29_20260612T122434Z_mbase/report.html`
- Result: no reportable findings.
- Coverage: generated source-like worklist was empty because the PR changes only `tests/test_python_supply_chain_controls.py`; the changed test-only surface was manually reviewed and recorded in `/tmp/codex-security-scans/pr-1945-sha-pin-governance/60e5b91ddc29_20260612T122434Z_mbase/artifacts/02_discovery/work_ledger.jsonl`.
- Validator: `python3 .../codex-security/0.1.8/scripts/validate_report_format.py --report-md /tmp/codex-security-scans/pr-1945-sha-pin-governance/60e5b91ddc29_20260612T122434Z_mbase/report.md` PASS.

## Bot / Review Status
- Review threads: GraphQL `reviewThreads(first:100)` returned `[]` on the pre-governance code head `60e5b91ddc29452f74d24f4541c41261279ad676`; final current-head recheck is required before merge.
- Sourcery: `COMMENTED`, no actionable thread found; review text says the changes look good.
- Cubic: `COMMENTED`, review text says no issues found across 1 file.
- CodeRabbit: substantive review on head `2fddc7244159811c5cac24355f2202b4a573ffa2` produced a walkthrough and one docstring-coverage pre-merge warning; the warning was fixed by adding a docstring to `test_ci_main_full_suite_checkout_uses_pinned_checkout_action`. Final recheck on the follow-up head hit CodeRabbit quota/rate limit again. Coordinator disposition: NOT-A-BUG / external service limitation accepted for this narrow test-only PR after the only substantive CodeRabbit warning was fixed and repo-native current-head gates remain authoritative.
- Codecov: previous current-head comment reported all modified and coverable lines covered; current-head coverage must be rechecked after the final follow-up push.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- No review threads were present to resolve.
- No actionable bot review comments were detected by the current merge-readiness parser; CodeRabbit skipped-review caveat is documented above and is not counted as a substantive review.

## Fixed in Commit Mapping
- No actionable review comments

## Local Validation Evidence
- `python3 scripts/orchestration/check_preflight.py --path tests/test_python_supply_chain_controls.py --path docs/review/PR_1945_FIXED_MAPPING.md` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `python3 scripts/orchestration/task_bootstrap.py --goal "Complete PR #1945 pinned checkout supply-chain regression governance and merge readiness" --task-class pr_governance --path tests/test_python_supply_chain_controls.py --path docs/review/PR_1945_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent security-auditor --pr-phase post_open_review --native-bridge-transport codex-native-subagents` PASS.
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/e4b6587c30a6.json --pretty --pr-phase post_open_review` PASS.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m py_compile tests/test_python_supply_chain_controls.py` PASS.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_python_supply_chain_controls.py::test_ci_main_full_suite_checkout_uses_pinned_checkout_action` PASS.
- `python3 scripts/ci/guard_actions_pin.py --root .` PASS.
- `make validate-changed` PASS with absolute root `.venv` interpreter configuration.
- `pre-commit run --all-files` PASS with `PRE_COMMIT_HOME=/tmp/pre-commit-pr1945`.

## Machine-Heavy Verify Deferral
- Full local `make verify` was not run by explicit operator instruction because this repository has a very large test suite and the machine cannot carry it for this lane.
- This PR uses the operator-approved machine-heavy exception: focused local gates, `make validate-changed`, `pre-commit run --all-files`, current-head CI parity, and strict merge wrapper evidence.
- No response or PR body may claim full local `make verify` passed.

## Merge Readiness
- [ ] Current-head CI terminal success confirmed after the final governance push.
- [x] Full local `make verify` explicitly deferred by operator instruction; no full-suite pass is claimed.
- [x] `pre-commit run --all-files` passes with no uncommitted hook edits after this artifact update.
- [x] `make validate-changed` passes with absolute root `.venv` interpreter configuration.
- [x] PR body Phase2 gate passes against the live PR body.
- [ ] Strict review-thread disposition passes with auth.
- [ ] Strict merge-readiness wrapper passes with auth.
- [ ] CodeRabbit / Sourcery / Cubic / Codex review actionables checked and mapped or dispositioned on the current head.
- [ ] Mandatory wait-window after latest bot/review activity completed.

## Deferred / Follow-ups
- None for the code/test diff.
