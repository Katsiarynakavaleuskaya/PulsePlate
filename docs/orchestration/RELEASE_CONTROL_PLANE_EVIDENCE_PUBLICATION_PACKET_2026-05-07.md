# Release Control Plane Evidence Publication Packet

Date: 2026-05-07

## Goal

Add the governed release-control-plane evidence publication workflow required
after PR #1692 made production CD fail closed on missing real evidence.

## Coordinator Route

- Primary: `agent-coordinator`
- Implementation owner: `app-store-release-agent`
- Reviewers: `security-auditor`, `qa-engineer-agent`, `bug-hunter`
- Advisory: `architecture-specialist`, `dev-operator`, `ml-engineer-agent`,
  `data-scientist-agent`
- Custom skills: `pulseplate-pr-review`,
  `pulseplate-app-store-release`, `pulseplate-premortem-risk-review`

## Scope

In scope:

- `.github/workflows/release-control-plane-evidence.yml`
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md`
- release-control-plane ledger and epic notes
- focused workflow/docs tests

Out of scope:

- App Store Connect upload execution
- Fastlane upload mutation
- iOS, frontend, backend, OpenAPI, RAG, billing, semantic cache, GraphRAG, or
  product-facing runtime changes
- fake production evidence or fixture substitution

## Required Evidence Layout

```text
release-control-plane/
  release_manifest.json
  rag_gate_result.json
  build_equivalence_result.json
```

The workflow publishes governed evidence only. It does not create release truth.
The canonical validator remains `scripts/ci/check_release_control_plane.py`.

## Local Execution Policy

Use repo virtualenv only:

```bash
test -x .venv/bin/python
.venv/bin/python scripts/orchestration/check_preflight.py
.venv/bin/python scripts/orchestration/check_agent_consistency.py
```

Do not run full `make verify` for this coordinator-owned CI/workflow slice.
Use bounded gates and `make validate-changed`.

## Validation Plan

```bash
.venv/bin/python scripts/orchestration/check_preflight.py
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python -m pytest -q tests/test_release_control_plane_evidence_publication_workflow.py
.venv/bin/python -m pytest -q tests/test_release_control_plane_ci_gate.py tests/test_production_release_evidence_wiring.py tests/test_build_equivalence.py
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed
PATH=.venv/bin:$PATH pre-commit run --all-files
```

## Premortem Checks

- Fixture evidence cannot enter production publication.
- Placeholder values and malformed JSON block.
- Workflow cannot run from untrusted PR triggers.
- App Store/Fastlane secrets are not referenced.
- Source run and release manifest git SHA must match workflow `git_sha`.
- Docs do not imply production readiness or App Store readiness.
- Missing evidence files fail closed.
- Mapping artifacts are evidence after fixes, not substitutes for fixes.
