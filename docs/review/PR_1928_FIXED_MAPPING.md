# PR 1928 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1928>

## Summary

This PR hardens the design bridge coverage inventory validator so evidence
anchors are normalized once to a repo-relative path before allowed-root and
file-existence checks. It keeps the work bounded to the design inventory
validator, focused regression tests, and required review-governance artifacts.

## Scope

- Reuse one normalized repo-relative evidence path for allowed-root and
  existence checks.
- Reject traversal and absolute evidence anchors, including line-suffix
  traversal shapes.
- Preserve valid repo-local `docs/` evidence anchors.
- Add post-open premortem and fixed-mapping evidence for PR #1928.

## Out of Scope

- No OpenAPI, backend runtime, frontend, iOS, nutrition, LLM/RAG, or release
  behavior changes.
- No semantic-cache, advisory wiki, or product AI runtime changes.
- No full local `make verify`; this lane uses the operator-approved
  machine-heavy exception with focused local gates and current-head CI.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- Notes: Sourcery's two actionable threads are fixed and mapped below.
  CodeRabbit was review-rate limited and left no actionable code finding.
  Cubic reported no issues. Final strict merge-readiness remains pending
  current-head CI, bot state, review-thread resolution verification, and the
  required wait-window.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1928#discussion_r3380639611 -> 7ae591bc19
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1928#discussion_r3380639644 -> 7ae591bc19
Disposition: FIXED
Commit: 7ae591bc19
Evidence: `scripts/design/design_bridge_coverage_inventory.py`; `tests/test_design_bridge_coverage_inventory.py`; `docs/review/PR_1928_PREMORTEM.md`
Reason: Sourcery's review was valid. The fixing commit computes one normalized relative path per evidence anchor, reuses it for allowed-root and file-existence checks, removes the redundant helper API, adds traversal/line-suffix/same-root cases, and adds an absolute repo-local anchor regression.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1928#issuecomment-4659763267
Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1928_FIXED_MAPPING.md`
Reason: CodeRabbit did not run a review because the organization hit its review-rate/credit limit. The comment contains no actionable code, test, documentation, or governance finding for this PR.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1928#pullrequestreview-4458585230
Disposition: NOT-A-BUG
Evidence: Cubic reported "No issues found" across the two PR files at head `32ca43ac68a8de4ab36cf7282eb7b06ed8d67f25`.
Reason: The Cubic review contains no actionable finding to fix or defer.

## Premortem Finding Closure

- PM-1928-001 path normalization drift: FIXED by computing one normalized
  `relative_path` in `_validate_record(...)` and reusing it for both
  allowed-root and existence checks.
- PM-1928-002 negative coverage misses valid and invalid edge pairs: FIXED by
  parameterizing traversal shapes and adding an absolute repo-local anchor
  regression.
- PM-1928-003 governance false readiness: FIXED by adding this artifact,
  recording the machine-heavy validation exception, and keeping merge-readiness
  pending strict current-head evidence.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/ae43c36d4be4.json`
- Role dispatch manifest: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/ae43c36d4be4.json --pretty`
- Declared role order: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> web-research-agent`

## Role-Agent Evidence

- `agent-coordinator`: completed post-open scope/routing pass for packet
  `ae43c36d4be4`; approved narrow implementation to fix Sourcery actionables,
  add mapping/body governance, and use focused gates.
- `qa-engineer-agent`: completed post-open QA pass; requested an absolute
  repo-local evidence-anchor regression. Fixed in `7ae591bc19`.
- `bug-hunter`: completed post-open regression pass; found no blocker after the
  focused code/test fix.
- `security-auditor`: completed post-open security pass; found no remaining
  path traversal, absolute-path, secret, auth, quota, or fail-open blocker.
- `cursor-specialist-agent`: completed post-open governance pass; identified
  missing Codex Security / pulseplate-pr-review / mapping / body evidence as
  blockers to close before readiness.
- `web-research-agent`: completed no-research-required pass; no external
  research was needed for stdlib `pathlib` repo-local validation.
- Codex Security diff scan / finding discovery: completed side-effect-free
  two-file review under
  `/tmp/codex-security-scans/BMI-App_2025_clean/32ca43ac6_pr1928_two_file_20260612T122739Z`;
  `raw_candidates.jsonl` is empty and `report.md` / `report.html` report no
  findings.
- `pulseplate-pr-review`: completed side-effect-free dry-run report at
  `/tmp/pr1928_review_report_bounded.md`.
  - Disposition: NOT-A-BUG
  - Evidence: the dry-run large-diff note comes from two-dot historical branch
    divergence; GitHub PR files list only
    `scripts/design/design_bridge_coverage_inventory.py` and
    `tests/test_design_bridge_coverage_inventory.py` before this local
    governance update, while local triple-dot diff for the fixing head contains
    only `docs/review/PR_1928_PREMORTEM.md`,
    `scripts/design/design_bridge_coverage_inventory.py`, and
    `tests/test_design_bridge_coverage_inventory.py`.
  - Gate: `make validate-changed` passed with `50 passed`.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/artifacts/orchestration/experiments/pr_1928_oracle_packet.json`
- Artifact: `artifacts/orchestration/experiments/results/pr_1928_oracle_result.json`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution: `commit_decision`
- `shared_tree_untouched=true`
- `promotion_ready=false`
- `coauthor_required=true`
- Co-author trailer used in `7ae591bc19`: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
- Oracle commands:
  - `python3 scripts/orchestration/check_preflight.py --path scripts/design/design_bridge_coverage_inventory.py --path tests/test_design_bridge_coverage_inventory.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `python3 -m pytest -q tests/test_design_bridge_coverage_inventory.py`
  - `python3 scripts/design/design_bridge_coverage_inventory.py validate docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json`

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_preflight.py --path scripts/design/design_bridge_coverage_inventory.py --path tests/test_design_bridge_coverage_inventory.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py ...` generated packet `artifacts/orchestration/task_packets/ae43c36d4be4.json`.
- PASS: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/ae43c36d4be4.json --pretty`
- PASS: `python3 -m black --check scripts/design/design_bridge_coverage_inventory.py tests/test_design_bridge_coverage_inventory.py`
- PASS: `python3 -m pytest -q tests/test_design_bridge_coverage_inventory.py` (`50 passed`)
- PASS: `python3 -m py_compile scripts/design/design_bridge_coverage_inventory.py tests/test_design_bridge_coverage_inventory.py`
- PASS: `python3 scripts/design/design_bridge_coverage_inventory.py validate docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json`
- PASS: `git diff --check`
- PASS: `make validate-changed` (`50 passed`)
- PASS: `pre-commit run --all-files`
- PASS: commit hook chain for `7ae591bc19`, including Black, Ruff, Bandit
  changed files, backend changed-file tests, and commit message validation.

## Machine-Heavy Verify Exception

Full local `make verify` is operator-deferred for this lane because it runs the
machine-heavy project-wide suite. This PR uses focused local gates,
`make validate-changed`, `pre-commit run --all-files`, and current-head GitHub
CI as the heavy signal before any merge-readiness claim.

## Merge Readiness

Not claimed.

Required before merge readiness:

- Push `7ae591bc19` and this mapping artifact to the PR branch.
- Update the PR body Phase2 mirror.
- Resolve mapped Sourcery review threads only after this artifact exists on the
  PR branch.
- Run strict review-thread disposition and merge-readiness checks with auth.
- Confirm current-head required CI and external bot state have no pending jobs
  or actionable comments.
- Observe the mandatory wait-window after the latest bot/review activity.
