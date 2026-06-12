# PR 1929 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1929>

## Summary

This PR hardens Codex skill copy-marker verification against unsafe marker
paths. The remediation keeps the verifier read-only, avoids CLI/API shape
changes for valid repo-managed copies, and adds deterministic tests for
symlink, missing no-follow support, path replacement, invalid UTF-8, and
diagnostic redaction behavior.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/f65232defe55.json`
- Branch: `codex/propose-fix-for-marker-symlink-vulnerability`
- PR phase: `post_open_review`
- Role dispatch command executed: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/f65232defe55.json --pretty`
- Declared role order executed: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> web-research-agent`

## Scope

- Harden `scripts/verify_codex_skills_install.py` copy-marker reads.
- Extend `tests/test_install_codex_skills.py` regression coverage.
- Add this fixed-mapping artifact and mirror the required PR-body sections.

## Out of Scope

- No installer flag changes.
- No runtime app, API, OpenAPI, web, iOS, nutrition, billing, or LLM behavior changes.
- No full local `make verify`; this PR uses the operator-approved machine-heavy
  exception with narrow local gates plus current-head CI parity before any
  readiness claim.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [ ] Current-head CI parity confirmed after the latest push.
- [ ] Strict merge-readiness wrapper passed.
- [ ] Mandatory final wait-window completed.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1929#discussion_r3380640466 -> 478cc4056fb344913242f93f6f85fd7f919fa2aa
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1929#pullrequestreview-4458588387 -> 478cc4056fb344913242f93f6f85fd7f919fa2aa
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1929#issuecomment-4659767730 -> 478cc4056fb344913242f93f6f85fd7f919fa2aa
Disposition: FIXED
Commit: 478cc4056fb344913242f93f6f85fd7f919fa2aa
Evidence: `scripts/verify_codex_skills_install.py:109`; `tests/test_install_codex_skills.py:463`; `tests/test_install_codex_skills.py:479`
Reason: Sourcery's security review was valid. The fix replaces ad hoc marker-error strings with constants, fails closed when `os.O_NOFOLLOW` is unavailable, compares the initial no-follow `stat` identity with `fstat()` before reading marker bytes, and adds deterministic tests for no-follow absence and stat/open path replacement.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1929#issuecomment-4659765270
Disposition: NOT-A-BUG
Evidence: CodeRabbit selected only `scripts/verify_codex_skills_install.py` and `tests/test_install_codex_skills.py` but did not run a review because the organization hit review-rate/credit limits.
Reason: The comment is a quota notice and finishing-touch prompt, not an actionable code, test, documentation, or governance finding.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1929#issuecomment-4659862582
Disposition: NOT-A-BUG
Evidence: Codecov reported all modified and coverable lines covered by tests.
Reason: The comment contains no actionable follow-up.

## Premortem Finding Closure

- PM-1929-001: Marker path can be swapped between initial stat and open.
  Disposition: FIXED. Evidence: `scripts/verify_codex_skills_install.py:137`
  checks `fstat()` identity before any marker payload read; covered by
  `tests/test_install_codex_skills.py:479`.
- PM-1929-002: Platforms without `O_NOFOLLOW` could silently degrade to an
  unsafe plain open. Disposition: FIXED. Evidence:
  `scripts/verify_codex_skills_install.py:125` returns
  `MARKER_ERROR_NO_NOFOLLOW`; covered by `tests/test_install_codex_skills.py:463`.
- PM-1929-003: Marker error strings can drift through repeated literals.
  Disposition: FIXED. Evidence: marker error constants are centralized in
  `scripts/verify_codex_skills_install.py:63`.
- PM-1929-004: Security regression tests could trip secret scanning.
  Disposition: FIXED. Evidence: tests use benign marker payload names and
  `.venv/bin/detect-secrets scan tests/test_install_codex_skills.py` returned
  empty results.
- PM-1929-005: Governance mapping before a real fix commit would violate
  commit-after-comment policy. Disposition: FIXED. Evidence: this artifact maps
  the Sourcery review to non-trigger fix commit
  `478cc4056fb344913242f93f6f85fd7f919fa2aa`, created after the review comment.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-9d32ff5a5966.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-9d32ff5a5966.json`
- Result: `accepted`
- Contribution kind: `fixed_mapping_review`
- Co-author required: `true`
- Oracle commands:
  - `python3 -m py_compile scripts/verify_codex_skills_install.py tests/test_install_codex_skills.py`
  - `python3 scripts/verify_codex_skills_install.py --help`
  - `git diff --check HEAD~1 HEAD`
- Rejected earlier oracle attempt: `artifacts/orchestration/experiments/results/exp-76731eec4574.json` was rejected because isolated checkout validation lacked a repo `.venv`; it is not used as readiness proof.

## Role-Agent Evidence

- `agent-coordinator`: completed scope/routing pass for packet `f65232defe55`; kept scope to the verifier, tests, fixed mapping, and PR body metadata.
- `qa-engineer-agent`: reviewed the implementation and flagged deterministic path replacement test stability; fixed before commit by replacing the marker path with `Path.replace`.
- `bug-hunter`: found no blocking runtime regression after py_compile, ruff, Black check, focused pytest, and detect-secrets scan passed.
- `security-auditor`: found no blocking security regression after the marker read became fail-closed for missing no-follow support and rejected stat/open identity replacement before payload read.
- `cursor-specialist-agent`: confirmed workflow/provenance requirements and required this parser-safe mapping artifact plus machine-heavy verify deferral.
- `web-research-agent`: confirmed no external research was required and no browsing-derived authority should be used for this local tooling/security PR.

## Codex Security Diff Scan

- Scan path: `/tmp/codex-security-scans/BMI-App_2025_clean/478cc405_20260612T195545Z`
- Final reports: `report.md` and `report.html`
- Worklist: `artifacts/02_discovery/deep_review_input.csv`
- Closure evidence: `artifacts/02_discovery/work_ledger.jsonl`
- Result: no reportable findings for the scoped verifier/test remediation files.
- Scope note: the deterministic rank helper preserved a broader full-branch
  `rank_input.csv`, but the operator-approved remediation scan scope is
  `scripts/verify_codex_skills_install.py` and
  `tests/test_install_codex_skills.py`.

## PulsePlate PR Review

- Dry-run report: `/tmp/pulseplate_pr1929_review_report.md`
- Disposition: FIXED for missing fixed-mapping findings.
  Evidence: this artifact now exists and contains the canonical discussion
  thread pass and fixed mapping.
- Disposition: NOT-A-BUG for the large-diff planning note.
  Evidence: the operator-approved scope for this remediation commit remains the
  verifier, tests, fixed mapping, and PR body metadata; full local `make verify`
  remains intentionally deferred under the machine-heavy exception.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --path scripts/verify_codex_skills_install.py --path tests/test_install_codex_skills.py --path docs/review/PR_1929_FIXED_MAPPING.md`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --goal "Bring PR #1929 Codex skill marker security hardening to merge readiness" --task-class "Security/Tooling" --path scripts/verify_codex_skills_install.py --path tests/test_install_codex_skills.py --path docs/review/PR_1929_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase post_open_review --native-bridge-transport codex-native-subagents`
- PASS: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/f65232defe55.json --pretty`
- PASS: `python3 -m py_compile scripts/verify_codex_skills_install.py tests/test_install_codex_skills.py`
- PASS: `.venv/bin/ruff check scripts/verify_codex_skills_install.py tests/test_install_codex_skills.py`
- PASS: `.venv/bin/black --check scripts/verify_codex_skills_install.py tests/test_install_codex_skills.py`
- PASS: `.venv/bin/python -m pytest tests/test_install_codex_skills.py -q` (`27 passed`)
- PASS: `.venv/bin/detect-secrets scan tests/test_install_codex_skills.py` (`results: {}`)
- PASS: `git diff --check`
- PASS: `make validate-changed` (`tests/test_install_codex_skills.py`, `27 passed`)

## Machine-Heavy Verify Exception

Full local `make verify` is intentionally not run for this coordinator/tooling
lane under the operator-approved machine-heavy exception. This PR must use the
documented narrow local gates, `pre-commit run --all-files`, and current-head
GitHub CI parity before any merge-readiness claim.

## Merge Readiness

Not claimed yet.

Required before merge:

- Run `PRE_COMMIT_HOME=/tmp/pre-commit-pr1929 pre-commit run --all-files`.
- Push the mapping commit and refresh the PR body mirror.
- Resolve the mapped Sourcery review thread only after this artifact is pushed.
- Confirm current-head CI parity for the pushed SHA.
- Confirm CodeRabbit, Sourcery, Cubic, Codecov, and GitHub review state have no
  unresolved actionable findings.
- Run `python3 scripts/orchestration/check_merge_ready.py --pr-number 1929 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`.
- Complete the mandatory final wait-window after latest bot/review activity.
