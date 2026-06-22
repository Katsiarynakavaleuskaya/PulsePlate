# GHSA-6v7p-g79w-8964 - msgpack Unpacker crash

## Status

Remediated in this branch for the repo surfaces that carry the vulnerable
`msgpack` pin. The `requirements-ci-lite.txt` Dependabot alert remains a graph
attribution recheck until a direct repo-owned `ci-lite` dependency path is
proven.

## Alert

- Tool: GitHub Dependabot
- Package: `msgpack`
- Ecosystem: pip
- Advisory: `GHSA-6v7p-g79w-8964`
- Severity: HIGH
- Vulnerable range: `<=1.2.0`
- Fixed version: `1.2.1`
- Open alerts observed on 2026-06-22: `#225`, `#226`, `#227`

## Current Repo State

The current repo-owned vulnerable pins are in the development and combined
development/runtime lock surfaces:

- `requirements-dev.txt:108` - replaced the prior `msgpack==1.1.2` pin.
- `requirements-lock.txt:210` - replaced the prior `msgpack==1.1.2` pin.
- `requirements-dev.in:27` - new explicit floor `msgpack>=1.2.1,<2.0.0`.
- `tests/fixtures/dependency_security_schema.json:16` - guard blocks
  `msgpack <1.2.1`.

`requirements-ci-lite.in` and `requirements-ci-lite.txt` do not contain a direct
`cachecontrol` or `msgpack` requirement on current `origin/main`. The live
Dependabot alert `#225` names `requirements-ci-lite.txt` as a transitive
manifest, but this PR does not add unused packages to `ci-lite` just to satisfy
scanner attribution. Recheck the alert after GitHub dependency graph refreshes;
if it remains open, use a new packet to prove the actual `ci-lite` dependency
path before touching that profile.

## Exposure Assessment

The advisory describes an availability issue: repeated `Unpacker` reuse after a
caught error can crash the process when unpacking untrusted input. PulsePlate has
not proven product-runtime use of `msgpack`; the current direct repo evidence is
dev tooling and combined lock exposure through `CacheControl` / `pip-audit`.

## Remediation

This branch:

1. Adds an explicit development-profile floor for `msgpack>=1.2.1,<2.0.0`.
2. Pins `msgpack==1.2.1` in `requirements-dev.txt` and `requirements-lock.txt`.
3. Adds `blocked_versions.msgpack: ["<1.2.1"]` so vulnerable pinned versions
   cannot return without forcing `msgpack` into unrelated requirement surfaces.
4. Records the seven-alert lane boundary in
   `docs/security/DEPENDABOT_ALERT_INVENTORY.md`.

## Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-msgpack-ci-lite-alert-recheck`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-python-dependency-surface-contract`

## Validation

```bash
python3 scripts/orchestration/check_preflight.py --path requirements-dev.in --path requirements-dev.txt --path requirements-lock.txt --path tests/fixtures/dependency_security_schema.json --path docs/security --path docs/DEPENDENCY_MANAGEMENT.md --path docs/roadmap/BACKLOG_LEDGER.md
python3 scripts/orchestration/check_agent_consistency.py
pytest -q tests/test_dependency_security_guard.py
python3 scripts/ci/check_docs_phase1_gates.py --files docs/security/GHSA-6v7p-g79w-8964-msgpack.md
make validate-changed
pre-commit run --all-files
```

## References

- <https://github.com/advisories/GHSA-6v7p-g79w-8964>
- <https://osv.dev/vulnerability/GHSA-6v7p-g79w-8964>
- <https://github.com/msgpack/msgpack-python/releases/tag/v1.2.1>
