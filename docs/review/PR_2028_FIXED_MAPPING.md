# PR 2028 - Fixed in Commit Mapping

## Lane Start Provenance
- Packet: `artifacts/orchestration/task_packets/bd82ec50a38e.json`
- Post-open packet: `artifacts/orchestration/task_packets/32206ba2f2fe.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `feat/orchestration-review-fallback-learning-loop`
- Current base: `origin/main` at `80cb3b3f7c86947102a7ce97233d7993f2eb4769`
- Final pushed head: mirrored in the PR body after push.

## Discussion Thread Pass
- [x] Discussion-thread pass completed for known CodeRabbit/Sourcery review batches.
- [x] Fixed in commit mapping refreshed after the `origin/main` rebase.
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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#pullrequestreview-4585161591 -> 8447963db4c9cd7690b9fea779625f8abaca5b9c
Disposition: FIXED
Commit: 8447963db4c9cd7690b9fea779625f8abaca5b9c
Evidence: `tests/test_install_locked_python_requirements.py` uses `sys.executable` for direct-proxy fallback tests so runtime tag selection stays in-process. The full focused test file passed after the rebase.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485646667 -> 29bd27eb4f46bf87b5d36062853b9e852c601e8d
Disposition: FIXED
Commit: 29bd27eb4f46bf87b5d36062853b9e852c601e8d
Evidence: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md` lists the machine-consumed `.v1` JSON contracts and keeps scoped validation as narrative-only advisory policy.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485646668 -> 29bd27eb4f46bf87b5d36062853b9e852c601e8d
Disposition: FIXED
Commit: 29bd27eb4f46bf87b5d36062853b9e852c601e8d
Evidence: `scripts/orchestration/agent_lesson_promoter.py` validates loaded records through `validate_agent_learning_record()` before proposal emission; `tests/test_agent_learning_loop.py` covers file-load validation and extra-property rejection.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485646669 -> 29bd27eb4f46bf87b5d36062853b9e852c601e8d
Disposition: FIXED
Commit: 29bd27eb4f46bf87b5d36062853b9e852c601e8d
Evidence: `scripts/orchestration/skill_router.py` avoids generic review-oracle routing and `tests/test_skill_router.py` proves generic Experiment Runner oracle text does not route `pulseplate-review-pattern-oracles`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755463 -> 494a6e223b953334ac571adaa90b2bba3e0a40e8
Disposition: FIXED
Commit: 494a6e223b953334ac571adaa90b2bba3e0a40e8
Evidence: `scripts/orchestration/agent_learning_loop.py` redacts token-family values before generic token handling; `tests/test_agent_learning_loop.py` covers `ghs_` redaction.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755465 -> 27166c4238dc0add9ad2fcafb170d22cffbf98bc
Disposition: FIXED
Commit: 27166c4238dc0add9ad2fcafb170d22cffbf98bc
Evidence: `scripts/orchestration/agent_lesson_promoter.py` handles unreadable record files as malformed input errors; `tests/test_agent_learning_loop.py` covers the CLI failure path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755469 -> 2bf43d03f6013d63566b1efb8f5a56d10e999da8
Disposition: FIXED
Commit: 2bf43d03f6013d63566b1efb8f5a56d10e999da8
Evidence: `scripts/orchestration/pr_review_context.py` emits repo-relative fixed-mapping evidence; `tests/test_pr_review_context.py` verifies local workspace paths are not emitted.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755472 -> 2bf43d03f6013d63566b1efb8f5a56d10e999da8
Disposition: FIXED
Commit: 2bf43d03f6013d63566b1efb8f5a56d10e999da8
Evidence: `scripts/orchestration/pr_review_context.py` evaluates fixed-mapping PR-diff membership when diff data is available; `tests/test_pr_review_context.py` covers missing-SHA parity handling.

## Role And Review Findings
- `agent-coordinator` post-open pass: BLOCK on stale mapping, local-path evidence, obsolete scan-head evidence, and a non-worktree `git` context false negative.
Disposition: FIXED for mapping/local-path evidence by this refresh.
Evidence: This file records the current base `80cb3b3f7c86947102a7ce97233d7993f2eb4769`, uses only repo-relative evidence paths, and makes no current-head security-scan claim. The canonical preflight was rerun successfully with explicit `GIT_DIR` and `GIT_WORK_TREE` for the linked worktree.

- `qa-engineer-agent` post-open pass: BLOCK on stale mapping head/base references and stale PR body mirror.
Disposition: FIXED for mapping evidence by this refresh. PR body mirror remains pending until after push so it can cite the actual remote head.
Evidence: This mapping no longer embeds a self-stale local-head SHA and records the latest verified base `80cb3b3f7c86947102a7ce97233d7993f2eb4769`.

- `bug-hunter` post-open pass: BLOCK on an over-specific local task-packet inventory sentence in Experiment Runner evidence.
Disposition: FIXED.
Evidence: The Experiment Runner note now limits itself to the relevant fact: no current-head Experiment Runner result artifact is present locally.

- `security-auditor` post-open pass: BLOCK on raw local path exposure in unreadable learning-record errors and fixed-mapping context JSON.
Disposition: FIXED.
Evidence: `scripts/orchestration/agent_lesson_promoter.py` emits a generic unreadable-record error for `OSError`, and `scripts/orchestration/pr_review_context.py` emits only `repo_path` for fixed-mapping artifacts. `tests/test_agent_learning_loop.py` and `tests/test_pr_review_context.py` assert local `tmp_path` and `/etc/...` paths are absent from CLI errors and context payloads.

## Premortem Evidence
- Disposition: FIXED
- Evidence: `scripts/orchestration/agent_learning_loop.py`, `tests/test_agent_learning_loop.py`, `docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md`, `scripts/orchestration/pr_review_report.py`, `tests/test_pr_review_report.py`, and `docs/orchestration/SCOPED_VALIDATION_POLICY.md` cover learning-record validation, degraded-source advisory semantics, and scoped-validation boundaries.

## Experiment Runner Evidence
- Status: historical accepted oracle-only evidence from the original lane.
- Current-head authority: not claimed after the latest rebase.
- Note: no current-head Experiment Runner result artifact is present locally to cite as current-head evidence.

## Validation Evidence
- `python3 scripts/orchestration/check_preflight.py` with explicit linked-worktree `GIT_DIR` and `GIT_WORK_TREE`.
- `python3 scripts/orchestration/check_agent_consistency.py` with explicit linked-worktree `GIT_DIR` and `GIT_WORK_TREE`.
- `python -m py_compile` for changed orchestration helpers and CLIs.
- Focused pytest for review oracles, review-source status, PR review context/reporting, skill routing, task bootstrap, skill install/mirror, symlink integrity, agent learning loop, CI workflow governance, installer fallback tests, authz contracts, route-family bootstrap, runtime-env canonicalization, test router, and OpenAPI determinism.
- `make validate-changed`.
- `pre-commit run --all-files` with explicit linked-worktree `GIT_DIR` and `GIT_WORK_TREE`.
- `git diff --check origin/main...HEAD`.
- `git ls-remote origin refs/heads/main refs/pull/2028/head` confirmed `main` at `80cb3b3f7c86947102a7ce97233d7993f2eb4769` before this mapping refresh.

## Security Evidence
- No new Codex Security scan was started after the latest rebase, per operator instruction to stop repeated scans unless the surface materially changes.
- Historical Codex Security evidence remains advisory only for older heads and is not used as current-head merge authority.
- Current diff remains offline governance/tooling plus CI/test hardening; no product runtime writes, GitHub posting, thread resolution, branch-protection mutation, provider calls, or auto-merge authority are introduced.

## Merge Readiness
- Not claimed.
- Pending: remaining post-open role passes, `pulseplate-pr-review`, push of the rebased branch, current-head CI, bot/review-thread disposition, strict merge-readiness checks, and the required wait-window.
