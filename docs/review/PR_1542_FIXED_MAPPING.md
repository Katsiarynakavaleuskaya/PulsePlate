# PR #1542 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1542>
Branch: `codex/fix-trivy-41989-suppression`
Date: 2026-04-26

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No actionable review comments were raised.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/586
- Evidence: `trivy/ignore-policy.rego`
- Evidence: `docs/security/CVE-2026-41989-libgcrypt20.md`
- Evidence: `docs/roadmap/BACKLOG_LEDGER.md`

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `pre-commit run --all-files` (PASS)
- `pytest -q 'tests/test_dependency_security_guard.py::test_dependency_security_guard_enforces_blocked_versions[surface6]'`
  (PASS, existing regression guard)
- `pytest -q tests/test_install_locked_python_requirements.py::test_repo_ruff_emergency_fallback_matches_dev_requirement_surfaces`
  (PASS, existing regression guard)
- Manual GitHub alert verification: <https://api.github.com/repos/Katsiarynakavaleuskaya/PulsePlate/code-scanning/alerts/586>
