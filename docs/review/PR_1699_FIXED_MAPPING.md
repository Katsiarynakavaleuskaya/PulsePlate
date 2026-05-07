# PR 1699 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1699
Branch: `ci/release-control-plane-evidence-publication`
Head at open: `9f6a655c63dc9facb94301265da024dd567dce47`

## Summary

This artifact records pre-open subagent findings and post-open governance
placeholders for PR #1699. Mapping is evidence after fix or disposition; it is
not a substitute for fixes.

## Pre-Open Subagent Findings

### Source runs are not allowlisted

Disposition: FIXED
Commit: `bfb94e11a`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml`
- `tests/test_release_control_plane_evidence_publication_workflow.py`

### Publication run SHA is not checked

Disposition: FIXED
Commit: `bfb94e11a`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml`
- `tests/test_release_control_plane_evidence_publication_workflow.py`

### Fixture/sample evidence and placeholder hashes can still validate

Disposition: FIXED
Commit: `bfb94e11a`
Evidence:

- `.github/workflows/release-control-plane-evidence.yml`
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md`
- `tests/test_release_control_plane_evidence_publication_workflow.py`

### Dependency audit blocked push

Disposition: FIXED
Commit: `9f6a655c6`
Evidence:

- `requirements.txt`
- `requirements-lock.txt`
- `requirements-ci-lite.txt`
- `requirements-docker-runtime.txt`
- `scripts/ci/emergency_python_wheels.json`
- `tests/fixtures/dependency_security_schema.json`
- `.secrets.baseline`
- `PATH=.venv/bin:$PATH pre-commit run pip-audit --hook-stage pre-push --all-files` passed.

## Post-Open Review Threads

No post-open human, CodeRabbit, Sourcery, or Cubic actionable review threads
were present when this artifact was created. Any later actionable review comment
must be added here with one of:

- `FIXED`: commit SHA plus evidence.
- `NOT-A-BUG`: evidence and rationale.
- `DEFERRED`: backlog link and rationale.

## Validation

- `.venv/bin/python scripts/orchestration/check_preflight.py` -> PASS
- `.venv/bin/python scripts/orchestration/check_agent_consistency.py` -> PASS
- `.venv/bin/python -m pytest -q tests/test_release_control_plane_evidence_publication_workflow.py tests/test_release_control_plane_ci_gate.py tests/test_production_release_evidence_wiring.py tests/test_build_equivalence.py tests/test_release_manifest.py tests/test_dependency_security_guard.py tests/test_install_locked_python_requirements.py` -> PASS
- `.venv/bin/python scripts/ci/check_docs_phase1_gates.py --files docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md docs/orchestration/RELEASE_CONTROL_PLANE_EVIDENCE_PUBLICATION_PACKET_2026-05-07.md docs/roadmap/BACKLOG_LEDGER.md docs/security/CVE-2026-40347-python-multipart.md docs/security/GHSA-v92g-xgxw-vvmm-mako.md` -> PASS
- `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` -> PASS
- `PATH=.venv/bin:$PATH pre-commit run --all-files` -> PASS
- `PATH=.venv/bin:$PATH pre-commit run pip-audit --hook-stage pre-push --all-files` -> PASS
- `git push -u origin ci/release-control-plane-evidence-publication` pre-push hooks -> PASS

## Merge Readiness

Not claimed. Merge readiness still requires current-head CI, review-thread
disposition, mandatory wait-window, and strict merge-readiness wrapper.
