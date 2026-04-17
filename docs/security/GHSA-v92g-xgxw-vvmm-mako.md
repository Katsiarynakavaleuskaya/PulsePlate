# GHSA-v92g-xgxw-vvmm - Mako

## Summary

- Package: `Mako`
- GHSA: `GHSA-v92g-xgxw-vvmm`
- Severity: `medium`
- Fixed version: `1.3.11`

This lane remediates the `Mako` advisory by raising the repo-managed security
floor to `1.3.11` across the governed Python source, dev, pinned, and CI-lite
requirement surfaces.

## Repo Evidence

- `requirements.in:39` - runtime source floor is `mako>=1.3.11,<2.0.0`
- `requirements-ci-lite.in:36` - CI-lite source floor is `mako>=1.3.11,<2.0.0`
- `requirements-dev.in:25` - dev tooling surface now carries `mako>=1.3.11,<2.0.0`
- `constraints.txt:51` - constraints floor is `mako>=1.3.11`
- `requirements.txt:103` - runtime lock pins `mako==1.3.11`
- `requirements-dev.txt:87` - dev lock pins `mako==1.3.11`
- `requirements-lock.txt:213` - full lock pins `mako==1.3.11`
- `requirements-ci-lite.txt:152` - CI-lite lock pins `mako==1.3.11`
- `scripts/ci/emergency_python_wheels.json:85-90` - exact wheel fallback records
  `mako==1.3.11` with artifact-scoped expiry and pinned `sha256`
- `tests/fixtures/dependency_security_schema.json:4` - dependency security schema
  records minimum safe version `1.3.11`

## Validation

```bash
.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
rg -n "mako|Mako" requirements.in requirements-ci-lite.in requirements-dev.in requirements.txt requirements-dev.txt requirements-lock.txt requirements-ci-lite.txt constraints.txt tests/fixtures/dependency_security_schema.json scripts/ci/emergency_python_wheels.json
python3 scripts/ci/install_locked_python_requirements.py --index-url "${PULSEPLATE_PYTHON_INDEX_URL}" --trusted-host "${PULSEPLATE_PYTHON_TRUSTED_HOST}" --preflight-only
```

## Notes

- The repo uses a schema-driven dependency guard, so the remediation must be
  reflected in both source manifests and the pinned lock surfaces.
- The floor is enforced explicitly rather than relying on the current Alembic
  transitive resolution, so future lock regeneration cannot drift back to the
  vulnerable `1.3.10` release.
- Current-head dependency-install evidence for the private-proxy lag and the
  exact-wheel fallback governance lives in
  `docs/security/MAKO_1_3_11_PRIVATE_INDEX_ADVISORY.md:5-18` and
  `docs/security/MAKO_1_3_11_PRIVATE_INDEX_ADVISORY.md:31-38`.
- This lane stays dependency-only; runtime and frontend behavior remain out of
  scope per
  `docs/orchestration/DEPENDABOT_ALERTS_114_116_REMEDIATION_TASK_PACKET_2026-04-17.md:101-106`.

## Temporary Seam Governance

- ADR: `docs/architecture/ADR_WAVE6_SECURITY_FLOOR_UNBLOCK_SEAM_2026-04-17.md:1-79`
- Seam backlog / DoD / blockers:
  `docs/roadmap/BACKLOG_LEDGER.md:1657-1678`
- Emergency-manifest retirement backlog:
  `docs/roadmap/BACKLOG_LEDGER.md:424-451`
