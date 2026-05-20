# PR #1777 - Fixed in Commit Mapping

**Scope:** Philosophy Epic V2 PR-2 admission policy spec generator / claim-family
oracle.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 92083c466
Evidence: CI/docs routing now passes the Philosophy admission policy JSON, schema, and generated oracle fixture into Docs Phase1 gates, and `tests/test_ci_workflow_pr_size_governance_contract.py` guards the workflow contract; this closes the Codex/Cubic finding that policy-only diffs could skip the new Phase1 checks.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#pullrequestreview-4328165585 -> 92083c466
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#discussion_r3273668187 -> 92083c466
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#discussion_r3273691727 -> 92083c466

Disposition: FIXED
Commit: 50de520c7
Evidence: Bot findings from Sourcery, CodeRabbit, and cubic were closed in code/docs/tests: detector-label mismatch errors include expected/actual sets; oracle drift guidance no longer hard-codes the default policy filename; allowed oracle cases fail on any downstream false positive; merged PR-1 ledger state and PR-2 target PR are synced; Philosophy agent guidance names the exact oracle fixture path; oracle fixture write mode is blocked when validation already failed. Focused local proof: `python3 scripts/ci/check_semantic_cache_gate.py --check-philosophy-admission-oracle-drift`; `.venv/bin/python -m pytest -q tests/test_philosophy_admission_policy_oracle.py tests/test_ci_workflow_pr_size_governance_contract.py`; `git diff --check`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#discussion_r3273641024 -> 50de520c7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#discussion_r3273641038 -> 50de520c7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#pullrequestreview-4328170555 -> 50de520c7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#discussion_r3273672603 -> 50de520c7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#discussion_r3273672626 -> 50de520c7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#pullrequestreview-4328193097 -> 50de520c7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#discussion_r3273691732 -> 50de520c7

Disposition: NOT-A-BUG
Evidence: Sourcery's review-level extraction comments are advisory refactor feedback, not correctness defects for this PR-2 governance/test-infrastructure scope. The policy/oracle logic intentionally remains in the existing semantic-cache gate entrypoint for this PR so the new guard cannot drift from the existing gate-closed admission checker. The root loop risk is addressed by policy-as-data, generated oracle drift checks, docs/CI wiring, and agent guidance; broader Experiment Runner oracle-manifest or helper-module extraction belongs in a separate coordinator-owned lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1777#pullrequestreview-4328132580

## Role-Agent / Premortem Pass

- `agent-coordinator` start gate - completed before implementation through
  `check_preflight.py` and `task_bootstrap.py --pr-phase pre_open`.
- `pulseplate-premortem-risk-review` - completed and closed in
  `docs/orchestration/PHILOSOPHY_EPIC_V2_PR2_POLICY_ORACLE_PACKET_2026-05-20.md`;
  decision: proceed with fixes captured as `FIXED`.
- `architecture-specialist` - completed; policy-as-data, schema parity, drift
  checks, and no-runtime boundaries are implemented.
- `philosophy-agent` - completed; claim-family semantics now live in canonical
  policy data with temporal/modal dimensions and allowed negative controls.
- `qa-engineer-agent` - pre-open pass completed; post-open pass is running after
  PR creation.
- `qa-engineer-agent` post-open finding - FIXED in commit `6120393bd`.
  Evidence: `scripts/ci/check_semantic_cache_gate.py` now generates modal and
  temporal cross-product oracle cases; `tests/test_philosophy_admission_policy_oracle.py`
  rejects the five false-green examples from QA; focused pytest passed locally.
- `security-auditor` - pre-open pass completed; post-open diff-scoped security
  scan is running after PR creation.
- `security-auditor` / `codex-security` style post-open diff scan - completed;
  no security-actionable findings. Evidence: scan checked path/write primitives,
  JSON-driven regex injection, ReDoS shape, CI weakening, subprocess/network
  additions, runtime activation drift, and secrets/baseline drift; `git diff
  --check`, semantic-cache gate drift, docs phase gate, `make validate-changed`,
  and `pre-commit run --all-files` passed locally.
- `bug-hunter` - pre-open pass completed; post-open pass is pending after QA per
  role order.
- `bug-hunter` post-open provider-approval finding - FIXED in commit
  `92083c466`. Evidence:
  `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json`
  adds Redis/GPTCache/provider-backed approval predicates and seed regressions,
  the oracle fixture was regenerated, and
  `tests/test_philosophy_admission_policy_oracle.py` now rejects those examples.
- `bug-hunter` post-open CI-wiring finding - FIXED in commit `92083c466`.
  Evidence: `.github/workflows/ci.yml` now passes the policy JSON and generated
  oracle fixture into Docs Phase1 gates and includes
  `tests/test_philosophy_admission_policy_oracle.py` in route contract safety
  suites; `tests/test_ci_workflow_pr_size_governance_contract.py` guards both
  workflow contracts.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --mode analyze --path docs/orchestration --path docs/roadmap --path scripts/ci --path tests --path .cursor/agents`
  - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `python3 scripts/ci/check_semantic_cache_gate.py --check-philosophy-admission-oracle-drift`
  - PASS.
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/PHILOSOPHY_EPIC_V2_PR2_POLICY_ORACLE_PACKET_2026-05-20.md docs/roadmap/BACKLOG_LEDGER.md docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.schema.json tests/fixtures/orchestration/philosophy_admission_claim_oracle.json`
  - PASS.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_philosophy_admission_policy_oracle.py tests/test_philosophy_semantic_cache_admission_contract.py tests/test_semantic_cache_gate.py`
  - PASS.
- `DEV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed`
  - PASS.
- `pre-commit run --all-files` - PASS.
- Pre-push hooks - PASS, including mypy, pip-audit, backend tests, full-repo
  bandit, and docker build test.

## Current CI / Review State

- Initial PR #1777 current-head CI is not merge-ready. `PR Body Phase2 gates`
  failed before this canonical mapping artifact existed.
- `pr_scope_guard` failed through PR size governance because this governance/test
  infrastructure PR is above 800 changed lines and needs an explicit PR-body
  `## Split Justification`.
- Bot review is still in progress. This artifact must be updated if CodeRabbit,
  Sourcery, Cubic, Codex, or human review adds actionable comments.

## Machine-Heavy Gate Note

Full local `make verify` is not claimed for this PR. The user requested
`make validate-changed` rather than full `make verify`; merge readiness remains
blocked until current-head CI, post-open role checks, review-thread disposition,
fixed mapping/body mirror, and strict merge wrapper pass.
