# Nightly Full Tests Triage — March 22, 2026

## Symptom
- Workflow: `Nightly Full Tests`
- Run: `23395469933`
- Job: `tests` (`68057604027`)
- Result: failed at `2026-03-22 04:21:31 UTC`
- Duration: `6m16s`

## Failure Signature
- Coverage completed successfully: `97.86%`
- Single failing test:
  - `tests/test_openapi_determinism.py::test_openapi_and_schema_ts_are_deterministic`
- Failing stderr tail from the run:
  - `Frontend commands require Node 22.22.1 or newer major runtime; current runtime is 20.20.1.`
  - `make: *** [Makefile:433: frontend-install] Error 1`

## Root Cause
- PR `#1209` (`96502f42`, `fix(ci): align frontend openapi sync with node 22`) raised the repo frontend/OpenAPI runtime contract to Node `22.22.1` via [`.nvmrc`](../../.nvmrc), [`frontend/package.json`](../../frontend/package.json), and [`scripts/frontend_npm.sh`](../../scripts/frontend_npm.sh).
- `Nightly Full Tests` did not get the same Node bootstrap as the working OpenAPI sync lane in CI, so `make openapi` inside [`tests/test_openapi_determinism.py`](../../tests/test_openapi_determinism.py) executed against the runner default Node `20.20.1`.
- A second drift was found in [`cd.yml`](../../.github/workflows/cd.yml): production gating still queried `nightly.yml` (`Nightly Tests`) instead of `nightly-tests.yml` (`Nightly Full Tests`).

## Chosen Fix
- Add Node `22.22.1` setup and frontend dependency bootstrap to [`nightly-tests.yml`](../../.github/workflows/nightly-tests.yml) before pytest.
- Point the production nightly gate in [`cd.yml`](../../.github/workflows/cd.yml) at `nightly-tests.yml`.
- Keep legacy `nightly.yml` intact for now; this triage only removes it from release gating.

## Repro Commands
```bash
python3 scripts/orchestration/check_preflight.py
make openapi
pytest -q tests/test_openapi_determinism.py
gh run view 23395469933 --job 68057604027 --log-failed
```

## Verification Plan
```bash
pre-commit run --all-files
make verify
gh workflow run "Nightly Full Tests" --ref fix/nightly-full-tests-node22-parity
```

## Links
- Failed run: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/23395469933>
- Failed job: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/23395469933/job/68057604027>
- Last green nightly full run before failure: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/23371563160>
- Regression introducer PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209>
