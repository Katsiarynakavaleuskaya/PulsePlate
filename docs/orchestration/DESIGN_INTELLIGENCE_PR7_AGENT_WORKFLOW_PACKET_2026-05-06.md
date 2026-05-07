<!-- markdownlint-disable MD013 -->
# Design Intelligence PR-7 Agent Workflow Packet

## Goal

Add the Design Intelligence PR-7 design-agent workflow and PR template after the web PR-5 and iOS PR-6 decision packets.

## Coordinator Route

Run before editing:

```bash
.venv/bin/python scripts/orchestration/check_preflight.py
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python scripts/orchestration/task_bootstrap.py \
  --goal "Design Intelligence PR-7: add design-agent workflow and PR template after web and iOS parity decisions" \
  --task-class "Design" \
  --pr-phase pre_open \
  --path docs/orchestration/DESIGN_AGENT_WORKFLOW.md \
  --path docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md \
  --path docs/orchestration/DESIGN_INTELLIGENCE_PR7_AGENT_WORKFLOW_PACKET_2026-05-06.md \
  --path .github/PULL_REQUEST_TEMPLATE/design.md \
  --path AGENTS.md \
  --path docs/roadmap/BACKLOG_LEDGER.md \
  --path Makefile \
  --path tests/test_design_agent_workflow_docs.py \
  --requested-agent agent-coordinator \
  --requested-agent creative-designer \
  --requested-agent frontend-engineer \
  --requested-agent architecture-specialist \
  --requested-agent security-auditor \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter \
  --requested-agent data-scientist-agent
```

Role order is coordinator-first:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. `architecture-specialist`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`
8. `data-scientist-agent`

## Source Precedence

Canonical:

- Repo code, docs, tests, and `AGENTS.md`.
- `/tokens` as token authoring truth.
- Generated mirrors as derived runtime artifacts.
- UI vocabulary.
- Backend/OpenAPI contracts.
- Runtime web and iOS components.

Reference/process only:

- `docs/design/DESIGN.md`.
- Reference manifests.
- Screen evidence packs.
- Design scorecards.
- Web acceptance briefs and iOS parity audits.
- Figma, Canva, Storybook, external references, prompt outputs, generated briefs, and PR templates.

## In Scope

- Add `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`.
- Add `docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md`.
- Add `.github/PULL_REQUEST_TEMPLATE/design.md`.
- Add this PR-7 packet.
- Add a narrow `AGENTS.md` pointer.
- Add a small docs guard test.
- Add a tiny Makefile interpreter guard so design targets honor `DEV_PYTHON`.
- Update the Design Intelligence ledger status.

## Out Of Scope

- No web redesign.
- No iOS redesign.
- No runtime code changes.
- No backend/OpenAPI changes.
- No `/tokens` changes.
- No manual generated mirror edits; generated mirror diffs are allowed only when produced by canonical tooling and explicitly scoped to reflect `/tokens` changes.
- No Figma or Canva writes.
- No screenshots, videos, traces, or binary artifacts.
- No PR-8 GEPA implementation.

## Validation

Use repo `.venv` only:

```bash
.venv/bin/python scripts/orchestration/check_preflight.py
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python scripts/design/generate_design_md.py --check
.venv/bin/python scripts/design/reference_manifest.py validate-dir docs/design/reference_manifest/examples
.venv/bin/python scripts/design/screen_evidence_pack.py validate-dir docs/design/screen_evidence/examples
.venv/bin/python scripts/design/design_scorecard.py validate-score docs/design/design_scorecard/examples/web_marketing.scorecard.sample.json
.venv/bin/python scripts/design/design_scorecard.py validate-score docs/design/design_scorecard/examples/ios_home.scorecard.sample.json
.venv/bin/python -m pytest -q tests/test_design_agent_workflow_docs.py
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make design-guard
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make tokens-check
PATH=.venv/bin:$PATH pre-commit run --all-files
```

This packet uses the operator-approved machine-heavy design-lane exception: bounded local checks replace full local `make verify` only when the PR body and fixed mapping artifact document the deferral and current-head CI/strict merge readiness remain authoritative.

## Risks

- Workflow accidentally creates another source of truth.
- Template implies Figma, Canva, Storybook, evidence packs, or scorecards can override repo truth.
- Premortem becomes a mapping-only ritual instead of an actual diff review.
- Template encourages full local `make verify` or green-main claims against operator instructions.
- PR mutates runtime files, generated mirrors, or token outputs.

## Required Reviews

- Premortem must inspect the actual docs/test diff and real defects must be fixed before mapping.
- Bug-hunter must inspect the actual diff for source-of-truth drift, runtime drift, generated mirror edits, hidden artifacts, and missing required sections.
- Review comments must be mapped in `docs/review/PR_<N>_FIXED_MAPPING.md` after the PR number exists.

## Definition Of Done

- Design-agent workflow exists.
- Design PR template exists in docs and GitHub template form.
- `.venv/bin/python` policy is documented.
- Premortem-as-real-fix rule is documented.
- Review mapping rules are documented.
- Docs guard test passes.
- No runtime or generated mirror diff exists.
- Bounded checks pass.
