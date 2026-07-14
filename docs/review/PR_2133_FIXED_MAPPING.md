# PR #2133 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2133

Branch: `codex/setuptools-cve-2026-59890`

## Summary

Remediate CVE-2026-59890 / PYSEC-2026-3447 by moving every governed
setuptools source and lock surface to the fixed 83.0.0 boundary. Carry over the
already reviewed two-file Docker source-manifest freshness prerequisite from PR
#2120 so the dependency remediation can pass its fail-closed Docker lane without
bypassing pre-push policy. Preserve the canonical private Python proxy,
dependency-profile ownership, generated-lock provenance, artifact identity,
application behavior, and forward-only rollback.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/97acbef5b317.json`
  (local-only, gitignored).
- Coordinator-corrected pre-open role order executed:
  `agent-coordinator -> dev-operator -> security-auditor -> architecture-specialist -> qa-engineer-agent -> bug-hunter`.
- Post-open packet: `artifacts/orchestration/task_packets/1b11d90b6b05.json`
  (local-only, gitignored).
- Post-open role order executed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- Cycle-resolution packet: `artifacts/orchestration/task_packets/7857caa1a0f2.json`
  (local-only, gitignored). The coordinator approved a bounded carryover of the
  unchanged PR #2120 material commit, reuse of its completed role evidence, and
  composition of the two path-disjoint sealed scans after exact content parity.
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
- `ad381545d` - cherry-pick the unchanged two-file PR #2120 source-manifest
  freshness commit so the combined prerequisite can satisfy the Docker lane.

## Carryover / Supersession

- Carries over and supersedes PR #2120.
- Canonical tracking:
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr2133-docker-manifest-prerequisite-consolidation`.
- Only `scripts/ci/docker_source_artifacts.json` and
  `tests/test_docker_workflow_build_path_contract.py` are carried over. Artifact
  version, filename, official HTTPS URL, full SHA3-256 digest, fetch reason,
  loader behavior, Dockerfile, workflows, and runtime topology are unchanged.
- The carried patch SHA-256 is
  `0b9f07e5aa5cd37fd7c1b132766bfcfceeb1891295a8383bc302f7b7ca21c9d4`
  both for original commit `ba66c949` and cherry-pick `ad381545d`; `git diff
  --exit-code ba66c949 HEAD -- <two carried paths>` is empty.

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
  Evidence: CodeRabbit completed the latest two-file governance/documentation
  pass and explicitly reported `No actionable comments were generated`. Its
  generic docstring-coverage warning has no applicable production callable:
  the material diff changes dependency manifests, a policy schema,
  documentation, and deterministic test functions only.
  Reason: Adding production docstrings is impossible on this diff, and test
  functions follow the repository's existing deterministic guard style.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2133#pullrequestreview-4694262296
  Disposition: NOT-A-BUG
  Evidence: Sourcery reports only its weekly diff-character rate limit and
  requests no repository change.
  Reason: The COMMENTED quota notice is external capacity state, not a PR
  finding or approval.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2133#issuecomment-4973729972
  Disposition: NOT-A-BUG
  Evidence: Cursor reports that Bugbot is not enabled for the account and
  explicitly states that no review was performed; it requests no repository
  change.
  Reason: Reviewer availability is external capacity state, not a code defect,
  review approval, or merge-readiness evidence.
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
- Cyclic prerequisite bypass: closed by carrying the unchanged, separately
  reviewed manifest patch into this PR rather than skipping pre-push or merging
  either red lane.
- Source substitution during carryover: closed by the identical patch
  fingerprint, unchanged artifact identity/digest, and deterministic identity
  assertions in the carried test.
- Resolver churn: closed by sequential no-upgrade lock regeneration and parsed
  exact-diff review showing no unrelated package-version movement.
- Unsafe local install: closed by proving exact-pin availability through the
  approved private proxy before the operator-authorized `make venv-sync` needed
  to satisfy mandatory hooks; the gitignored environment now reports
  setuptools 83.0.0 and no tracked dependency source changed during sync.
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
- PASS: combined focused dependency-security, Python supply-chain, and Docker
  workflow contract suite after carryover.
- PASS: current combined-head `pip-audit` pre-push hook against
  `requirements.txt`; no known vulnerabilities.
- PASS: current combined-head `make validate-changed`.
- PASS: current combined-head `pre-commit run --all-files` with no skipped
  required hook and no hook-produced tracked change.
- PASS: exact carryover patch fingerprint and zero content diff against original
  commit `ba66c949`.
- PASS: all 13 executable/lock/test dependency blobs are unchanged from scanned
  implementation head `def03ed50`; their ordered path/blob fingerprint is
  `1694f8bbd646f6505d55eeb53a235dc0c06d01e072ec209398961ad783634400`.
- PASS: Phase 1 docs gates after adding exact evidence anchors at
  `tests/test_python_supply_chain_controls.py:1264` and
  `tests/test_dependency_security_guard.py:390`.
- PASS: local Phase 2 validation of both the canonical artifact and published
  body mirror after correcting the strict `Artifact:` evidence label; the first
  current-head CI body-only failure is superseded by this parser-safe body.
- PENDING: canonical current-head GitHub CI after this governance commit and
  strict authenticated merge readiness.
- NOT RUN: local full `make verify`; prohibited by the repository local budget
  rule.

## Security Review

- PASS: mandatory post-open security-auditor found no actionable issue.
- PASS: sealed Codex Security scan
  `d3e49b4a-a801-4564-adcb-363ba4e5cb9d` covered all 14 exact-diff rows at
  `def03ed50991937c8a84b391160a8ba06014b609` and reported zero findings.
- PASS: sealed Codex Security scan
  `26e2d9fc-8859-43b3-a8dd-be6aebdeb1ec` covered both carried PR #2120 rows at
  `ba66c94938b02da01a7a2be263e8e3f76a897f06` and reported zero findings.
- PASS: coordinator packet `7857caa1a0f2` approved composing the two sealed
  scans because the reviewed path sets are disjoint and exact content/patch
  parity proves no changed security-relevant row. Governance-only body, ledger,
  and mapping edits do not reopen scanning. No additional scan was launched.
- PASS: `pulseplate-pr-review` found no correctness, architecture, test, or
  security defect. Its only notes were the then-missing fixed-mapping artifact,
  which this file supplies.

## Risks / Rollback

Rollback is forward-only. Do not restore setuptools 78.1.1 or any version
below 83.0.0, and do not restore the stale source-manifest review date. If
83.0.0 is incompatible or unavailable, keep install and release lanes blocked
and either repair the approved proxy or move to another tested patched 83.x
release through a separately reviewed dependency update. A future manifest
rollback must use a newly reviewed freshness date while preserving the same
artifact-integrity controls.

## Deferred / Follow-ups

- Close PR #2120 as superseded only after merged `main` is verified to contain
  the two carried manifest paths. Tracking:
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr2133-docker-manifest-prerequisite-consolidation`.
