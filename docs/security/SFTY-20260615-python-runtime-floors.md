# SFTY-20260615 Python runtime dependency floors

## Summary

Safety 3.8.1 began reporting active high-gate findings for the current `main`
runtime lock after PR #1982 merged. This hotfix raises only the affected
repo-managed Python runtime floors:

| Package | Safety IDs | Previous repo pin | New repo floor |
| --- | --- | --- | --- |
| `cryptography` | `SFTY-20260615-96125` | `46.0.7` | `48.0.1` |
| `python-multipart` | `SFTY-20260615-29344`, `SFTY-20260615-09692`, `SFTY-20260615-38625`, `SFTY-20260615-86547` | `0.0.27` | `0.0.31` |
| `starlette` | `SFTY-20260615-86827`, `SFTY-20260615-22503`, `SFTY-20260615-83407`, `SFTY-20260615-32787` | `1.0.1` | `1.3.1` |

The scope is dependency-security only. It does not change application behavior,
legacy routes, OpenAPI, frontend, iOS, macOS, FoodDB, premium, exports, insight,
or planning engines.

## Repo Evidence

- Source floors: `requirements.in`, `requirements-ci-lite.in`,
  `requirements-docker-runtime.in`, `requirements-dev.in`, and `constraints.txt`
  require `cryptography>=48.0.1`, `python-multipart>=0.0.31`, and
  `starlette>=1.3.1`.
- Lock surfaces: `requirements.txt`, `requirements-ci-lite.txt`,
  `requirements-docker-runtime.txt`, `requirements-dev.txt`, and
  `requirements-lock.txt` pin `cryptography==48.0.1`,
  `python-multipart==0.0.31`, and `starlette==1.3.1`.
- Guard source of truth:
  `tests/fixtures/dependency_security_schema.json` records the same three
  minimum floors and blocks pinned `python-multipart<0.0.31`.
- Emergency fallback rotation:
  `scripts/ci/emergency_python_wheels.json` replaces the old
  `cryptography==46.0.7` and `python-multipart==0.0.27` artifacts with exact
  `cryptography==48.0.1` Linux x86_64 wheels and the exact
  `python-multipart==0.0.31` pure wheel, each pinned by `sha256`, with a
  short expiry of `2026-06-30`.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py tests/guards/test_security_devtooling_regression_guards.py tests/test_python_supply_chain_controls.py
python3 scripts/ci/run_safety_audit.py
make validate-changed
pre-commit run --all-files
```

Full local `make verify` is intentionally deferred for this machine-heavy
main-stabilization hotfix; current-head CI is the heavy verification signal.
