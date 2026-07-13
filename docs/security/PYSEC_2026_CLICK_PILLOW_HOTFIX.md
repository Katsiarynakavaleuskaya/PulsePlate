# PYSEC-2026 Click and Pillow security hotfix

## Summary

The repository pre-push `pip-audit` gate reported the following findings on the
shared Python dependency graph:

- Click `8.3.1`: `PYSEC-2026-2132`, fixed in `8.3.3`.
- Pillow `12.2.0`: `PYSEC-2026-2253`, `PYSEC-2026-2254`,
  `PYSEC-2026-2255`, `PYSEC-2026-2256`, and `PYSEC-2026-2257`, fixed in
  `12.3.0`.

This hotfix raises explicit security floors without changing product behavior,
OpenAPI, Docker image construction, or the private Python package source.

## Remediation contract

- Shared runtime, Docker-runtime, CI-lite, and dev sources declare Click
  `>=8.3.3,<9.0.0` and Pillow `>=12.3.0,<13.0.0`.
- `constraints.txt` keeps exact `8.3.3` / `12.3.0` parity with pinned lock
  surfaces.
- `tests/fixtures/dependency_security_schema.json` makes both fixed releases
  fail-closed minimums across the shared guard surfaces.
- Runtime, Docker-runtime, CI-lite, dev, aggregate, and optional-vector locks
  no longer retain an affected Click or Pillow pin.
- The approved package source remains the credential-free canonical devpi root
  `https://packages.pulseplate.app/root/pulseplate/+simple/`; no public index or
  emergency-wheel fallback is introduced.

## Resolver evidence

The checked-in runtime and Docker-runtime lock headers record targeted,
proxy-safe `pip-compile` commands with `--no-emit-index-url`; their exact Click
and Pillow pins are visible in the same files. After the private proxy stalled
during the next seeded resolution, the remaining affected locks received only
the already-resolved exact pins and provenance annotations. Deterministic tests
enforce the resulting floors, exact Click/Pillow pins, and the repository-wide
ban on `pip==...` entries across repo-managed lock surfaces.

Private-proxy responses, interpreter/tool versions, and command transcripts are
local operator evidence and are intentionally gitignored. They supported the
PR decision but are not presented as durable checked-in proof.

## Evidence anchors

- `requirements.in:5-17`
- `requirements-docker-runtime.in:10-22`
- `requirements-ci-lite.in:12-23`
- `requirements-dev.in:24-28`
- `constraints.txt:39-43`
- `requirements.txt:1-6`
- `requirements.txt:31-124`
- `requirements-docker-runtime.txt:1-6`
- `requirements-docker-runtime.txt:44-168`
- `requirements-ci-lite.txt:56-241`
- `requirements-dev.txt:42-154`
- `requirements-lock.txt:63-297`
- `requirements-rag-vector.txt:80`
- `requirements-rag-vector-cpu.txt:80`
- `tests/fixtures/dependency_security_schema.json:2-9`
- `tests/test_dependency_security_guard.py:31-37`
- `tests/test_dependency_security_guard.py:606-635`
- `tests/test_python_supply_chain_controls.py:1210-1261`

## Validation

```bash
python3 scripts/ci/check_python_dependency_surfaces.py
python3 scripts/ci/check_docs_phase1_gates.py \
  --files docs/security/PYSEC_2026_CLICK_PILLOW_HOTFIX.md \
          docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md
.venv/bin/python -m pytest -q \
  tests/test_dependency_security_guard.py \
  tests/test_python_supply_chain_controls.py
git diff --check
```

## Rollback

Revert the hotfix as one PR only if the release causes a confirmed compatibility
regression. Until a supported replacement is deployed, Python dependency install
and release lanes must remain blocked rather than restoring affected pins or
bypassing the private proxy.
