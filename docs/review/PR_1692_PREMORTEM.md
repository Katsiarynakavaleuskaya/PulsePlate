# PR #1692 Premortem

Mode: `pr-premortem`
Coordinator packet: `artifacts/orchestration/task_packets/954153912a69.json`

## Summary

PR #1692 replaces the fixture-only release-control-plane CI gate with a
production tag gate that checks real release evidence before build/deploy jobs.

Frame: It is 48 hours from now. This hotfix made production release automation
worse. We are looking backward to understand why.

Changed files inspected:

- `.github/workflows/cd.yml`
- `docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `tests/test_release_control_plane_ci_gate.py`
- `tests/test_python_supply_chain_controls.py`
- `docs/review/PR_1692_PREMORTEM.md`
- `docs/review/PR_1692_FIXED_MAPPING.md`

## Risk Table

| Priority | Failure mode | Finding | Required fix | Evidence | Disposition |
| --- | --- | --- | --- | --- | --- |
| P0 | Production deploy proceeds without release evidence | Production jobs now need `release-control-plane-gate`. | Keep gate in `needs` for build, deploy config, SSH deploy, and self-hosted deploy. | `tests/test_python_supply_chain_controls.py` dependency assertions | FIXED |
| P0 | Production build proceeds without gate | `build-production` depends on `release-control-plane-gate`. | Assert workflow dependency. | `tests/test_python_supply_chain_controls.py` | FIXED |
| P0 | Fixture evidence used in production path | Fixture job and fixture path are removed. | Assert no fixture job/path and real artifact paths. | `tests/test_release_control_plane_ci_gate.py` | FIXED |
| P0 | Release gate uses `continue-on-error` | Gate job has no `continue-on-error`. | Add workflow guard. | `tests/test_release_control_plane_ci_gate.py::test_workflow_integration_enforces_real_evidence_before_production_paths` | FIXED |
| P1 | No real artifact source or documented fail-closed operator path | No approved producer/downloader exists in this PR; choose Option B. | Document protected artifact requirement and ledger follow-up. | `docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md`; `docs/roadmap/BACKLOG_LEDGER.md` | FIXED |
| P1 | App Store/Fastlane upload behavior changed | Gate job contains no App Store/Fastlane secrets or upload behavior. | Keep release gate non-secret and test forbidden terms. | `tests/test_release_control_plane_ci_gate.py::test_workflow_integration_does_not_require_app_store_secrets` | FIXED |
| P1 | Normal PR path requires production artifacts or secrets | Gate runs only on production tags. | Keep `if: startsWith(github.ref, 'refs/tags/v')`. | `.github/workflows/cd.yml` | FIXED |
| P1 | Workflow `needs` graph is wrong | All production jobs include gate dependency. | Assert exact dependency graph. | `tests/test_python_supply_chain_controls.py` | FIXED |
| P2 | Checker output artifacts are not uploaded | Gate uploads JSON/Markdown decision artifacts with `always()`. | Assert upload-artifact and output paths in gate job. | `tests/test_release_control_plane_ci_gate.py` | FIXED |
| P2 | Gate blocks all tags without clear operator contract | This is intentional until real artifacts are supplied. | Document stop condition and ledger follow-up. | `docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md` | FIXED |

## Decision

PASS. No unresolved P0/P1 findings remain. Option B is explicit: production tags
fail closed until protected real release evidence is supplied.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `. .venv/bin/activate && pytest -q tests/test_release_control_plane_ci_gate.py` PASS
- `. .venv/bin/activate && pytest -q tests/test_python_supply_chain_controls.py` PASS
- `. .venv/bin/activate && pytest -q tests/test_repo_policy_guards.py` PASS
- `make validate-changed` PASS
- `pre-commit run --all-files` initially reformatted `tests/test_release_control_plane_ci_gate.py` with Black; rerun PASS after including the hook change.
