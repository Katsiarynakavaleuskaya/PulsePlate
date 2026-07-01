# PR #2057 Fixed in Commit Mapping

Canonical review-governance artifact for PR #2057:
`chore(deps): enforce dependency ownership without expanding legacy authority`.

## Scope

- Enforce first-pass dependency ownership for the audited Python subset only:
  `pyarrow`, `pandas`, `httpx2`, `reportlab`, `matplotlib`, `numpy`, and
  `aiosqlite`.
- Remove `pyarrow` from runtime, CI-lite, aggregate, and constraints surfaces
  after confirming no canonical runtime owner.
- Keep `pyarrow` in data dependency surfaces.
- Preserve legacy compatibility as transitional evidence, not canonical runtime
  authority.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open pass status:

- `qa-engineer-agent`: reviewed the dependency checker, focused tests,
  generated requirements surfaces, and docs. No actionable defect found.
- `bug-hunter`: reviewed pyarrow removal boundaries, warning-only severity
  tiers, and legacy-only ownership blocking. No actionable defect found.
- `security-auditor`: reviewed supply-chain/runtime authority boundaries,
  local-path leakage risk, and fail-closed checker behavior. No actionable
  defect found.
- Codex Security diff scan `cb1de52e-4988-4fa8-a683-d214546a9a0c`: complete,
  14/14 worklist rows covered, 0 findings.
- `pulseplate-pr-review`: repo-governance review completed; current remaining
  blockers are CI/governance state, not code-review actionables.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2057#pullrequestreview-4608060018
Disposition: NOT-A-BUG
Evidence: Sourcery generated a reviewer guide and file-level summary for this dependency-surface PR, with no inline code-review defect requiring a code or docs change.
Reason: This bot review is governance-relevant feedback, not an actionable implementation defect.

## Implementing Commits

- `80c56590f` - `chore(deps): enforce dependency ownership`
- `94c903e1e` - `docs(review): add dependency ownership evidence`
- `4131cf325` - `fix(deps): satisfy dependency checker typing`

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

- `PR Body Phase2 gates`: failing only because this artifact did not exist yet.
- `Merge readiness gate`: failing only because this artifact did not exist yet.
- `Private Python proxy health`: failing on upstream mirror `HTTP 502`
  responses for `cryptography`, `requests`, `pytest-xdist`, `hypothesis`, and
  `pgvector`; `aiosqlite` returned `200`.
- `RAG Release Gates Smoke`: failing on an unrelated scheduled/smoke lane, not
  caused by this dependency-surface diff.

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
