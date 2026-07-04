# PR 2076 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2076

Branch: `codex/preflight-private-index-warning-scope`

## Summary

This PR scopes orchestration preflight diagnostics for
`PULSEPLATE_PYTHON_INDEX_URL` so unrelated startup/preflight lanes do not show
private-proxy warning noise while dependency-sensitive and ambiguous lanes stay
strict.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: f7858c9b20fac1da8271e646731761c36757a227
Evidence: scripts/orchestration/check_preflight.py now defines NONCANONICAL_PRIVATE_PROXY_ROOT_ERROR_CODE and reuses it for the suppression set and normalized-root diagnostic branch. tests/test_orchestration_preflight.py parametrizes ambiguous analyze warnings across non-credential private-index error codes. Covered by .venv/bin/python -m pytest -q tests/test_orchestration_preflight.py.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2076#discussion_r3523767563 -> f7858c9b20fac1da8271e646731761c36757a227
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2076#discussion_r3523767564 -> f7858c9b20fac1da8271e646731761c36757a227
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2076#pullrequestreview-4630182820 -> f7858c9b20fac1da8271e646731761c36757a227

Disposition: FIXED
Commit: f7858c9b20fac1da8271e646731761c36757a227
Evidence: tests/test_orchestration_preflight.py adds strict execute/merge coverage for noncanonical_private_proxy_root under ambiguous and dependency-sensitive scopes, and scripts/orchestration/check_preflight.py routes both validator and normalized-root diagnostics through _emit_private_index_diagnostic. Covered by .venv/bin/python -m pytest -q tests/test_orchestration_preflight.py.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2076#discussion_r3523771895 -> f7858c9b20fac1da8271e646731761c36757a227
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2076#pullrequestreview-4630186604 -> f7858c9b20fac1da8271e646731761c36757a227

## Role-Agent Evidence

- Pre-open packet: `artifacts/orchestration/task_packets/460f6432fcc7.json`
- Pre-open role order completed: `agent-coordinator -> cursor-specialist-agent -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist`.
- Post-open packet: `artifacts/orchestration/task_packets/b246ad7d1515.json`
- Current post-open packet: `artifacts/orchestration/task_packets/965672eaaf7c.json`
- Post-open coordinator found and cleared the stale PR head / missing canonical mapping artifact blocker before merge-readiness claims.
- Post-open QA found the missing noncanonical_private_proxy_root strict-path coverage and unmapped bot actionables; commit `f7858c9b20fac1da8271e646731761c36757a227` fixes them.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-9fdcd5c0aa05.json`

- Experiment id: `exp-9fdcd5c0aa05`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution kind: `commit_decision`
- `coauthor_required=true`
- Commit carrying required trailer: `a3138ad48dbffc9c94a23ed3634fca3df1d77ba9`
- Oracle commands passed: `python3 -m pytest -q tests/test_orchestration_preflight.py` and `python3 -m pytest -q tests/test_private_python_proxy_health.py`.

Infra caveat: the first zero-network local attempt recorded `status=rejected`
because this macOS development host did not provide `unshare` for the
network-disabled sandbox. The accepted `network_budget=1` artifact kept the
same local oracle commands and does not grant product runtime, provider,
client, dependency installer, or public API authority.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/460f6432fcc7.json`
Starter: `scripts/orchestration/start_pr_lane.sh`

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --mode analyze --path scripts/orchestration/check_preflight.py --path tests/test_orchestration_preflight.py` - PASS; no private-index warning for explicit non-dependency scope under the ambient wrong-root env.
- `python3 scripts/orchestration/check_preflight.py` - PASS; ambiguous no-path preflight still reports the private-index warning.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `.venv/bin/python -m pytest -q tests/test_orchestration_preflight.py` - PASS, 44 passed after bot-review fix coverage.
- `.venv/bin/python -m pytest -q tests/test_private_python_proxy_health.py` - PASS, 31 passed.
- `PULSEPLATE_PYTHON_INDEX_URL="https://packages.pulseplate.app/root/pulseplate/+simple/" python3 scripts/ci/install_locked_python_requirements.py --preflight-only` - PASS.
- `git diff --check` - PASS.
- `make validate-changed` - PASS after the implementation commit selected `tests/test_orchestration_preflight.py`.
- `pre-commit run --all-files` - PASS before push.

## Merge Readiness

Not claimed here. Requires current-head CI after the latest mapping/body commit,
strict merge-readiness gate, post-open role chain completion, Codex Security
diff scan/finding discovery when available, `pulseplate-pr-review`, and resolved
review threads.
