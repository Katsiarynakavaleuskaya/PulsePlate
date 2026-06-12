# PR #1965 Fixed in Commit Mapping

## Goal

Complete the artifact-reader guard bypass fix and the required governance
evidence for PR #1965.

## Business Reason

The artifact-reader guard protects PulsePlate runtime surfaces from reading
local orchestration, agent-run, and security-lab artifacts as product truth. A
guard bypass here can create a false green for evidence-rail separation.

## Scope

- Harden literal path-part handling in
  `scripts/ci/check_artifact_reader_contracts.py`.
- Extend deterministic regression coverage in
  `tests/test_artifact_validation_boundary.py`.
- Add this canonical review mapping artifact for PR #1965.

## Out Of Scope

- Runtime API behavior, OpenAPI, frontend, iOS, billing, entitlements, LLM
  provider behavior, migrations, and deployment workflows.
- Any new local artifact publication or semantic-cache behavior.

## Files Changed

- `scripts/ci/check_artifact_reader_contracts.py`
- `tests/test_artifact_validation_boundary.py`
- `docs/review/PR_1965_FIXED_MAPPING.md`

## Key Decisions

- Fixed the original mixed literal/dynamic suffix bypass in commit
  `80b3a03e8555429d70ecef7a0adea8435ae14492`.
- Fixed role-discovered parent-traversal bypasses in commit
  `fd74cf3dc7446d96c4533acae7d1f8f2aa671cec`.
- Merged current `origin/main` in commit
  `eb28431e36a10d0825676308c67905e65826fe60` and preserved main's
  repo-root-prefix normalization together with this PR's dynamic-prefix and
  parent-traversal hardening.
- Kept the client/runtime/product contract surface unchanged.
- Used the operator-approved machine-heavy exception for local full
  `make verify`; narrow local gates plus fresh current-head CI are required
  before any merge-readiness claim.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## External Bot And Review Dispositions

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1965#issuecomment-4688711741
Disposition: NOT-A-BUG
Evidence: CodeRabbit reported a review rate/usage-credit limit notice and did
not report a code-actionable finding.
Reason: External reviewer availability notice only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1965#issuecomment-4688728454
Disposition: NOT-A-BUG
Evidence: Codex connector reported code-review usage limits and did not report
a code-actionable finding.
Reason: External reviewer availability notice only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1965#issuecomment-4688921419
Disposition: NOT-A-BUG
Evidence: Codecov reported that all modified and coverable lines are covered by
tests.
Reason: Coverage status only; no requested code change.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1965#pullrequestreview-4483507875
Disposition: NOT-A-BUG
Evidence: Sourcery reported a weekly diff-character rate-limit notice and did
not report a code-actionable finding.
Reason: External reviewer availability notice only.

- Cubic reviewer status
Disposition: NOT-A-BUG
Evidence: Cubic completed as neutral/skipped for the PR head and did not post a
code-actionable finding.
Reason: External review status only.

## Role-Agent Findings

| Role | Result | Evidence |
| --- | --- | --- |
| `agent-coordinator` | Finding fixed. | Found that same-string parent traversal such as `Path("artifacts/safe/../orchestration", name).read_text()` bypassed the guard. Commit `fd74cf3dc7446d96c4533acae7d1f8f2aa671cec` adds `_collapse_path_parts(...)` and regression coverage. |
| `qa-engineer-agent` | Finding fixed. | Found that parent traversal across path argument boundaries still bypassed the guard for `Path(...)`, `joinpath(...)`, `/`, and `os.path.join(...)`. Commit `fd74cf3dc7446d96c4533acae7d1f8f2aa671cec` folds accumulated parts after each composition step and adds regressions. |
| `bug-hunter` | PASS via manual fallback. | The native subagent transport returned a usage-limit error for this role. Manual pass used `.cursor/agents/bug-hunter.md`; targeted probes confirmed cross-argument traversal is now flagged and paths normalizing outside forbidden artifact roots remain allowed. |
| `security-auditor` | PASS. | Manual pass used `.cursor/agents/security-auditor.md`; no runtime, auth, secret, subprocess, billing, LLM, or data-path expansion was found. Codex Security diff scan reported no findings. |
| `dev-operator` | PASS. | Manual pass used `.cursor/agents/dev-operator.md`; focused commands and pre-commit changed-file hooks passed, with `make validate-changed` and `pre-commit run --all-files` required before push. |
| `architecture-specialist` | PASS. | Manual pass used `.cursor/agents/architecture-specialist.md`; the diff stays in CI guard/test governance and does not move product truth into clients or runtime code. |
| `cursor-specialist-agent` | PASS. | Manual pass used `.cursor/agents/cursor-specialist-agent.md`; preflight, task bootstrap, and role dispatch bridge were run, and the subagent-transport quota fallback is documented here. |
| `web-research-agent` | PASS. | Manual pass used `.cursor/agents/web-research-agent.md`; no external claims, library choices, CVE advisories, or web research inputs are required for this two-file repo-governance fix. |

## Premortem Finding Closure

- Finding: the mixed literal/dynamic suffix fix might still discard forbidden
  artifact roots.
  - Disposition: FIXED
  - Evidence: commit `80b3a03e8555429d70ecef7a0adea8435ae14492` added dynamic
    suffix preservation, and focused boundary tests cover mixed
    literal/dynamic artifact roots.
- Finding: parent traversal could normalize into a forbidden artifact root after
  the initial fix.
  - Disposition: FIXED
  - Evidence: commit `fd74cf3dc7446d96c4533acae7d1f8f2aa671cec` folds `..`
    across same-string and cross-argument composition and adds deterministic
    regressions.
- Finding: the traversal fix might widen into false positives for paths that
  normalize outside forbidden artifact roots.
  - Disposition: NOT-A-BUG
  - Evidence: manual bug-hunter probe for
    `Path("artifacts/orchestration/../../tmp", name).read_text()` returned no
    findings.
- Finding: missing Phase2 mapping/body governance could keep current-head CI
  red.
  - Disposition: FIXED
  - Evidence: this artifact provides the canonical mapping source of truth; the
    PR body mirror must be refreshed and checked by
    `check_pr_body_phase2_gates.py` before push.

## Codex Security Diff Scan / Finding Discovery

- Scan id: `pr1965_80b3a03e8_20260612T100540Z`
- Reviewed surfaces: `scripts/ci/check_artifact_reader_contracts.py` and
  `tests/test_artifact_validation_boundary.py`
- Result: no reportable findings survived discovery.
- Report validation: `validate_report_format.py` passed for the local
  `report.md`; `report.html` rendered successfully.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/pr1965-artifact-guard-oracle-result.json`
- Packet: `artifacts/orchestration/experiments/artifacts/orchestration/experiments/pr1965-artifact-guard-oracle.json`
- Experiment id: `exp-50a3ddbed587`
- Runner mode: `oracle_only_governance_reviewer`
- Result: `status: accepted`; `mutated_paths: []`; `shared_tree_untouched: true`
- Oracle commands executed: `py_compile`, artifact guard CLI, and focused
  boundary pytest; all returned 0.
- Co-author: required. Commits shaped by this oracle review include the
  canonical trailer:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## PulsePlate PR Review

- Command:
  `python3 scripts/orchestration/pr_review_context.py --pr 1965 --repo Katsiarynakavaleuskaya/PulsePlate --repo-root . --base "$(git merge-base origin/main HEAD)" --head HEAD --output /tmp/pr1965_pr_review_context.json`
- Command:
  `python3 scripts/orchestration/pr_review_report.py --context /tmp/pr1965_pr_review_context.json --format markdown --packet-id 298a5168547b --packet-path artifacts/orchestration/task_packets/298a5168547b.json --output /tmp/pr1965_pr_review_report.md`
- Result: no deterministic findings from supplied context; scope reviewed was
  limited to `scripts/ci/check_artifact_reader_contracts.py` and
  `tests/test_artifact_validation_boundary.py`.

## Tests / Validation

Passed on this PR lane:

- `python3 scripts/orchestration/check_preflight.py --path scripts/ci/check_artifact_reader_contracts.py --path tests/test_artifact_validation_boundary.py --path docs/review/PR_1965_FIXED_MAPPING.md`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/task_bootstrap.py --goal "PR 1965: complete artifact-reader guard bypass fix governance and merge readiness" --task-class security_ci_fix --pr-phase post_open_review --path scripts/ci/check_artifact_reader_contracts.py --path tests/test_artifact_validation_boundary.py --path docs/review/PR_1965_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent security-auditor --requested-agent dev-operator --requested-agent architecture-specialist`
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/298a5168547b.json --pretty`
- `python3 -m py_compile scripts/ci/check_artifact_reader_contracts.py tests/test_artifact_validation_boundary.py`
- `python3 scripts/ci/check_artifact_reader_contracts.py --repo-root .`
- focused boundary pytest through the repo-approved Python interpreter:
  58 passed after merging current `origin/main`.
- `git diff --check origin/main...HEAD && git diff --check`
- commit-time pre-commit changed-file hooks for commit
  `fd74cf3dc7446d96c4533acae7d1f8f2aa671cec`.
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/review/PR_1965_FIXED_MAPPING.md`
- `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1965`
- `make validate-changed`
- `pre-commit run --all-files`

Operator-approved machine-heavy deferral:

- Full local `make verify` is intentionally not run for this PR because the
  operator approved the machine-heavy exception. No local full-verify green is
  claimed. Current-head CI and strict merge readiness must be used as the heavy
  signal after push.

## Security Notes

No secrets, auth, billing, LLM, export, runtime route, OpenAPI, iOS, frontend,
database, migration, or production deployment surface changed. The guard remains
fail-closed for detectable local artifact reads and enumerations.

## Risks / Rollback

Risk: a static guard can still miss path constructions it cannot resolve from
literal components.

Mitigation: the changed guard now preserves forbidden literal roots through
dynamic suffixes and parent traversal folding, and tests cover the discovered
equivalence classes.

Rollback: revert merge-resolution commit
`eb28431e36a10d0825676308c67905e65826fe60`, code hardening commit
`fd74cf3dc7446d96c4533acae7d1f8f2aa671cec`, the original PR code commit
`80b3a03e8555429d70ecef7a0adea8435ae14492`, and this governance artifact
commit. No data or runtime migration is involved.

## Deferred / Follow-Ups

None. No backlog entry is needed because all role/premortem/Codex Security
findings in this PR scope are fixed or non-actionable.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/298a5168547b.json`
- Starter: not used; startup was run directly through repo preflight,
  `task_bootstrap.py`, and `role_dispatch_bridge.py`.

## Merge Readiness

Not claimed by this artifact. Required current-head CI, body Phase2 gates,
review-thread disposition, bot-actionable pass, mandatory wait window, and
strict merge-ready wrapper must pass after push before merge.
