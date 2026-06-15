# PR 1979 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979>

## Summary

This guard-compatibility lane makes the ruff dependency guard derive the
expected ruff version from `requirements-dev.in` instead of hard-coding the
previous exact pin. The guard still requires the generated and constraint
surfaces to match that source and still forbids a ruff emergency wheel fallback.

This is a prerequisite for the Dependabot ruff lane (#1973). Raw #1973 remains
blocked separately because it includes broad `requirements-lock.txt` resolver
churn and adds `pip==26.1.2`.

## Lane Start Provenance

- Branch: `codex/ruff-guard-manifest-parity`
- Base at branch start: `eabf69ecc8ed288c718239d09579fd61f4cd879a`
- Initial implementation commit:
  `ea74f14fb2d6c9d7d4efff268f624a2334f7c84f`
- Initial mapping artifact commit:
  `ea52cf7cfced59f1b35f683d3cd02f9ac164dc77`
- Packet: `artifacts/orchestration/task_packets/1a8d6fe97dcc.json`
- Experiment Runner packet:
  `artifacts/orchestration/experiments/exp-9bd8f13b42ee.json`
- Experiment Runner accepted result:
  `artifacts/orchestration/experiments/results/exp-9bd8f13b42ee.json`
- Machine-heavy exception: full local `make verify` intentionally deferred
  under the operator-approved dependency/security lane scope. Focused local
  gates and current-head CI remain required before merge readiness.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Sourcery review `4494544909`: rate-limit metadata, not actionable code
  review feedback; dispositioned below as NOT-A-BUG.
- CodeRabbit review `4494573487`: three actionable mapping text findings;
  dispositioned below as FIXED.
- Codex connector review `4494581350`: review metadata with no actionable
  inline findings; dispositioned below as NOT-A-BUG.
- Post-open role loop completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- CodeRabbit CLI review completed with 0 issues.
- Codex Security diff scan / finding discovery completed with no findings.
- `pulseplate-pr-review` dry-run completed with no deterministic findings.

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#pullrequestreview-4494544909
Disposition: NOT-A-BUG
Evidence: Sourcery reported weekly diff-character rate limiting and did not return an actionable code or documentation finding.
Reason: rate-limit metadata does not require a code change.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#pullrequestreview-4494573487 -> acb6d162abc370469a55fb36cc5f3b7752186a70
Disposition: FIXED
Commit: acb6d162abc370469a55fb36cc5f3b7752186a70
Evidence: `docs/review/PR_1979_FIXED_MAPPING.md` now uses exact completed checkbox labels, `Phase 2`, and clearer QA role wording.
Reason: CodeRabbit requested parser-safe checkbox wording plus two mapping text cleanup items.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#pullrequestreview-4494581350
Disposition: NOT-A-BUG
Evidence: Codex connector review contains the automated review header and reviewed commit metadata only; it does not include an actionable code or docs finding.
Reason: no fix is required for metadata-only review output.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411139936 -> 2153e4a12174bb719fa44b6f8391d349b042c173
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411139941 -> 2153e4a12174bb719fa44b6f8391d349b042c173
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411146058 -> 2153e4a12174bb719fa44b6f8391d349b042c173
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411146060 -> 2153e4a12174bb719fa44b6f8391d349b042c173
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411146062 -> 2153e4a12174bb719fa44b6f8391d349b042c173
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411146064 -> 2153e4a12174bb719fa44b6f8391d349b042c173
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411203628 -> 2153e4a12174bb719fa44b6f8391d349b042c173
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411203632 -> 2153e4a12174bb719fa44b6f8391d349b042c173
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411203635 -> 2153e4a12174bb719fa44b6f8391d349b042c173
Disposition: FIXED
Commit: 2153e4a12174bb719fa44b6f8391d349b042c173
Evidence: `docs/review/PR_1979_FIXED_MAPPING.md` now uses completed checkbox labels, `Phase 2`, canonical `Packet:` provenance, valid disposition blocks instead of stale no-actionable text, a reachable CodeRabbit proof SHA, raw hex `Commit:` values, and precise Experiment Runner trailer evidence.
Reason: the mapped comments requested parser-safe governance text, reachable/raw commit proof, and accurate Experiment Runner attribution evidence.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411146066
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411146069
Disposition: NOT-A-BUG
Evidence: Current PR history contains `ea74f14fb2d6c9d7d4efff268f624a2334f7c84f`, and `git merge-base --is-ancestor ea74f14fb2d6c9d7d4efff268f624a2334f7c84f HEAD` returns success. `git log --format=%B origin/main..HEAD` shows the canonical `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer on every material PR commit.
Reason: these comments referenced stale reviewed-head ancestry/metadata; the current branch contains the cited implementation proof commit and the required Experiment Runner attribution trailer.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411263520
Disposition: NOT-A-BUG
Evidence: `gh pr view 1979 --json headRefOid` reports `680f526c969d8a0daf777424a2d507f56fe13922`, and `git ls-remote origin refs/pull/1979/head` reports the same SHA. From the PR branch, `git merge-base --is-ancestor acb6d162abc370469a55fb36cc5f3b7752186a70 HEAD` and `git merge-base --is-ancestor 2153e4a12174bb719fa44b6f8391d349b042c173 HEAD` both return success.
Reason: the comment cited stale reviewed-head `f78be22d71d91f1a8bd3d3e04af7d61fff403d1b`, which is not the current GitHub PR head; the mapped FIXED proof commits are reachable from the current PR branch.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1979#discussion_r3411263524
Disposition: NOT-A-BUG
Evidence: `git log --format=%H%n%B origin/main..HEAD` shows the canonical `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer on every material PR commit, including the latest mapping/proof commits.
Reason: the comment cited stale reviewed-head `f78be22d71d91f1a8bd3d3e04af7d61fff403d1b`; the current PR branch satisfies the Experiment Runner attribution invariant.

## Role Dispatch Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/check_preflight.py --path tests/test_install_locked_python_requirements.py`
- PASS: role dispatch manifest from packet
  `artifacts/orchestration/task_packets/1a8d6fe97dcc.json`
- Pre-open role order completed before implementation:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> cursor-specialist-agent -> architecture-specialist`.
- `agent-coordinator`: blocked raw #1973 and required separate guard-compat
  work because the Dependabot branch carries resolver churn and `pip==26.1.2`.
- `qa-engineer-agent`: accepted ruff derivation from `requirements-dev.in` and
  required dependency guard coverage to remain focused.
- `bug-hunter`: required existing parsers instead of ad hoc regexes and no new
  stale ruff literal.
- `security-auditor`: required no changes to manifests, lockfiles, emergency
  wheels, installer scripts, or torch waiver docs.
- `cursor-specialist-agent`: required non-draft PR, PR-numbered mapping, and
  post-open review loop.
- `architecture-specialist`: confirmed `requirements-dev.in` is the source
  surface and generated/constraint files are parity surfaces.

## Post-Open Role Finding Closure

- `agent-coordinator` post-open pass:
Disposition: FIXED
Commit: 159544c599e4b15ae65dc5ed6b0d74a57e7dd5bd
Evidence: PR body now uses exact `## Tests`, exact completed checkboxes, exact
`- No actionable review comments`, Experiment Runner `Artifact:`, and lane
`Packet:` fields. This mapping artifact now uses exact parser-safe labels and a
real mapping commit SHA.

- `qa-engineer-agent` post-open pass:
Disposition: FIXED
Commit: 159544c599e4b15ae65dc5ed6b0d74a57e7dd5bd
Evidence: QA accepted the implementation and identified the same parser-shape
and CodeRabbit mapping text nits. The parser-shape and wording fixes are now in
this artifact and PR body.

- `bug-hunter` post-open pass:
Disposition: FIXED
Commit: 159544c599e4b15ae65dc5ed6b0d74a57e7dd5bd
Evidence: bug-hunter found no implementation regression and called out the same
mapping/body parser defects. The exact `Packet:`, checkbox, no-actionable,
`Artifact:`, `Phase 2`, and QA wording fixes are now applied.

- `security-auditor` post-open pass:
Disposition: FIXED
Commit: 159544c599e4b15ae65dc5ed6b0d74a57e7dd5bd
Evidence: security-auditor accepted the supply-chain boundary and found the bad
mapping SHA plus parser-invalid governance text. This artifact now cites the
real mapping commit `ea52cf7cfced59f1b35f683d3cd02f9ac164dc77` and parser-safe
labels.

## Premortem Finding Closure

- PM-001: Deriving from generated lockfiles could bless resolver churn.
Disposition: FIXED
Commit: ea74f14fb2d6c9d7d4efff268f624a2334f7c84f
Evidence: `tests/test_install_locked_python_requirements.py` derives
`expected_ruff_version` from `requirements-dev.in` and compares other ruff
surfaces to that value.

- PM-002: Guard change could weaken emergency fallback or private-index
guarantees.
Disposition: FIXED
Commit: ea74f14fb2d6c9d7d4efff268f624a2334f7c84f
Evidence: the ruff emergency fallback assertion remains in
`tests/test_install_locked_python_requirements.py`; private-index preflight
passed with `scripts/ci/install_locked_python_requirements.py --preflight-only`.

- PM-003: Machine-heavy validation deferral could be under-documented.
Disposition: FIXED
Commit: ea52cf7cfced59f1b35f683d3cd02f9ac164dc77
Evidence: this artifact records the local `make verify` deferral and the focused
validation bundle required for the operator-approved exception.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-9bd8f13b42ee.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Contribution: `oracle_review`
- Co-author required: true; all material PR commits include
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Accepted oracle commands:
  - `python3 -m pytest -q tests/test_install_locked_python_requirements.py -k 'ruff_private_proxy_pin or quality_tooling_profile'`
  - `python3 -m pytest -q tests/test_dependency_security_guard.py -k repo_managed_lock_surfaces_do_not_pin_pip`

## Post-Open Review Evidence

- PASS: `coderabbit review --agent -t committed -c AGENTS.md`
  (`review_completed`, `findings: 0`)
- PASS: Codex Security diff scan / finding discovery
  - Scan artifact:
    `/tmp/codex-security-scans/BMI-App_2025_clean/746014b7059fe226dcc8bb72eccd3bfeda04f629_20260615T052340Z`
  - Report:
    `/tmp/codex-security-scans/BMI-App_2025_clean/746014b7059fe226dcc8bb72eccd3bfeda04f629_20260615T052340Z/report.md`
  - HTML:
    `/tmp/codex-security-scans/BMI-App_2025_clean/746014b7059fe226dcc8bb72eccd3bfeda04f629_20260615T052340Z/report.html`
  - Coverage: 2/2 diff-scoped files have `work_ledger.jsonl` completion
    receipts; no candidate findings were opened.
- PASS: `python3 scripts/orchestration/pr_review_context.py --pr 1979 --output /tmp/pulseplate_pr1979_review_context.json`
- PASS: `python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr1979_review_context.json --format markdown --packet-path artifacts/orchestration/task_packets/17a037545574.json --output /tmp/pulseplate_pr1979_review_report.md`
- PASS: `python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr1979_review_context.json --format json --packet-path artifacts/orchestration/task_packets/17a037545574.json --output /tmp/pulseplate_pr1979_review_report.json`
- PASS: `.venv/bin/python -m pytest -q tests/test_pr_review_report.py`
  (`9 passed`)

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_preflight.py --path tests/test_install_locked_python_requirements.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/install_locked_python_requirements.py --preflight-only --index-url "$PULSEPLATE_PYTHON_INDEX_URL" --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json`
- PASS: `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py -k 'ruff_private_proxy_pin or quality_tooling_profile'`
  (`2 passed`)
- PASS: `.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py -k repo_managed_lock_surfaces_do_not_pin_pip`
  (`1 passed`)
- PASS: `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py`
- PASS: `make validate-changed`
  (reported no selected diff tests; focused pytest above is the concrete local
  coverage for this test-only guard change)
- PASS: `pre-commit run --all-files`
- PASS during push hooks: `pip-audit`, backend pre-push pytest, and full-repo
  Bandit.
- PASS: PR body Phase 2 parser guard after post-open mapping updates:
  `python3 scripts/ci/check_pr_body_phase2_gates.py --body /tmp/pr1979-body-current.md --pr-number 1979 --commit-range origin/main..HEAD`
- PASS: PR size governance:
  `python3 scripts/ci/check_pr_size_governance.py --base-sha eabf69ecc8ed288c718239d09579fd61f4cd879a --head-sha acb6d162abc370469a55fb36cc5f3b7752186a70 --body "$(cat /tmp/pr1979-body-current.md)"`

## Merge Readiness

Merge readiness is not claimed by this artifact alone. Required remaining proof:

- current-head PR CI for the latest pushed head;
- PR-body Phase 2 and mapping guards after this artifact is committed and the PR
  body mirror is refreshed;
- strict merge-readiness wrapper with GitHub auth;
- no unresolved review threads or actionable bot comments;
- mandatory wait-window after the latest bot/review activity.

## Risks / Rollback

- Risk: deriving from the wrong surface would make the guard self-referential.
  Mitigation: the expected ruff version is derived only from `requirements-dev.in`.
- Risk: future Dependabot updates could still include unrelated resolver churn.
  Mitigation: this PR does not merge #1973; the later ruff dependency lane must
  keep a clean ruff-only diff with no `pip==...` pin.
- Rollback: revert this PR. It changes tests only and does not alter runtime or
  dependency state.
