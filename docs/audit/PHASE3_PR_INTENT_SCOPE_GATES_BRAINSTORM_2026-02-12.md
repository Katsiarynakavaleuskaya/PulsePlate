<!-- markdownlint-disable MD013 -->

# Phase3 PR Intent/Scope Gates — Brainstorm Audit

**Date:** 2026-02-12
**Scope:** Next phase planning after PR #719 (Phase1 docs gates) and PR #720 (Phase2 PR body gates).
**Type:** Proposal / planning audit (not implementation evidence).

## Context

- Phase1 established docs metadata and evidence hygiene gates (`scripts/ci/check_docs_phase1_gates.py` + CI job).
- Phase2 established PR body metadata gates (`scripts/ci/check_pr_body_phase2_gates.py` + CI job).
- Current progression suggests a Phase3 that validates **PR intent vs actual diff scope** to reduce review drift and policy bypass.

## Evidence Pointers (repo state)

- `scripts/ci/check_docs_phase1_gates.py:1`
- `scripts/ci/check_pr_body_phase2_gates.py:1`
- `.github/workflows/ci.yml:113`
- `.github/workflows/ci.yml:181`
- `.github/pull_request_template.md:1`
- `AGENTS.md:1245`
- `docs/roadmap/BACKLOG_LEDGER.md:24`

## Agent Dialogue (Synthesis)

### agent-coordinator

- Keep sequence strict: docs-first planning artifact -> deterministic contract -> runtime implementation PR.
- Avoid mixed concerns (no feature shipping in planning PR).
- Ensure ledger traceability before calling work "ready".

### ai-app-architect

- Proposed phase name: **Phase3 PR Intent/Scope Gates**.
- Objective: enforce that PR-declared intent (type, deferred/follow-ups, risk claims) is consistent with changed files and guard policies.
- Contract-first design: parser rules in one module + deterministic tests + CI integration.

### architecture-specialist

- In scope for first implementation: repository policies and CI gating only.
- Out of scope: app runtime behavior, endpoint contracts, database migrations.
- Keep changes local to `scripts/ci/*`, `.github/workflows/ci.yml`, PR templates, tests, docs.

### security-auditor

- Main risks: policy bypass by misleading PR descriptions, hidden scope creep, stale deferred items.
- Deterministic checks should fail on missing/invalid links to ledger items when follow-ups are declared.
- No secret-bearing data or external network calls in parsers.

### logic-agent

- Invariant set should be explicit and testable:
  1. PR type declaration exists.
  2. PR type is compatible with changed paths.
  3. Deferred section exists.
  4. Deferred links must be valid format (ledger/issue/none marker).
  5. Runtime PR must not include planning-only docs under blocked patterns.
  6. Gate messages must be actionable and deterministic.

### algorithmic-art perspective

- Keep `algorithmic-art` as a separate, scoped stream (brand/marketing artifacts) and do not mix with guard-runtime changes in the same PR.
- Next `algorithmic-art` phase remains P2 backlog ("Algorithmic brand textures (seeded)").

## Recommended Next Phase

## Option A (recommended): Phase3 PR Intent/Scope Gates

**Objective:** Add deterministic CI checks that compare PR metadata intent to actual changed-file scope and deferred-tracking requirements.

### Proposed Deliverables

1. `scripts/ci/check_pr_intent_scope_phase3.py` with deterministic parser rules.
2. `tests/test_pr_intent_scope_phase3_gates.py` covering pass/fail and edge cases.
3. CI job in `.github/workflows/ci.yml` for pull request events (including `edited`).
4. Template alignment updates for PR type/deferred fields where needed.
5. Audit and AGENTS instruction updates (with exact run/fix command).

## Option B (secondary): Feedback-closure hardening

**Objective:** enforce stricter mapping between review comments and commits (extension of Phase2), only after Option A is stabilized.

## Definition of Done (planning/audit PR)

- A proposal audit exists with scope, invariants, risks, and anti-scope rules.
- Backlog ledger has a canonical item for Phase3 with owner/priority/DoD.
- No runtime code changed in planning PR.
- Proposed implementation plan is split into at least two PRs:
  - PR-Phase3-A: parser + tests + CI.
  - PR-Phase3-B: template/docs alignment and final hardening.

## Risks and Anti-Scope-Creep Guardrails

- **Risk:** mixing feature work with CI governance.
  - **Guardrail:** planning PR is docs-only; implementation PR scoped to CI/parser/tests/templates only.
- **Risk:** nondeterministic parser behavior.
  - **Guardrail:** strict regex + fixed fixtures + no network/time dependence.
- **Risk:** overblocking legitimate PRs.
  - **Guardrail:** start with narrow invariants, explicit error messages, add progressive tightening.
- **Risk:** backlog drift ("deferred but untracked").
  - **Guardrail:** mandatory ledger references in Deferred section and policy checks.

## Decision

Proceed with **Option A: Phase3 PR Intent/Scope Gates** as the immediate next phase, keeping `algorithmic-art` expansion in the separate P2 stream.

<!-- markdownlint-enable MD013 -->
