# PR #1646 Fixed in Commit Mapping

## Summary

PR #1646 adds Docker devcontainer foundation for PulsePlate local development while preserving `make venv` as fallback.

## Scope

- `.devcontainer/Dockerfile`, `.devcontainer/devcontainer.json`, `.devcontainer/docker-compose.devcontainer.yml`
- `Makefile` — `DEV_PYTHON` + devcontainer targets
- `README.md`, `CONTRIBUTING.md` — devcontainer workflow docs
- `tests/test_devcontainer_foundation.py` — 10 guard tests
- `docs/roadmap/BACKLOG_LEDGER.md` — 3 ledger items

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1646#discussion_r3178310427
  Disposition: FIXED
  Commit: c3efc4e78
  Evidence: docs/roadmap/BACKLOG_LEDGER.md — P2 entries moved after P1 entries to maintain priority sort order

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1646#discussion_r3178310429
  Disposition: NOT-A-BUG
  Evidence: tests/test_devcontainer_foundation.py:70-80 — guard intentionally scopes to known dangerous patterns (INDEX_URL, TRUSTED_HOST) rather than blocking all ARGs, because devcontainer base images may declare legitimate ARGs
  Reason: Narrowly-scoped pattern matching is intentional for foundation guard; tighter blocking can be added as follow-up if more secrets surfaces emerge

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1646#discussion_r3178331047
  Disposition: FIXED
  Commit: c3efc4e78
  Evidence: Makefile:571-573 — replaced symlink-only approach with `python3 -m venv .venv --without-pip` + symlink, so both `$(VENV_PYTHON)` and `source .venv/bin/activate` work inside container

## Deferred / Follow-ups

- [P2: CI devcontainer smoke job](docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-devcontainer-ci-smoke)
- [P2: Makefile DEV_PYTHON migration](docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-makefile-dev-python-migration)

## Validation

- `pytest -q tests/test_devcontainer_foundation.py` — 10/10 PASS
- `make test-fast` — PASS
- `pre-commit run --all-files` — PASS

## Merge Readiness

- [ ] CI green
- [x] review mapping artifact created
- [ ] no actionable bot comments remain
- [ ] mandatory wait-window elapsed
