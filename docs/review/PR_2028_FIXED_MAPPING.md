# PR 2028 - Fixed in Commit Mapping

## Lane Start Provenance
- Packet: `artifacts/orchestration/task_packets/bd82ec50a38e.json`
- Post-open packet: `artifacts/orchestration/task_packets/32206ba2f2fe.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `feat/orchestration-review-fallback-learning-loop`
- Current base: `origin/main` at `c1dc21f45f615b3262d30cf32e4077920f10a16e`
- Current PR head: GitHub current-head checks are the source of truth after each push.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Known CodeRabbit/Sourcery review batches and post-open role findings are dispositioned below.
- Fixed in commit mapping was refreshed after the `origin/main` rebase.
- [ ] Current-head CI, bot/review state, strict merge-readiness checks, and wait-window are still pending.

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#pullrequestreview-4584656910
Disposition: NOT-A-BUG
Evidence: `docs/orchestration/AGENT_LEARNING_LOOP.md` and `docs/orchestration/REVIEW_PATTERN_ORACLES.md` keep the helpers proposal-only, offline, and without runtime or merge authority.
Reason: The Sourcery item was an advisory maintainability signal, not a correctness, security, or runtime-authority defect in this scoped governance contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#pullrequestreview-4584666854
Disposition: NOT-A-BUG
Evidence: This CodeRabbit aggregate review is a container for inline findings. The actionable inline findings are mapped below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#pullrequestreview-4584826178
Disposition: NOT-A-BUG
Evidence: This CodeRabbit aggregate review is a container for inline findings. The actionable inline findings are mapped below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#pullrequestreview-4585161591 -> 12464406ba7703f6591bb3c3a8f9376425b51e43
Disposition: FIXED
Commit: 12464406ba7703f6591bb3c3a8f9376425b51e43
Evidence: `tests/test_install_locked_python_requirements.py` uses `sys.executable` for direct-proxy fallback tests so runtime tag selection stays in-process. The full focused test file passed after the rebase.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485646667 -> 63500759f884b458c670f99a55e3d2ec8f205c03
Disposition: FIXED
Commit: 63500759f884b458c670f99a55e3d2ec8f205c03
Evidence: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md` lists the machine-consumed `.v1` JSON contracts and keeps scoped validation as narrative-only advisory policy.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485646668 -> 63500759f884b458c670f99a55e3d2ec8f205c03
Disposition: FIXED
Commit: 63500759f884b458c670f99a55e3d2ec8f205c03
Evidence: `scripts/orchestration/agent_lesson_promoter.py` validates loaded records through `validate_agent_learning_record()` before proposal emission; `tests/test_agent_learning_loop.py` covers file-load validation and extra-property rejection.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485646669 -> 63500759f884b458c670f99a55e3d2ec8f205c03
Disposition: FIXED
Commit: 63500759f884b458c670f99a55e3d2ec8f205c03
Evidence: `scripts/orchestration/skill_router.py` avoids generic review-oracle routing and `tests/test_skill_router.py` proves generic Experiment Runner oracle text does not route `pulseplate-review-pattern-oracles`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755463 -> 0680eeaf5d004da98b48b443117b77f18c647fe1
Disposition: FIXED
Commit: 0680eeaf5d004da98b48b443117b77f18c647fe1
Evidence: `scripts/orchestration/agent_learning_loop.py` redacts token-family values before generic token handling; `tests/test_agent_learning_loop.py` covers `ghs_` redaction.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755465 -> f333c798484e881b48ba374535dec22df6bee3f8
Disposition: FIXED
Commit: f333c798484e881b48ba374535dec22df6bee3f8
Evidence: `scripts/orchestration/agent_lesson_promoter.py` handles unreadable record files as malformed input errors; `tests/test_agent_learning_loop.py` covers the CLI failure path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755469 -> e459e7daad6ea889b4e8822bd2951585f1709934
Disposition: FIXED
Commit: e459e7daad6ea889b4e8822bd2951585f1709934
Evidence: `scripts/orchestration/pr_review_context.py` emits repo-relative fixed-mapping evidence; `tests/test_pr_review_context.py` verifies local workspace paths are not emitted.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755472 -> e459e7daad6ea889b4e8822bd2951585f1709934
Disposition: FIXED
Commit: e459e7daad6ea889b4e8822bd2951585f1709934
Evidence: `scripts/orchestration/pr_review_context.py` evaluates fixed-mapping PR-diff membership when diff data is available; `tests/test_pr_review_context.py` covers missing-SHA parity handling.

## Role And Review Findings
- `agent-coordinator` post-open pass: BLOCK on stale mapping, local-path evidence, obsolete scan-head evidence, and a non-worktree `git` context false negative.
Disposition: FIXED for mapping/local-path evidence by this refresh.
Evidence: This file records the current base `c1dc21f45f615b3262d30cf32e4077920f10a16e`, uses only repo-relative evidence paths, and makes no current-head security-scan claim. The canonical preflight was rerun successfully with explicit `GIT_DIR` and `GIT_WORK_TREE` for the linked worktree.

- `qa-engineer-agent` post-open pass: BLOCK on stale mapping head/base references and stale PR body mirror.
Disposition: FIXED for mapping evidence by this refresh. PR body mirror remains pending until after push so it can cite the actual remote head.
Evidence: This mapping no longer embeds a self-stale local-head SHA and records the latest verified base `c1dc21f45f615b3262d30cf32e4077920f10a16e`.

- `bug-hunter` post-open pass: BLOCK on an over-specific local task-packet inventory sentence in Experiment Runner evidence.
Disposition: FIXED.
Evidence: The Experiment Runner note now limits itself to the relevant fact: no current-head Experiment Runner result artifact is present locally.

- `security-auditor` post-open pass: BLOCK on raw local path exposure in unreadable learning-record errors and fixed-mapping context JSON.
Disposition: FIXED.
Evidence: `scripts/orchestration/agent_lesson_promoter.py` emits a generic unreadable-record error for `OSError`, and `scripts/orchestration/pr_review_context.py` emits only `repo_path` for fixed-mapping artifacts. `tests/test_agent_learning_loop.py` and `tests/test_pr_review_context.py` assert local `tmp_path` and `/etc/...` paths are absent from CLI errors and context payloads.

- `cursor-specialist-agent` post-open pass: BLOCK on fixed-mapping parity when PR metadata is unavailable but an explicit diff head is provided, and on review-pattern oracle token-family redaction before hashing.
Disposition: FIXED.
Evidence: `scripts/orchestration/pr_review_context.py` compares local mapping evidence against `pr_metadata_head or diff_head`; `scripts/orchestration/review_pattern_oracles.py` redacts `github_pat_...` and full `ghs_...` tokens before fingerprinting. `tests/test_pr_review_context.py` and `tests/test_review_pattern_oracles.py` cover both regressions.

- `architecture-specialist` post-open pass: BLOCK on learning-record validation accepting tampered records, review-source status schema allowing arbitrary strings, and local path leakage in command diagnostics.
Disposition: FIXED.
Evidence: `scripts/orchestration/agent_learning_loop.py` revalidates redacted stored fields and recomputes `dedupe_fingerprint` / `lesson_id`; `docs/orchestration/contracts/review_source_status.v1.json` enumerates statuses in parity with `REVIEW_SOURCE_STATUSES`; `scripts/orchestration/pr_review_context.py` redacts command diagnostics. `tests/test_agent_learning_loop.py`, `tests/test_review_source_status.py`, and `tests/test_pr_review_context.py` cover all three regressions.

- `pulseplate-pr-review` dry-run pass: advisory `note` on large-diff risk above the review-risk threshold.
Disposition: NOT-A-BUG.
Evidence: The rebased dry-run report generated at `2026-06-28T17:01:23Z` reports the same advisory large-diff note over 42 files / 2979 changed lines. PR body records a non-template split justification plus `Operator approval: approved`, `Emergency exception: approved`, and `Privileged scope exception: approved`; PR labels include `scope/operator-approved`, `scope/emergency-approved`, and `scope/privileged-approved`; `python3 scripts/ci/check_pr_size_governance.py --base-sha c1dc21f45f615b3262d30cf32e4077920f10a16e --head-sha HEAD --event-path <tmp event with live PR body and labels>` passed with `PR scope governance: OK (>30 files) because an operator-approved emergency exception is documented.`.
Reason: The large-diff note is valid review-planning signal, but the intentionally broad one-PR governance contract is operator-approved and locally validated by the repository size-governance gate.

## Premortem Evidence
- Disposition: FIXED
- Evidence: `scripts/orchestration/agent_learning_loop.py`, `tests/test_agent_learning_loop.py`, `docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md`, `scripts/orchestration/pr_review_report.py`, `tests/test_pr_review_report.py`, and `docs/orchestration/SCOPED_VALIDATION_POLICY.md` cover learning-record validation, degraded-source advisory semantics, and scoped-validation boundaries.

## Experiment Runner Evidence
- Not applicable: current refresh only repaired Phase2 body and size-governance proof text after rebase; no new Experiment Runner decision input was used.
- Status: historical accepted oracle-only evidence from the original lane.
- Current-head authority: not claimed after the latest rebase.
- Note: no current-head Experiment Runner result artifact is present locally to cite as current-head evidence, and rejected artifacts from other lanes are not reused.

## Validation Evidence
- `python3 scripts/orchestration/check_preflight.py` with explicit linked-worktree `GIT_DIR` and `GIT_WORK_TREE`.
- `python3 scripts/orchestration/check_agent_consistency.py` with explicit linked-worktree `GIT_DIR` and `GIT_WORK_TREE`.
- `python -m py_compile` for changed orchestration helpers and CLIs.
- Focused pytest for review oracles, review-source status, PR review context/reporting, skill routing, task bootstrap, skill install/mirror, symlink integrity, agent learning loop, CI workflow governance, installer fallback tests, authz contracts, route-family bootstrap, runtime-env canonicalization, test router, and OpenAPI determinism.
- `make validate-changed`.
- `pre-commit run --all-files` with explicit linked-worktree `GIT_DIR` and `GIT_WORK_TREE`.
- `git diff --check origin/main...HEAD`.
- `gh api repos/Katsiarynakavaleuskaya/PulsePlate/branches/main --jq .commit.sha` confirmed `main` at `c1dc21f45f615b3262d30cf32e4077920f10a16e` before this mapping refresh.

## Security Evidence
- No new Codex Security scan was started after the latest rebase, per operator instruction to stop repeated scans unless the surface materially changes.
- Historical Codex Security evidence remains advisory only for older heads and is not used as current-head merge authority.
- Current diff remains offline governance/tooling plus CI/test hardening; no product runtime writes, GitHub posting, thread resolution, branch-protection mutation, provider calls, or auto-merge authority are introduced.

## Merge Readiness
- Not claimed.
- Pending: push of the rebased branch, current-head CI, bot/review-thread disposition, strict merge-readiness checks, and the required wait-window.
