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
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed or explicitly
  dispositioned.
- [x] `pulseplate-pr-review` completed.
- [x] CodeRabbit, Sourcery, and Cubic actionables checked and dispositioned.
- [x] Review threads checked, dispositioned, and resolved if any appear.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 602fe4e3413bf6c80cc0192337b7dbfa9a390baf
Evidence: `app/metrics.py` and `core/db_fallback.py` now include contextual debug logging for best-effort metric failures, and `tests/test_install_locked_python_requirements.py` no longer asserts an exact empty header dictionary in the trusted-host health-check tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2056#pullrequestreview-4607238059 -> 602fe4e3413bf6c80cc0192337b7dbfa9a390baf

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
- PASS: Post-open `qa-engineer-agent` rerun on head `10ac323d0` found no
  code/test blocker after the canonical mapping artifact was pushed and the PR
  body no longer overstated completion.
- PASS: Post-open `bug-hunter` found no code/runtime blocker; its governance
  formatting findings were fixed locally before this mapping update.
- PASS: Post-open `security-auditor` found no security blockers in the current
  working-tree diff or full PR diff, confirmed B323 remains exact-host scoped,
  and confirmed no PR #2053/worktree contamination.
- PASS: Codex Security diff scan `4a8ee676-c649-478f-adae-b58bd22ec421`
  completed for
  `6571a4ba6181899330d0bec659328adfbb4bead0..602fe4e3413bf6c80cc0192337b7dbfa9a390baf`
  with 13/13 diff-scoped rows closed and 0 reportable findings. Report:
  `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-Mt46cu/BMI-App_2025_clean/602fe4e3413bf6c80cc0192337b7dbfa9a390baf_20260701T090630Z_xd609rzt/report.md`.
- PASS: `pulseplate-pr-review` dry-run report generated at
  `/tmp/pr2056_pulseplate_pr_review_after_push.md` after the PR remote matched
  local head `59f156b23`. It found no deterministic code, security,
  architecture, QA, or bug-hunter blocker; the only note was the advisory
  large-diff planning signal, dispositioned by the combined main/nightly
  stabilization scope, post-open role passes, Codex Security scan, and targeted
  gates above.
- PASS: CodeRabbit status was `SUCCESS`; Cubic completed `NEUTRAL`; Sourcery's
  high-level review was fixed in `602fe4e34`.

## Local Verification Exception

Local `make verify` was not run, per the repository local full-verify budget
rule. Full/heavy verification remains GitHub current-head CI.

## Merge Readiness

Not ready for merge. Current-head CI and strict merge-readiness remain required
before any readiness claim.
