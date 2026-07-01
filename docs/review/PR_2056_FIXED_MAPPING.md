# PR #2056 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2056

Branch: `codex/stabilize-main-nightly-nosec-ttl`

## Summary

This PR stabilizes the shared `main` CI and Nightly Full Tests failure caused by
expired `# nosec` TTL metadata in the Bandit suppression policy guard. It
removes avoidable B110 suppressions, refreshes still-required bounded
suppressions with a new TTL/ref, and adds TLS trusted-host mismatch coverage for
the B323 exception.

## Scope

- Replace avoidable B110 suppressions in non-critical metrics/db-fallback paths
  with debug logging.
- Remove now-unneeded B110/B105 suppressions where simple safe fixes exist.
- Refresh remaining justified suppressions to
  `remove-by: 2026-09-30, ref: PR-main-nightly-nosec-ttl`.
- Add deterministic coverage proving trusted-host TLS bypass remains exact-host
  scoped.
- Add PR-scoped premortem evidence.

## Out Of Scope

No PR #2053 worktree changes, PR #2054 creative-code changes, Dockerfile/image
policy changes, broad Bandit policy rewrites, or nosec allowlist expansion are
included.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/07e158339c7d.json`

Supplemental packet:
`artifacts/orchestration/task_packets/82da7727b5db.json`

Base/head root-cause evidence:

- `main` CI run `28497174542`, head
  `6571a4ba6181899330d0bec659328adfbb4bead0`, failed
  `tests/guards/test_nosec_policy_guard.py::test_nosec_policy_guard`.
- `Nightly Full Tests` run `28497874442`, same head, failed the same guard.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-f00e6e23de4e.json`

- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Experiment ID: `exp-f00e6e23de4e`
- Contribution kind: `commit_decision`
- Co-author required: `true`
- Commit trailer present in `e408dbd61`.

Zero-network local attempt:
`artifacts/orchestration/experiments/results/exp-405f31b46d8b.json` recorded
`status=rejected`, `failure_class=infra_flake`, because the macOS local
network-disabled sandbox lacked `unshare`.

## Discussion Thread Pass

- [x] Initial fixed-mapping artifact created after PR open.
- [ ] Post-open `qa-engineer-agent` pass completed.
- [ ] Post-open `bug-hunter` pass completed.
- [ ] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed or explicitly
  dispositioned.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit, Sourcery, and Cubic actionables checked and dispositioned.
- [ ] Review threads checked, dispositioned, and resolved if any appear.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS:
  `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/guards/test_nosec_policy_guard.py tests/test_install_locked_python_requirements.py::test_private_index_project_health_honors_matching_trusted_host tests/test_install_locked_python_requirements.py::test_private_index_project_health_uses_default_tls_for_mismatched_trusted_host -q`
  (`44 passed`)
- PASS:
  `.venv/bin/python -m pytest tests/test_metrics.py::test_record_legacy_alias_hit_swallows_counter_inc_errors tests/test_food_search_foundation.py::test_record_food_search_meili_performance_swallows_counter_and_histogram_errors tests/test_food_search_foundation.py::test_record_food_search_meili_stage_timing_noops_and_swallows_errors tests/test_philosophical_runtime.py::test_record_runtime_metrics_swallows_metric_failures tests/test_app_db_fallback_97.py::TestAppDBFallback97::test_configure_session_bindings_configure_raises -q`
  (`5 passed`)
- PASS: file-scoped Bandit on changed Python/security files exited `0` with
  Bandit comment warnings only.
- PASS: `make validate-changed` exited `0`; it was non-selective for this branch,
  so focused pytest and Bandit evidence above are primary.
- PASS: `pre-commit run --all-files` after Black formatted one touched line.
- PASS: commit hook.
- PASS: push hook, including changed-file mypy, `pip-audit`, backend pre-push
  pytest, full-repo Bandit, and Docker build test.

## Local Verification Exception

Local `make verify` was not run, per the repository local full-verify budget
rule. Full/heavy verification remains GitHub current-head CI.

## Merge Readiness

Not ready for merge. Current-head CI, post-open review/bot passes, review-thread
disposition checks, and strict merge-readiness remain required before any
readiness claim.
