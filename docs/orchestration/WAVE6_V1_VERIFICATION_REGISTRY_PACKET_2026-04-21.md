# Wave 6 V1 Verification Registry Packet

**Date:** 21 April 2026
**Scope:** bounded post-K1 runtime follow-up for verification registry and write admission
**Mode:** implementation packet

## Purpose

Freeze one narrow follow-up slice after `PR-K1` that adds a first-class
verification registry/bundle and enables verify-before-write admission for the
existing knowledge seam.

This packet exists to:

- add a bounded `core/verification/*` subdomain;
- reuse existing recursive verification diagnostics and philosophical runtime
  verification/falsification signals;
- require a passed verification bundle before knowledge writes;
- keep semantic cache, persistence, and public-contract changes out of scope.

## Current-head truth

- `PR-K1` already landed the bounded knowledge seam on `main` via PR `#1483`.
- `core/ai/insight_runtime.py` already owns the canonical non-HTTP runtime
  preparation seam and threads `knowledge_policy`.
- `core/rag/recursive_retrieval.py` already exposes bounded verification passes
  and `verification_calls`.
- `core/insight/philosophical_runtime.py` already runs
  `VerificationEnforcer`, `FalsificationChecker`, contradiction counting,
  rewrite/fallback logic, and internal candidate handoff.
- `app/services/insight_application_service.py` is already a thin handoff seam
  and must stay that way.

## Hard boundaries

- No `legacy_app.py` edits
- No `app/routers/*` edits
- No OpenAPI or public response contract changes
- No DB migrations or persistent verification storage
- No Redis / GPTCache / semantic-cache implementation
- No GraphRAG or ContextManifest work
- No widening into advisory/wiki/plugin control-plane rails

## Canonical implementation surfaces

### New internal subdomain

- `core/verification/__init__.py`
- `core/verification/contracts.py`
- `core/verification/policy.py`
- `core/verification/registry.py`

### Existing seams allowed to change

- `core/knowledge/promotion.py`
- `core/rag/orchestration.py`
- `core/insight/philosophical_runtime.py`
- `app/services/insight_application_service.py`
- `AGENTS.md`

## Required invariants

- Knowledge writes require a passed canonical verification bundle.
- Existing verification signals are reused, not duplicated in a parallel stack.
- `verify-before-write/cache/action` is the long-term contract, but this packet
  enables only `write`.
- Route and app layers must not author verification truth.
- Failed verification must degrade safely and must not break the response path.
- Semantic cache remains deferred under
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`.

## Required role-agent order for this lane

1. `agent-coordinator`
2. `architecture-specialist`
3. `data-scientist-agent`
4. `backend-engineer`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`

Rules:

- every assigned role agent must be used in this order;
- no assigned role agent may be skipped without an explicit packet update;
- the canonical post-open `qa-engineer-agent -> bug-hunter` pass remains
  mandatory.

## Deliverables

- bounded `core/verification/*` registry/contracts/policy seam
- `VerificationArtifact` / `VerificationBundle` materialization from existing
  recursive and philosophical verification signals
- write admission enforced through the canonical verification bundle
- deterministic tests for allowed/denied admission without payload drift
- root invariant wording updated without opening the semantic-cache gate

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- targeted pytest for verification/runtime/knowledge paths
- `pre-commit run --all-files`
- `make verify`
