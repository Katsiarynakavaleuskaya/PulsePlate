# Scoped Validation Policy

Scoped validation is an evidence policy for narrow governance/tooling work. It
selects focused deterministic gates before PR open without weakening merge
readiness.

Default scoped lane evidence:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- focused pytest for touched helpers, policies, and routing seams
- `python -m py_compile` for new orchestration CLIs
- `make validate-changed`
- `pre-commit run --all-files`
- `git diff --check`

If `make validate-changed` selects no relevant new files, it is not sufficient
evidence by itself; add focused pytest for the changed surface.

Full `make verify` remains the local merge-readiness gold standard. Deferring it
requires the repo's documented machine-heavy exception and current-head CI
parity before any readiness claim.
