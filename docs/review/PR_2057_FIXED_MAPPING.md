# PR #2057 Fixed in Commit Mapping

Canonical review-governance artifact for PR #2057:
`chore(deps): enforce dependency ownership without expanding legacy authority`.

## Scope

- Enforce first-pass dependency ownership for the audited Python subset only:
  `pyarrow`, `pandas`, `httpx2`, `reportlab`, `matplotlib`, `numpy`, and
  `aiosqlite`.
- Remove `pyarrow` from runtime, CI-lite, aggregate, and constraints surfaces
  after confirming no canonical runtime owner, and guard Docker runtime against
  future `pyarrow` reintroduction.
- Keep `pyarrow` in data dependency surfaces.
- Preserve legacy compatibility as transitional evidence, not canonical runtime
  authority.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open pass status:

- `qa-engineer-agent`: found missing Docker-runtime `pyarrow` guard coverage
  and an incomplete `pyarrow` docs row. Fixed in `b68239aba`; final rerun found
  no blocking findings.
- `bug-hunter`: reviewed pyarrow removal boundaries, warning-only severity
  tiers, legacy-only ownership blocking, and generated requirement surfaces. No
  blocking findings at `b68239aba`.
- `security-auditor`: reviewed supply-chain/runtime authority boundaries,
  import-alias false-positive/negative risk, local-path leakage risk, and
  fail-closed checker behavior. No blocking findings at `b68239aba`.
- Codex Security diff scan `cb1de52e-4988-4fa8-a683-d214546a9a0c`: complete,
  14/14 worklist rows covered, 0 findings.
- `pulseplate-pr-review`: repo-governance review completed; current remaining
  blockers are CI/governance state, not code-review actionables.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2057#pullrequestreview-4608060018 -> b68239aba
Disposition: FIXED
Evidence: `scripts/ci/check_python_dependency_surfaces.py:120`, `scripts/ci/check_python_dependency_surfaces.py:404`, `scripts/ci/check_python_dependency_surfaces.py:408`, `tests/test_python_dependency_surfaces.py:443`, `tests/test_python_dependency_surfaces.py:491`, and `docs/contracts/PYTHON_DEPENDENCY_SURFACES.md:79`.
Reason: Sourcery's high-level feedback identified blind underscore-to-hyphen import normalization risk and a stale `ownership_ok` reason-code doc entry. Commit `b68239aba` replaced blind import normalization with explicit distribution/import aliases, added positive and negative alias tests, removed `ownership_ok`, and added Docker-runtime `pyarrow` regression coverage found by the follow-up QA pass.

## Implementing Commits

- `80c56590f` - `chore(deps): enforce dependency ownership`
- `94c903e1e` - `docs(review): add dependency ownership evidence`
- `4131cf325` - `fix(deps): satisfy dependency checker typing`
- `b68239aba` - `fix(deps): use explicit import ownership aliases`

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_python_dependency_surfaces.py`
- PASS: `python3 verify_requirements.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_python_dependency_surfaces.py tests/test_python_supply_chain_controls.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_openapi_namespace_guards.py tests/test_exports.py tests/test_bmi_visualization.py`
- PASS: `python3 scripts/ci/install_locked_python_requirements.py --preflight-only`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: `pre-commit run --hook-stage pre-push mypy --files scripts/ci/check_python_dependency_surfaces.py`
- PASS: `git diff --check`

Private proxy local evidence:

- PASS: `PULSEPLATE_PYTHON_INDEX_URL=https://packages.pulseplate.app/root/pulseplate/+simple/ python3 scripts/ci/check_private_python_proxy_health.py --requirements-file requirements.txt --requirements-file requirements-ci-lite.txt --requirements-file requirements-data.txt --project aiosqlite --project cryptography --project requests --project pyarrow --python-version 3.11 --python-version 3.12 --python-version 3.13`
- PASS: `PULSEPLATE_PYTHON_INDEX_URL=https://packages.pulseplate.app/root/pulseplate/+simple/ python3 scripts/ci/check_private_python_proxy_health.py --requirements-file requirements.txt --requirements-file requirements-ci-lite.txt --requirements-file requirements-data.txt --requirements-file requirements-test.txt --python-version 3.11 --python-version 3.12 --python-version 3.13`

Current-head CI observation at artifact creation:

- Superseded run `28518112575` on `b68239aba` was cancelled by newer same-head
  CI and is not current-head merge truth.
- Current same-head run `28518269941` on `b68239aba` completed successfully:
  `PR Body Phase2 gates`, `Merge readiness gate`, `Private Python proxy health`,
  `lint`, `security`, `OpenAPI sync`, `test-pr (3.13)`, `coverage-pr`, and
  `diff-coverage` passed.
- A later governance-only mapping update must still be rechecked before merge;
  this artifact does not replace the strict current-head merge-readiness wrapper.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/d608be4643c6.json`
- Packet: `artifacts/orchestration/task_packets/066b799335fb.json`

The packet paths are gitignored local provenance artifacts; they are recorded
for operator traceability and are not canonical product/runtime evidence.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-7bcba836ae3b.json`

Accepted oracle-only fallback evidence:

- PASS: `python3 scripts/ci/check_python_dependency_surfaces.py`
- PASS: `python3 verify_requirements.py`
- PASS: `python3 -m pytest -q tests/test_python_dependency_surfaces.py tests/test_python_supply_chain_controls.py`

Rejected attempt:

- `exp-732a3a092f3a` was rejected before oracle execution because the local
  zero-network sandbox required `unshare` on `PATH`.

## Security Notes

- No route, auth, billing, export runtime, LLM, secret, workflow-token, or
  deployment surface changed.
- The diff reduces runtime dependency surface by removing `pyarrow` from
  runtime, CI-lite, aggregate, and constraints surfaces while keeping data/eval
  ownership intact.
- Legacy import evidence remains `legacy_compat_transitional`; it cannot create
  canonical runtime authority.

## Merge Readiness

- [ ] Current-head CI is green.
- [ ] Private proxy health is green or reclassified with current evidence.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`.
- [ ] Required review wait-window completed.

Merge readiness is not claimed in this artifact.
