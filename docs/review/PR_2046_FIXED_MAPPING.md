# PR 2046 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2046
Title: `ci(deps): prove private proxy mirror parity and retire emergency wheel fallbacks`
Branch: `codex/retire-emergency-wheel-fallbacks`

## Summary

This PR retires the runtime-effective emergency wheel fallback manifest after
the approved private Python proxy mirror parity proof. It keeps
`scripts/ci/emergency_python_wheels.json` as a schema-preserving empty
compatibility marker, adds an all-entry active-manifest parity checker, and
wires the checker into the existing private proxy health job.

## Lane Start Provenance

- Base after rebase: `56638a565de03bb7d4ae9a7c8289d759650886a9`
  (`feat(orchestration): add review fallback learning loop (#2028)`)
- Original post-#2036 planning SHA:
  `b28bad895ece063d5bfddc95aa326cd19b73cd13`
- Current branch head at PR open: `9af0917c1`
- Packet: `artifacts/orchestration/task_packets/f0ac59f07485.json`
- Declared role order:
  `agent-coordinator -> dev-operator -> security-auditor -> qa-engineer-agent -> bug-hunter`
- Experiment Runner oracle:
  `artifacts/orchestration/experiments/results/exp-9f9bdba0070d.json`
  (`status=accepted`, `contribution_kind=commit_decision`)

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-9f9bdba0070d.json`

## Main Baseline Checks

- PR #2036 is merged:
  https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2036
- Current main push CI at `56638a565de03bb7d4ae9a7c8289d759650886a9`
  completed successfully.
- `Nightly Full Tests` completed successfully for
  `b28bad895ece063d5bfddc95aa326cd19b73cd13` on
  2026-06-29 (`run 28353580504`).

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Pre-open discussion-thread pass completed for local role-agent and premortem findings.
- [x] Fixed mapping artifact created after PR number allocation.
- [x] Post-open qa-engineer-agent pass completed; actionable findings fixed or recorded below.
- [x] Post-open review-agent pass completed:
  `bug-hunter -> security-auditor`.
- [x] Codex Security diff scan / finding discovery completed; candidate
  `CS-2046-001` fixed below.
- [x] `pulseplate-pr-review` completed; advisory large-diff note recorded below.
- [ ] CodeRabbit, Sourcery, Cubic, current-head CI, and strict merge-readiness
  wrapper remain required before merge.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 9af0917c1
Evidence: `scripts/ci/check_emergency_wheel_mirror_parity.py`, `tests/test_emergency_wheel_mirror_parity.py`, `tests/test_private_python_proxy_workflow_contract.py`, and `.github/workflows/ci.yml`.
Reason: Adds fail-closed all-entry emergency wheel parity against the approved private proxy and places it after the representative proxy health step.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2046 -> 9af0917c1

Disposition: FIXED
Commit: 9af0917c1
Evidence: `scripts/ci/install_locked_python_requirements.py`, `scripts/ci/emergency_python_wheels.json`, and `tests/test_install_locked_python_requirements.py`.
Reason: Retires the runtime-effective emergency manifest as a dated empty compatibility marker and keeps arbitrary empty manifests fail-closed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2046 -> 9af0917c1

Disposition: FIXED
Commit: 9af0917c1
Evidence: `RUNBOOK_AGENT.md`, `docs/DEPENDENCY_MANAGEMENT.md`, `docs/roadmap/BACKLOG_LEDGER.md`, and `docs/review/PR_EMERGENCY_WHEEL_MIRROR_PARITY_PREMORTEM.md`.
Reason: Documents representative health versus all-entry parity, records premortem finding closure, and marks runtime-effective emergency fallbacks retired while leaving full compatibility-path removal as follow-up scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2046 -> 9af0917c1

Disposition: FIXED
Commit: 24270cb8c
Evidence: `scripts/ci/check_emergency_wheel_mirror_parity.py` compares Simple API `#sha256` fragments to manifest hashes; `tests/test_emergency_wheel_mirror_parity.py` covers digest mismatch failure.
Reason: Post-open qa-engineer-agent found exact filename parity without mirrored digest parity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2046#discussion_r3491263033 -> 24270cb8c

Disposition: FIXED
Commit: 24270cb8c
Evidence: `.github/workflows/ci.yml` creates `pulseplate-private-proxy-health-netrc-created` only when protected-main auth writes `.netrc`; cleanup removes `.netrc` only when that marker exists; `tests/test_private_python_proxy_workflow_contract.py` enforces the marker contract.
Reason: Post-open qa-engineer-agent found protected-main cleanup could delete a pre-existing runner `.netrc` after the configure step refused overwrite.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2046#discussion_r3491263044 -> 24270cb8c

Disposition: NOT-A-BUG
Evidence: `scripts/ci/check_emergency_wheel_mirror_parity.py` intentionally fails closed with `simple_page_truncated` before trusting a partial Simple API page; this is documented in validation as a proxy health signal rather than a filename miss.
Reason: Post-open qa-engineer-agent classified truncation-before-visible-filename as a false-red risk only; the fail-closed behavior is intentional for supply-chain parity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2046#discussion_r3491263041

Disposition: FIXED
Commit: 34a7d9ced
Evidence: `.github/workflows/ci.yml` now touches `pulseplate-private-proxy-health-netrc-created` before writing `$HOME/.netrc`; `tests/test_private_python_proxy_workflow_contract.py` asserts the marker-before-write ordering.
Reason: Codex Security candidate `CS-2046-001` found that a failure after writing `.netrc` but before marker creation could leave protected-main devpi credentials behind until runner cleanup.

Disposition: NOT-A-BUG
Evidence: The large line count is driven by retiring the active 34-entry emergency manifest payload and adding deterministic parity tests/docs for the same narrow infra/dependency lane; `make validate-changed` and `pre-commit run --all-files` passed for the current branch.
Reason: `pulseplate-pr-review` flagged an advisory `note` for `changed_lines > 800`; it did not identify an actionable code, security, or workflow defect.

Disposition: FIXED
Commit: f80f8be31
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` records PR #2046 as the target PR for the closed retired emergency manifest, Pillow fallback, and Mako fallback ledger items. `tests/test_emergency_wheel_mirror_parity.py` covers `simple_page_sha256_missing` and `simple_page_sha256_invalid`.
Reason: CodeRabbit found closed ledger items still using `PR-TBD` target metadata and requested focused branch coverage for missing/malformed Simple API `#sha256` fragments.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2046#discussion_r3493341332 -> f80f8be31
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2046#pullrequestreview-4593728060 -> f80f8be31

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path ...` PASS.
- `python -m pytest -q tests/test_emergency_wheel_mirror_parity.py tests/test_private_python_proxy_health.py tests/test_private_python_proxy_workflow_contract.py` PASS.
- `python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py` PASS.
- `python3 scripts/ci/check_emergency_wheel_mirror_parity.py --manifest scripts/ci/emergency_python_wheels.json --python-version 3.11 --python-version 3.12 --python-version 3.13 --format text` PASS with `retired=true artifacts=0 missing=0`.
- Representative live proxy health PASS on rerun with `--timeout 20 --retries 2`.
- Active pre-retirement manifest all-entry parity PASS before final rebase for
  the unchanged manifest with `artifacts=34 missing=0`; later reruns showed
  current proxy read-timeout flakiness on large project pages, not filename
  misses.
- Active `origin/main` manifest parity with digest comparison: full run reached
  `artifacts=34` with 22 `ok` and 12 transient proxy health failures
  (`tls_or_connect_timeout` / `origin_unhealthy`); immediate failed-artifact
  subset retry passed with `artifacts=12 missing=0`, proving no remaining exact
  filename or `#sha256` parity gaps on the failed set.
- `python3 scripts/ci/install_locked_python_requirements.py --preflight-only` PASS with the approved proxy.
- `make venv-sync` PASS.
- `make validate-changed` PASS.
- `pre-commit run --all-files` PASS.
- Push pre-push hooks PASS, including changed-file mypy, pip-audit, backend
  tests, full-repo Bandit, and Docker build test.
- `python -m pytest -q tests/test_emergency_wheel_mirror_parity.py tests/test_private_python_proxy_workflow_contract.py` PASS after post-open QA fixes.
- `python3 scripts/ci/check_emergency_wheel_mirror_parity.py --manifest scripts/ci/emergency_python_wheels.json --index-url https://packages.pulseplate.app/root/pulseplate/+simple/ --python-version 3.11 --python-version 3.12 --python-version 3.13 --format text` PASS with `retired=true artifacts=0 missing=0`.
- `python -m pytest -q tests/test_private_python_proxy_workflow_contract.py` PASS after Codex Security `CS-2046-001` fix.
- `GH_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_review_threads_disposition.py --pr-number 2046 --require-auth` PASS.
- Codex Security diff scan completed; candidate `CS-2046-001` fixed in
  `34a7d9ced`; no surviving reportable findings.
- `pulseplate-pr-review` dry-run report completed; 1 advisory large-diff note
  classified `NOT-A-BUG` above.
- Current-head CI PASS on `0241f897a` after merging `origin/main` with PR #2047
  billing fix and PR #2041 proxy-skip gate fix.
- `python -m pytest -q tests/test_emergency_wheel_mirror_parity.py tests/test_private_python_proxy_workflow_contract.py tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py` PASS after CodeRabbit fixes.
- `make validate-changed` PASS after CodeRabbit fixes.
- `pre-commit run --all-files` PASS after CodeRabbit fixes.

## Merge Readiness

Not merge-ready yet. Post-open role passes, Codex Security diff scan/finding
discovery, and `pulseplate-pr-review` are completed with actions/dispositions
recorded above. The CodeRabbit follow-up fix and mapping still need to be pushed,
review-thread disposition rechecked, and current-head CI rerun before any
merge-readiness claim.
