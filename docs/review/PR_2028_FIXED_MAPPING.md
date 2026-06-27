# PR 2028 - Fixed in Commit Mapping

## Lane Start Provenance
- Packet: `artifacts/orchestration/task_packets/bd82ec50a38e.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `feat/orchestration-review-fallback-learning-loop`
- Base: `origin/main` at `8625cc178`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#pullrequestreview-4584656910
Disposition: NOT-A-BUG
Evidence: `docs/orchestration/AGENT_LEARNING_LOOP.md` and `docs/orchestration/REVIEW_PATTERN_ORACLES.md` define proposal-only, no-runtime-authority boundaries for the new helpers. The Sourcery review is an advisory maintainability suggestion to consolidate helper import/authority-boundary wording later, not a correctness, security, runtime-authority, or merge-readiness defect in this scoped governance contract.
Reason: The PR intentionally keeps the new contracts and helper metadata self-contained so advisory artifacts remain reviewable without introducing a broader package/import refactor or a hidden single source of runtime authority.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#pullrequestreview-4584666854 -> acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Disposition: FIXED
Commit: acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Evidence: This CodeRabbit aggregate review listed the first review batch; its inline/out-of-diff findings are mapped below and fixed by schema-contract references, full promoter record validation, narrower skill-router oracle matching, and branch-focused promoter CLI tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#pullrequestreview-4584826178 -> acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Disposition: FIXED
Commit: acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Evidence: This CodeRabbit aggregate review listed the second review batch; its inline findings are mapped below and fixed by complete `ghs_` redaction, clean unreadable-file CLI errors, repo-relative fixed-mapping evidence, and SHA-independent fixed-mapping diff membership checks.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485646667 -> acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Disposition: FIXED
Commit: acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Evidence: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md` now lists the machine-consumed `.v1` JSON contracts and explicitly leaves scoped validation as narrative-only advisory policy.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485646668 -> acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Disposition: FIXED
Commit: acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Evidence: `scripts/orchestration/agent_lesson_promoter.py` now validates loaded records through `validate_agent_learning_record()` before proposal emission; `tests/test_agent_learning_loop.py` covers file-load full-contract validation and extra-property rejection.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485646669 -> acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Disposition: FIXED
Commit: acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Evidence: `scripts/orchestration/skill_router.py` removes the bare `oracle` lexeme from the review-pattern semantic group; `tests/test_skill_router.py` proves generic Experiment Runner oracle text no longer routes `pulseplate-review-pattern-oracles`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755463 -> acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Disposition: FIXED
Commit: acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Evidence: `scripts/orchestration/agent_learning_loop.py` checks the `ghs_` token pattern before the generic GitHub-token branch; `tests/test_agent_learning_loop.py` proves `ghs_abc-def.ghi` is fully redacted.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755465 -> acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Disposition: FIXED
Commit: acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Evidence: `scripts/orchestration/agent_lesson_promoter.py` catches `OSError` with malformed input errors; `tests/test_agent_learning_loop.py` covers unreadable record-file CLI failure.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755469 -> acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Disposition: FIXED
Commit: acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Evidence: `scripts/orchestration/pr_review_context.py` emits repo-relative fixed-mapping evidence via `repo_path`; `tests/test_pr_review_context.py` proves no-PR-number evidence avoids local workspace paths.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2028#discussion_r3485755472 -> acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Disposition: FIXED
Commit: acdc769a7ee1a2420d5a6cfc58cf33d6ffdc2a57
Evidence: `scripts/orchestration/pr_review_context.py` evaluates fixed-mapping PR-diff membership whenever diff data is available, independent of SHA parity; `tests/test_pr_review_context.py` covers the missing-SHA parity branch.

## Premortem Evidence
- Disposition: FIXED
- Commit: ca437e56282707f4134f3a57ab749cf5bc4dd00d
- Evidence: `scripts/orchestration/agent_learning_loop.py`, `tests/test_agent_learning_loop.py`, and focused pytest fixed invalid learning severity/path acceptance before PR open.
- Evidence: `docs/orchestration/REVIEW_SOURCE_DEGRADATION_POLICY.md`, `scripts/orchestration/pr_review_report.py`, and `tests/test_pr_review_report.py` keep degraded review-source status advisory unless explicit blocking findings exist.
- Evidence: `docs/orchestration/SCOPED_VALIDATION_POLICY.md` keeps scoped validation separate from merge readiness and records the local `make verify` deferral.

## Experiment Runner Evidence
- Artifact: `artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/orchestration-review-fallback-learning-loop-result.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution: `oracle_review`
- Co-author: required and present in `ca437e56282707f4134f3a57ab749cf5bc4dd00d`

## Validation Evidence
- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 -m py_compile` for changed orchestration CLIs/helpers
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest tests/test_agent_learning_loop.py tests/test_skill_router.py tests/test_pr_review_context.py -q`
- Focused pytest for review oracles, review-source status, PR review context/reporting, skill routing, task bootstrap, skill install/mirror, and symlink integrity
- Focused flake8 for changed Python files
- Focused mypy with `--explicit-package-bases` for changed orchestration scripts
- `make validate-changed`
- `pre-commit run --all-files`
- `pre-commit run mypy --hook-stage pre-push --files scripts/orchestration/pr_review_context.py`
- `git diff --check`
- Pre-push hooks from `git push origin feat/orchestration-review-fallback-learning-loop`
- Full `make verify` was attempted but stopped at `verify-env` because this isolated worktree has no local `.venv`; this PR does not claim merge readiness from local gates alone.

## Post-Open Review Evidence
- Post-open packet: `artifacts/orchestration/task_packets/f25b8bd19ce4.json`
- `qa-engineer-agent`: PASS after fixing review-source/fixed-mapping governance validation in `d3fd0fdec`.
- `bug-hunter`: PASS after fixing JSON stdout hygiene, stale fixed-mapping degradation, schema enum/path constraints, and local-path rejection in `4d6deb2b3`.
- `security-auditor`: PASS after fixing GitHub token-family redaction and URI/path rejection in `f8dcd8740`.
- Codex Security diff scan / finding discovery: PASS on current head `34d2f2cf`, scan `2392ac75-a730-4d2a-94a2-4cc281de9c07`, 9/9 coverage rows closed, 0 reportable findings, report `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-Hmdu7f/orchestration-review-fallback-learning-loop/34d2f2cf86ecba74d3fbdf1b79c38d3101f9e145_20260627T092340Z_rmh8spid/report.md`.
- `pulseplate-pr-review`: completed on current head `34d2f2cf`; review-source status clean, no blocking findings.
- `pulseplate-pr-review` note disposition: NOT-A-BUG.
  Evidence: PR plan explicitly locks the four governance blocks into one intentional PR, and local scoped gates (`make validate-changed`, `pre-commit run --all-files`, pre-push hooks) passed. The note is a review-planning signal for large diff size, not a defect in the current implementation.

## Merge Readiness
- Not claimed.
- Pending current-head CI, post-open review governance, bot/review-thread disposition, and strict merge-readiness checks.
