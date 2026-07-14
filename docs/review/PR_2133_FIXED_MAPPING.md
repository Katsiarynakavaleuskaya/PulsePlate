# PR #2133 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2133

Branch: `codex/setuptools-cve-2026-59890`

## Summary

Remediate CVE-2026-59890 / PYSEC-2026-3447 by moving every governed
setuptools source and lock surface to the fixed 83.0.0 boundary. Preserve the
canonical private Python proxy, dependency-profile ownership, generated-lock
provenance, application behavior, and forward-only rollback.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/97acbef5b317.json`
  (local-only, gitignored).
- Coordinator-corrected pre-open role order executed:
  `agent-coordinator -> dev-operator -> security-auditor -> architecture-specialist -> qa-engineer-agent -> bug-hunter`.
- Post-open packet: `artifacts/orchestration/task_packets/1b11d90b6b05.json`
  (local-only, gitignored).
- Post-open role order executed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- The actual-diff premortem closed all forecast failure scenarios before PR
  open.
- Experiment Runner used the explicit Apple Container backend on macOS; its
  accepted result passed 2/2 immutable oracles with strict isolation and no
  shared-tree mutation.

## Implementation Commits

- `def03ed50991937c8a84b391160a8ba06014b609` - raise the setuptools floor and
  exact pins, regenerate five governed locks through the approved private
  proxy, extend deterministic guards, and record forward-only rollback.
- `dcef7c4a1` - anchor the remediation decision to exact deterministic test
  evidence after the current-head Phase 1 docs gate identified the missing
  `file:line` references.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Pre-open packet and coordinator-corrected role order completed.
- [x] Actual-diff premortem completed with no open blocker.
- [x] Experiment Runner Apple Container oracle evidence accepted.
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed.
- [x] Codex Security diff scan completed for the material diff.
- [x] `pulseplate-pr-review` completed.
- [x] All current review threads dispositioned and resolved; GraphQL reported
  no review threads.
- [ ] Current-head CI completed after this governance artifact is pushed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

## Fixed in Commit Mapping

- No actionable review comments

## Bot Capacity Notices

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2133#issuecomment-4969183974
  Disposition: NOT-A-BUG
  Evidence: The Codex connector comment reports code-review usage limits only
  and requests no code, documentation, test, security, or governance change.
  Reason: External service capacity is not a defect or an approval signal.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2133#issuecomment-4969184578
  Disposition: NOT-A-BUG
  Evidence: The CodeRabbit comment is a rate-limit notice for the exact 14-file
  range and contains no diff-specific actionable finding.
  Reason: Review quota exhaustion is not a repository defect or a substantive
  CodeRabbit approval.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2133#pullrequestreview-4694262296
  Disposition: NOT-A-BUG
  Evidence: Sourcery reports only its weekly diff-character rate limit and
  requests no repository change.
  Reason: The COMMENTED quota notice is external capacity state, not a PR
  finding or approval.
- Cubic completed with a neutral status and generated the PR summary without
  an actionable review finding. This is recorded as no-actionable evidence,
  not as a substantive approval.

## Experiment Runner Evidence

Artifact:
`artifacts/orchestration/experiments/results/setuptools-cve-2026-59890-apple-oracle-v2-result.json`

The artifact is local-only and gitignored. The explicit
`--backend apple-container` run was accepted with strict network isolation,
2/2 immutable oracle passes, `shared_tree_untouched=true`, and
`mutated_paths=[]`. The runner materially shaped the commit decision, and the
implementation commit carries the required co-author trailer.

## Premortem

- Public-index or credential bypass: closed by canonical private-proxy health,
  `--no-emit-index-url`, forbidden-source guards, and credential-free tracked
  locks.
- Stale vulnerable pin: closed by the four bounded source profiles, flexible
  constraints floor, five exact 83.0.0 locks, and schema block for `<83.0.0`.
- Resolver churn: closed by sequential no-upgrade lock regeneration and parsed
  exact-diff review showing no unrelated package-version movement.
- Unsafe local install: closed by leaving `.venv` unchanged until post-merge
  `make venv-sync` through the approved proxy.
- Advisory or rollback drift: closed by the tracked remediation decision and
  forward-only rollback contract.
- Source/lock topology drift: closed by deterministic tests covering all ten
  governed source, constraint, and lock surfaces.

## Validation Evidence

- PASS: orchestration preflight and agent consistency.
- PASS: approved private-proxy health for setuptools 83.0.0 on Python 3.11,
  3.12, and 3.13.
- PASS: focused dependency-security and Python supply-chain tests.
- PASS: `python3 verify_requirements.py` and
  `python3 scripts/ci/check_python_dependency_surfaces.py`.
- PASS: pip-audit across all five changed locks; no known vulnerabilities.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files`.
- PASS: pre-push hooks, including Bandit and the Docker build test.
- PASS: `git diff --check`.
- PASS: Phase 1 docs gates after adding exact evidence anchors at
  `tests/test_python_supply_chain_controls.py:1264` and
  `tests/test_dependency_security_guard.py:390`.
- PENDING: canonical current-head GitHub CI after this governance commit and
  strict authenticated merge readiness.
- NOT RUN: local full `make verify`; prohibited by the repository local budget
  rule.

## Security Review

- PASS: mandatory post-open security-auditor found no actionable issue.
- PASS: sealed Codex Security scan
  `d3e49b4a-a801-4564-adcb-363ba4e5cb9d` covered all 14 exact-diff rows at
  `def03ed50991937c8a84b391160a8ba06014b609` and reported zero findings.
- PASS: `pulseplate-pr-review` found no correctness, architecture, test, or
  security defect. Its only notes were the then-missing fixed-mapping artifact,
  which this file supplies.

## Risks / Rollback

Rollback is forward-only. Do not restore setuptools 78.1.1 or any version
below 83.0.0. If 83.0.0 is incompatible or unavailable, keep install and
release lanes blocked and either repair the approved proxy or move to another
tested patched 83.x release through a separately reviewed dependency update.

## Deferred / Follow-ups

None for this prerequisite hotfix.
