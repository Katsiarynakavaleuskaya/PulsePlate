# PR #1690 Premortem

Mode: `pr-premortem`
Coordinator packet: `artifacts/orchestration/task_packets/954153912a69.json`

## Summary

PR #1690 keeps the Codecov upload token out of frontend CI build code by removing
the build-step `CODECOV_TOKEN` environment variable and removing `uploadToken`
from `frontend/vite.config.ts`.

Frame: It is 48 hours from now. This hotfix made the Codecov alert worse. We are
looking backward to understand why.

Changed files inspected:

- `.github/workflows/frontend-ci.yml`
- `frontend/vite.config.ts`
- `tests/test_python_supply_chain_controls.py`
- `docs/review/PR_1690_PREMORTEM.md`
- `docs/review/PR_1690_FIXED_MAPPING.md`

## Risk Table

| Priority | Failure mode | Finding | Required fix | Evidence | Disposition |
| --- | --- | --- | --- | --- | --- |
| P0 | `CODECOV_TOKEN` still reaches frontend build env | The original patch removes the token from `Build frontend`; no remaining build-step secret env found. | Add a guard that parses the workflow and asserts the build step has no `CODECOV_TOKEN` or `secrets.CODECOV_TOKEN`. | `tests/test_python_supply_chain_controls.py::test_frontend_build_keeps_codecov_token_out_of_branch_controlled_build` | FIXED |
| P0 | Vite config still reads `process.env.CODECOV_TOKEN` | The original patch removes `uploadToken`; no token read remains in `frontend/vite.config.ts`. | Add a guard asserting no `uploadToken` and no `process.env.CODECOV_TOKEN` in Vite config. | `tests/test_python_supply_chain_controls.py::test_frontend_build_keeps_codecov_token_out_of_branch_controlled_build` | FIXED |
| P1 | Bundle analysis runs on PRs or feature branches | The workflow expression enables analysis only for `push` on `refs/heads/main`. | Assert exact branch-controlled expression in workflow guard. | `tests/test_python_supply_chain_controls.py::test_frontend_build_keeps_codecov_token_out_of_branch_controlled_build` | FIXED |
| P1 | Trusted main build breaks because no token is passed to Vite | The build no longer depends on a Vite `uploadToken`; Codecov credentials are not available to branch-controlled build code. | Keep token out of build env and do not configure upload credentials in Vite. | `frontend/vite.config.ts` omits `uploadToken` | FIXED |
| P1 | Secret is available to branch-controlled code | No frontend build env secret remains in the changed build step. | Workflow guard checks no secret reference in the build step. | `tests/test_python_supply_chain_controls.py` | FIXED |
| P1 | Duplicate PR risk causes the same patch to merge twice | #1690 and #1691 have identical head SHA `38938e599795f9983a2768ac43cde317132cc849`; only #1690 is canonical. | Merge #1690 only, then close #1691 as duplicate with explicit comment. | GitHub PR metadata inspection | FIXED |

## Decision

PASS. No unresolved P0/P1 findings remain after the workflow/config guard and
duplicate handling plan.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `. .venv/bin/activate && pytest -q tests/test_python_supply_chain_controls.py` PASS
- `. .venv/bin/activate && pytest -q tests/test_repo_policy_guards.py` PASS
- `make validate-changed` PASS
- `pre-commit run --all-files` PASS

Ambient `pytest` without `.venv` failed before collection with
`ModuleNotFoundError: No module named 'fastapi'`; direct pytest reruns used the
repo virtualenv as required by `AGENTS.md`.
