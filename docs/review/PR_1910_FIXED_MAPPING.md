# PR 1910 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1910>

## Summary

This PR closes a subprocess absolute-binary guard bypass where a latest
self-referential assignment such as `cmd = cmd` or `args = args` could hide an
older unsafe `python` or `git` assignment. The follow-up fix in this lane also
preserves safe overwrite behavior when a no-op self assignment follows
`sys.executable`, including branch-dependent no-op assignments.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/d4a709519a5f.json`
- Dispatch manifest: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/d4a709519a5f.json --pretty`
- Required role order executed: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1910#pullrequestreview-4453295473
Disposition: NOT-A-BUG
Evidence: `. .venv/bin/activate && pytest -q tests/guards/test_subprocess_uses_absolute_binaries.py` passed with 36 tests; Codex Security diff scan found no reportable findings; `security-auditor` and `architecture-specialist` found no blockers after the local follow-up fix.
Reason: Sourcery's caching, helper-extraction, and comment suggestions are valid maintainability feedback, but not required for this narrow security guard regression. The concrete correctness issue found during role review was fixed separately in commit `f5df2c4fc`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1910#pullrequestreview-4476444708 -> 3fe8c0453
Disposition: FIXED
Evidence: removed the shadowed local `resolved` declarations from `_resolve_binary_expr` and `_resolve_argv_binary`; `. .venv/bin/activate && pytest -q tests/guards/test_subprocess_uses_absolute_binaries.py` passed with 36 tests.
Reason: CodeRabbit's low-value nitpick was valid and stayed inside the already-touched guard test file.

## Role Review Findings

- `agent-coordinator`: NOT-A-BUG. Scope remains narrow: the PR code surface is
  `tests/guards/test_subprocess_uses_absolute_binaries.py`, and the original CI
  blocker was missing governance evidence, not a product/runtime change.
- `qa-engineer-agent`: NOT-A-BUG. The original self-assignment bypass tests
  cover both binary-variable and argv-variable forms and preserve the safe
  overwrite behavior.
- `bug-hunter`: FIXED in `f5df2c4fc`. The role found a P1 false-positive where
  safe overwrite followed by no-op self assignment could resurrect an older
  unsafe literal. The fix rewinds resolution before self-cycle assignments
  rather than scanning past definite safe overwrites, and adds regressions for
  direct, wrapped, and branch-dependent self assignments.
- `security-auditor`: NOT-A-BUG. The residual branch-dependent conservative
  false-positive was fixed locally; unsafe self assignment still flags and safe
  `sys.executable` overwrite remains allowed.
- `architecture-specialist`: NOT-A-BUG. The fix stays within the policy guard
  file, does not touch product runtime or contracts, and avoids unrelated
  refactor.

## Codex Security Diff Scan

- Scan directory: `/tmp/codex-security-scans/BMI-App_2025_clean/pr1910_guard_20260611T054628Z`
- Markdown report: `/tmp/codex-security-scans/BMI-App_2025_clean/pr1910_guard_20260611T054628Z/report.md`
- HTML report: `/tmp/codex-security-scans/BMI-App_2025_clean/pr1910_guard_20260611T054628Z/report.html`
- Result: No reportable security findings.
- Evidence: one diff-scoped row, `tests/guards/test_subprocess_uses_absolute_binaries.py`, has a completion receipt in `artifacts/02_discovery/work_ledger.jsonl`; `raw_candidates.jsonl` is empty.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-f22d977e7d7b.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-f22d977e7d7b.json`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution: `fixed_mapping_review`
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- `promotion_ready=false`
- `coauthor_required=true`
- Co-author reason: Oracle-only guard validation shaped PR #1910 fixed-mapping evidence and commit readiness.
- Oracle commands:
  - `pytest -q tests/guards/test_subprocess_uses_absolute_binaries.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze --path tests/guards/test_subprocess_uses_absolute_binaries.py --path docs/review/PR_1910_FIXED_MAPPING.md`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `. .venv/bin/activate && pytest -q tests/guards/test_subprocess_uses_absolute_binaries.py`
- PASS: `git diff --check -- tests/guards/test_subprocess_uses_absolute_binaries.py`
- PASS: commit hooks for `f5df2c4fc`, including changed-file backend tests.
- PASS: commit hooks for `a491250b0`, docs-only with no changed-file backend tests.
- PASS: `make validate-changed`
- PASS: commit hooks for `3fe8c0453`, including changed-file backend tests.
- PASS: `. .venv/bin/activate && pytest -q tests/guards/test_subprocess_uses_absolute_binaries.py` after the CodeRabbit cleanup.
- OPERATOR-DEFERRED: full local `make verify` was not run; the operator
  explicitly limited local validation to `make validate-changed` because full
  verify runs the large project suite.
- ATTEMPTED / LOCAL LIMIT: `pre-commit run --all-files` did not complete
  locally because the full-repo Bandit hook was terminated with exit `-15`
  after warnings and no finding. Do not claim full pre-commit green from local
  evidence; current-head CI/pre-commit parity remains required before merge.
- PENDING: current-head CI after pushing the follow-up commits.
- PENDING: strict merge readiness with `check_merge_ready.py --require-auth`.

## Risks / Rollback

- Risk: overly permissive self-cycle handling could hide unsafe subprocess
  tokens. Mitigation: unsafe binary and argv self-assignment tests still assert
  one violation each.
- Risk: overly conservative cycle fallback could block safe subprocess calls.
  Mitigation: safe overwrite tests cover direct, wrapped, and branch-dependent
  self assignments.
- Rollback: revert `f5df2c4fc` and this mapping commit; the original PR head
  remains a test-only guard change.

## Deferred / Follow-ups

- None for PR #1910.
