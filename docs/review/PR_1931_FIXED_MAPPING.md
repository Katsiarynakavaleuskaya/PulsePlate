# PR #1931 Fixed in Commit Mapping

## Summary

This PR restores the BMI/WHR guard's camelCase waist-to-hip threshold detection
while keeping the design-scorecard false-positive boundary intact. The change is
test/governance-only: no runtime BMI logic, backend route, OpenAPI, frontend,
iOS, nutrition, or medical-claim behavior changes.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/5091fc31e50b.json`
- Packet: `artifacts/orchestration/task_packets/16832e753f0d.json`
- Role dispatch: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/16832e753f0d.json --pretty --pr-phase post_open_review`
- Role order preserved: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> web-research-agent`
- Post-open remediation note: PR #1931 was already open before this closeout pass; this evidence records the required post-open governance recovery and does not claim pre-open execution.

## Role Review Evidence

- `agent-coordinator`: scope locked to `tests/test_no_bmi_math_outside_core.py` and `docs/review/PR_1931_FIXED_MAPPING.md`; no runtime, contract, backend, frontend, iOS, or nutrition behavior changes allowed.
- `qa-engineer-agent`: required focused regex coverage for `waistHipRatioThreshold`, `waistToHipRatioThreshold`, `normalized_score`, and unrelated waist camelCase negatives before wider gates.
- `bug-hunter`: reviewed false-green risks from overlapping waist-to-hip regex alternatives and stale PR-body/mapping governance; fix is code/test first, then mapping.
- `security-auditor`: no auth, secrets, network, subprocess, LLM, quota, rate-limit, data migration, or production runtime surfaces touched; security risk is limited to guard weakening/false positives.
- `cursor-specialist-agent`: verified the closeout uses repo-native bootstrap/dispatch artifacts and keeps local `artifacts/` provenance gitignored.
- `web-research-agent`: no external research required; live GitHub PR metadata, CI logs, and bot comments are the only external signals used for this closeout.

## Premortem Closure

- Finding: Regex refactor could accidentally weaken WHR threshold detection.
  - Disposition: FIXED
  - Evidence: `tests/test_no_bmi_math_outside_core.py` retains `waistHipRatioThreshold`, adds/keeps `waistToHipRatioThreshold`, and focused `bmi_thresholds_re` tests pass.
- Finding: Refactor could reintroduce the design scorecard `normalized_score >= 0.85` false positive.
  - Disposition: FIXED
  - Evidence: `tests/test_no_bmi_math_outside_core.py` keeps explicit normalized-score negatives and the focused test run passes.
- Finding: Mapping-only governance could leave Sourcery's regex maintainability feedback unresolved.
  - Disposition: FIXED
  - Evidence: `_BMI_THRESHOLD_CONTEXT` now uses shared identifier/camel-case waist-to-hip subpatterns instead of duplicated overlapping `waist.*hip` alternatives.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-a1732095b657.json`
- Status: accepted
- Mode: `oracle_only_governance_reviewer`
- Mutation boundary: `mutated_paths=[]`, `promotion_ready=false`
- Contribution: `fixed_mapping_review`
- Co-author: required because the accepted artifact shaped PR #1931 fixed-mapping and merge-readiness closeout.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- GraphQL review-thread check found no inline review threads on PR #1931.
- Sourcery review-level actionable feedback is fixed and mapped below.
- Cubic reported no issues on the original one-file diff.
- CodeRabbit was rate-limited/skipped on the original head and must be rechecked after the follow-up push; no CodeRabbit code finding existed at the time this artifact was created.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1931#pullrequestreview-4458583036 -> bf82fec0eb7dfbacbab99b16aa74cd002d2356f0

Disposition: FIXED
Commit: bf82fec0eb7dfbacbab99b16aa74cd002d2356f0
Evidence: `tests/test_no_bmi_math_outside_core.py` factors shared BMI/WHR identifier context, consolidates camelCase waist-to-hip matching through `_WAIST_TO_HIP_CAMEL_CONTEXT`, keeps `waistHipRatioThreshold` and `waistToHipRatioThreshold` positives, and adds an unrelated waist camelCase negative. Focused validation: `.venv/bin/python -m pytest -q tests/test_no_bmi_math_outside_core.py -k "bmi_thresholds_re"` (`5 passed`).

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path tests/test_no_bmi_math_outside_core.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/orchestration/task_bootstrap.py --goal "PR 1931 BMI WHR guard post-open governance closeout" --task-class pr_governance --path tests/test_no_bmi_math_outside_core.py --requested-agent agent-coordinator --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent security-auditor --pr-phase post_open_review` - PASS, packet `artifacts/orchestration/task_packets/5091fc31e50b.json`
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/5091fc31e50b.json --pretty --pr-phase post_open_review` - PASS, role order `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor`
- `python3 scripts/orchestration/task_bootstrap.py --goal "PR 1931 BMI WHR guard post-open governance closeout" --task-class pr_governance --path tests/test_no_bmi_math_outside_core.py --path docs/review/PR_1931_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent security-auditor --pr-phase post_open_review` - PASS, packet `artifacts/orchestration/task_packets/16832e753f0d.json`
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/16832e753f0d.json --pretty --pr-phase post_open_review` - PASS, role order `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> web-research-agent`
- `.venv/bin/python -m py_compile tests/test_no_bmi_math_outside_core.py` - PASS via root-repo venv fallback from the isolated PR worktree
- `.venv/bin/python -m pytest -q tests/test_no_bmi_math_outside_core.py -k "bmi_thresholds_re"` - PASS (`5 passed`) via root-repo venv fallback from the isolated PR worktree
- `.venv/bin/python -m pytest -q tests/test_no_bmi_math_outside_core.py` - PASS (`28 passed`) via root-repo venv fallback from the isolated PR worktree
- `make validate-changed` - PASS with repo `.venv` fallback, selected `tests/test_no_bmi_math_outside_core.py` and passed all 28 tests
- `pre-commit run --all-files` - PASS after installing ignored local `frontend/node_modules/`; frontend hook passed under the normal hook command after the local dependency install
- `npm run test:precommit -- --maxWorkers=1` - PASS (`91 passed`, `765 passed`, `1 skipped`) as resource-diagnostic evidence for the earlier local `frontend-tests` `SIGKILL`
- `GH_TOKEN=$(gh auth token) python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 1931 --require-auth` - PASS (`OK: No resolved review threads found`)
- `python3 scripts/orchestration/experiment_bootstrap.py ... --runner-mode oracle_only_governance_reviewer` - PASS, packet `artifacts/orchestration/experiments/exp-a1732095b657.json`
- `python3 scripts/orchestration/experiment_runner.py --packet artifacts/orchestration/experiments/exp-a1732095b657.json --contribution-kind fixed_mapping_review --coauthor-required --coauthor-reason "Accepted oracle evidence shaped PR #1931 fixed-mapping and merge-readiness closeout."` - PASS, accepted result `artifacts/orchestration/experiments/results/exp-a1732095b657.json`
- Codex Security diff scan / finding discovery - PASS, no findings; reviewed touched test/docs surfaces, generated the required markdown/HTML scan report, and found no auth, secrets, network, subprocess, LLM, quota, persistence, deploy, or runtime trust-boundary changes.
- Operator exception: full local `make verify` is explicitly out of scope for this closeout after operator direction on 2026-06-11; use `make validate-changed`, focused/full guard tests, pre-commit, strict PR/governance checks, and current-head CI parity. A local exploratory `make verify` attempt reached full `mypy` and failed only in unrelated semantic-cache files outside the PR diff (`core/ai/semantic_cache_offline_admission_runner.py`, `core/ai/semantic_cache_shadow_admission_harness.py`); PR #1931 diff is limited to `tests/test_no_bmi_math_outside_core.py` and this mapping artifact.

## Merge Readiness

- [ ] Current-head CI terminal success confirmed after the follow-up push.
- [ ] CodeRabbit / Sourcery / Cubic review actionables checked and mapped.
- [x] Strict review-thread disposition passes with auth.
- [ ] Strict merge-readiness guard passes with auth.
- [ ] Mandatory wait-window after latest bot/review activity completed.
- [x] Operator-approved machine-heavy exception documented; required narrow gates pass locally, current-head CI parity pending after push.

## Deferred / Follow-ups

- None.
