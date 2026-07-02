# Residual Runtime Dependency Ownership Premortem

## Scope

This PR settles the residual dependency-surface ownership debt after PR #2057
without repeating the earlier `pyarrow` runtime quarantine work.

## Failure Stories

1. `aiosqlite` ownership is promoted too broadly.
   - Impact: reviewers could read SQLite async fallback support as production DB
     authority.
   - Mitigation: ownership evidence is limited to `core/db.py` async SQLite URL
     derivation; docs state production/staging Postgres policy is unchanged.

2. The private proxy preflight guard blocks unrelated orchestration tasks.
   - Impact: non-dependency work becomes coupled to local package-proxy env
     drift.
   - Mitigation: malformed `PULSEPLATE_PYTHON_INDEX_URL` is warning-only in
     analyze mode and fail-closed only in execute/merge for dependency-sensitive
     paths.

3. `numpy` direct-owner cleanup creates hidden lock churn.
   - Impact: a narrow ownership PR becomes a resolver or unsafe-package change.
   - Mitigation: attempted regeneration was rejected after it introduced an
     unrelated unsafe `pip==` stanza in `requirements-lock.txt`; `numpy` remains
     direct warning-only debt for a future resolver-stable PR.

4. `pyarrow` runtime quarantine regresses.
   - Impact: data-profile-only Parquet support leaks back into runtime,
     Docker-runtime, CI-lite, or aggregate lock authority.
   - Mitigation: checker policy remains unchanged for `pyarrow`; this PR only
     fixes stale data-profile wording.

## Validation Focus

- `python3 scripts/ci/check_python_dependency_surfaces.py`
- `python3 verify_requirements.py`
- Focused pytest for dependency surfaces, preflight, and supply-chain docs
- `make validate-changed`
- `pre-commit run --all-files`
