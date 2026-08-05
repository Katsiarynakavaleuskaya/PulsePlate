# Historical: SFTY-20260615 Python runtime dependency floors

## Status

This document preserves the June 2026 floor rotation. Its `46.0.7` and `48.0.1`
cryptography states are superseded. Current authority is
`docs/security/CRYPTOGRAPHY_50_0_0_ADVISORY_CLUSTER.md`; current evidence is
`requirements.in:43`, `requirements.txt:39`, and
`tests/fixtures/dependency_security_schema.json:4`. The emergency manifest is
now the retired empty marker recorded at
`scripts/ci/emergency_python_wheels.json:5`.

## Summary

Safety 3.8.1 began reporting active high-gate findings for the current `main`
runtime lock after PR #1982 merged. This historical hotfix raised only the
then-affected repo-managed Python runtime floors:

| Package | Safety IDs | Previous repo pin | Historical June 2026 floor |
| --- | --- | --- | --- |
| `cryptography` | `SFTY-20260615-96125` | `46.0.7` | `48.0.1` |
| `python-multipart` | `SFTY-20260615-29344`, `SFTY-20260615-09692`, `SFTY-20260615-38625`, `SFTY-20260615-86547` | `0.0.27` | `0.0.31` |
| `starlette` | `SFTY-20260615-86827`, `SFTY-20260615-22503`, `SFTY-20260615-83407`, `SFTY-20260615-32787` | `1.0.1` | `1.3.1` |

The scope is dependency-security only. It does not change application behavior,
legacy routes, OpenAPI, frontend, iOS, macOS, FoodDB, premium, exports, insight,
or planning engines.

## Repo Evidence

The following snapshot prose preserves the original remediation record without
claiming that its historical locations are current-tree line anchors. Current
cryptography evidence is recorded in the Status section above.

- The shared source manifests and `constraints.txt` recorded the then-current
  `cryptography>=48.0.1`, `python-multipart>=0.0.31`, and
  `starlette>=1.3.1` floors.
- The runtime, CI-lite, Docker-runtime, dev, and aggregate locks recorded
  `cryptography==48.0.1`, `python-multipart==0.0.31`, and
  `starlette==1.3.1`.
- `tests/fixtures/dependency_security_schema.json` recorded the same three
  historical minimum floors and blocked pinned `python-multipart<0.0.31`.
- The historical emergency manifest rotated from `cryptography==46.0.7` and
  `python-multipart==0.0.27` to exact `cryptography==48.0.1` Linux x86_64
  wheels and the exact `python-multipart==0.0.31` pure wheel, each then pinned
  by `sha256`, with a historical expiry of `2026-06-30`. These artifacts are no
  longer active.
- Historical fallback manifest renewal:
  the then-current manifest renewed the exact fallback TTL to `2026-06-30`
  under the existing
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-private-pypi-proxy-mirror-parity`
  tracking item. This is a time-boxed private-index mirror-lag bridge for the
  historically enumerated exact wheels, not a broad public-index bypass. The
  current marker is empty and retired as recorded in the Status section.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py tests/guards/test_security_devtooling_regression_guards.py tests/test_python_supply_chain_controls.py
make validate-changed
pre-commit run --all-files
```

`python3 scripts/ci/run_safety_audit.py` is auth-gated by `SAFETY_API_KEY`; it
is expected to run in current-head CI. Without that token, local execution
fails closed before scanning and is not local pass evidence.

Full local `make verify` is intentionally deferred for this machine-heavy
main-stabilization hotfix; current-head CI is the heavy verification signal.
