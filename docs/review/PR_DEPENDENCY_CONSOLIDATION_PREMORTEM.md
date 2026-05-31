# Premortem: Governed Dependabot Dependency Consolidation

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Packet: `artifacts/orchestration/task_packets/0bec9cf9c850.json`

## Frame

It is one week from now. The consolidated dependency PR either broke local/CI
Python installs or obscured which Dependabot changes were actually accepted. We
are looking backward to understand why.

## Scope Inspected

- `constraints.txt`
- `requirements-all.txt`
- `requirements-ci-lite.in`
- `requirements-ci-lite.txt`
- `requirements-dev.in`
- `requirements-dev.txt`
- `requirements-lock.txt`
- `requirements-test.in`
- `requirements-test.txt`
- `requirements.txt`
- `tests/test_install_locked_python_requirements.py`
- `tests/test_python_supply_chain_controls.py`
- Dependabot PRs `#1854`, `#1855`, `#1856`, and `#1857`

## Failure Modes

### P1: Consolidation leaves manifest and lock pins inconsistent

**Failure story:** Each Dependabot PR passed its own generated diff, but the
manual consolidation kept only part of a bump. `constraints.txt` allowed a new
version while one of the generated lock files still pinned the old version, so
local installs and CI lanes resolved different tool versions.

**Containment:** Verify every accepted pin across the relevant source and lock
files before push:

- `coverage>=7.14.1` and `coverage[toml]==7.14.1`
- `pytest-asyncio>=1.4.0` and `pytest-asyncio==1.4.0`
- `hypothesis~=6.155.1` and `hypothesis==6.155.1`
- `ruff>=0.15.15` and `ruff==0.15.15`
- `safety>=3.8.1`
- `diff-cover>=10.3.0` and `diff-cover==10.3.0`

### P1: Private index lacks one of the exact wheels

**Failure story:** Public Dependabot resolution succeeded, but the private
PulsePlate Python index did not yet mirror one exact wheel. CI or operator
machines using `PULSEPLATE_PYTHON_INDEX_URL` failed during installation, and the
failure was misdiagnosed as a SQLite regression.

**Containment:** Run the private-index exact-wheel validation when
`PULSEPLATE_PYTHON_INDEX_URL` is available. If the variable is unavailable or a
wheel is missing, keep the PR open and record the blocked validation explicitly.

### P2: Generated unsafe-package entries are accepted without reproduction

**Failure story:** Dependabot regenerated `requirements-dev.txt` and added an
unsafe `pip==26.1.1` entry. The consolidation copied that output without
checking whether local pip-tools reproduces it, creating unexplained lock churn.

**Containment:** Reject generated `pip==...` lock churn because
`tests/test_dependency_security_guard.py` forbids repo-managed lock surfaces
from pinning pip as an unsafe package. Treat other generated lock churn as
acceptable only when it matches the Dependabot source PRs and survives
`install_locked_python_requirements.py --preflight-only` plus focused
supply-chain guards.

### P2: Runtime/toolchain pin alignment leaks into this dependency PR

**Failure story:** While touching requirements, the PR also changed Python,
Ruby, Docker, Node, or iOS release pins. That widened review scope, mixed
different rollback paths, and made it harder to close the original Dependabot
updates.

**Containment:** Keep this PR limited to Python dependency manifests and the
premortem/fixed-mapping review artifacts. Runtime alignment remains PR2.

### P2: SQLite architecture failures are bundled into dependency cleanup

**Failure story:** Existing SQLite-backed test fragility appeared during local
validation, and the PR absorbed unrelated DB/test architecture fixes. The
dependency lane became a broad stabilization PR instead of an auditable bump.

**Containment:** Only fix SQLite behavior here if a changed dependency produces
a fresh, reproducible regression. Otherwise, record SQLite as a separate lane.

## Required Validation

- `python3 scripts/orchestration/check_preflight.py --path ...`
- `python scripts/orchestration/check_agent_consistency.py`
- exact-pin consistency checks across the changed requirement files
- private-index exact-wheel checks when `PULSEPLATE_PYTHON_INDEX_URL` is set
- `python scripts/ci/install_locked_python_requirements.py --preflight-only`
- focused dependency and supply-chain guards
- `make validate-changed`
- `pre-commit run --all-files`
- current-head CI after the governed PR is opened

## Decision

Proceed with PR1 only. Do not close the superseded Dependabot PRs until the
governed PR is open and the consolidated diff has been validated against the
accepted pin set.
