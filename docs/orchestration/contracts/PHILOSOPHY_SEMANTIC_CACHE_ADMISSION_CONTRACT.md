# Philosophy Semantic-Cache Admission Contract

## Purpose

Philosophy Epic V2 PR-1 defines an offline, deterministic admission policy for
which philosophical request classes may ever enter a **future** semantic-cache
path after the global semantic-cache gate opens. It does not open the
semantic-cache gate. It does not enable runtime caching. It does not duplicate
the SC-G5 backend selection matrix.

This contract does not open the semantic-cache gate.

Gate remains closed.

- Gate status: closed.
- Runtime allowed: false.
- Implementation allowed: false.
- Admission mode: policy-only metadata.
- Default admission while gate closed: `runtime_only`.
- Hard-blocked surfaces remain `blocked_from_cache`.

## Wellness-Only Scope

This admission policy governs wellness product metadata only. It does not
authorize clinical, diagnostic, or therapeutic claims. Philosophical outputs
remain non-authoritative relative to medical fact; cache admission must not
change that epistemic status.

## Upstream Contracts (Reference Only)

PR-1 references merged upstream truth and must not restate SC-G5 ranking
rules, candidate labels, or backend evaluation matrices:

- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md` — gate-closed markers.
- `docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md`
  — SC-G5 label-only backend selection (merged via PR #1742,
  `cb1db8b40`).
- `core/insight/philosophical_runtime.py` — bounded philosophical runtime seam.
- `core/verification/` — verify-before-write bundle requirements for
  promotion paths.

## Admission Classes

Every philosophical request class MUST resolve to exactly one admission class:

| Class | Meaning while gate closed |
| --- | --- |
| `runtime_only` | May use philosophical runtime helpers only; no cache read/write/admission. |
| `blocked_from_cache` | Never eligible for semantic cache (hard block). |
| `verification_bundle_required` | Must pass a canonical verification bundle before any future cache consideration. |
| `future_cache_candidate_deferred` | May be reviewed only after gate-open PR + SC-G5 + admission re-check; not active now. |

Falsifiability (repo): this contract is violated if implemented code paths (a)
admit `blocked_from_cache` surfaces to a semantic cache, (b) treat
`verification_bundle_required` paths as cache-eligible without a passed bundle,
or (c) ship cache adapters for philosophy before the global semantic-cache gate
opens. Assertions in prose alone do not satisfy these conditions.

## Blocked Surfaces (Hard Block)

The following surfaces are `blocked_from_cache` regardless of gate state until
a dedicated reviewed contract explicitly changes them:

- billing, subscription, entitlement, or paywall truth;
- auth/session/account identity truth;
- medical diagnosis, treatment, medication, or therapy routing;
- compliance/legal output caches;
- raw user free-text persistence for cache keys;
- advisory wiki, workforce memory, GraphRAG, or plugin/control-plane outputs as
  product truth;
- FitChef/CBT coaching paths that bypass wellness-only validators.

Evidence: `AGENTS.md:318` AI input screening requirement and `AGENTS.md:347`
knowledge promotion invariant; `app/security/agent_input_guard.py:191`
fail-closed AI input scanning.

## Verification Bundle Required

Surfaces that may produce promotable or cache-adjacent philosophical artifacts
MUST remain `verification_bundle_required` until a passed canonical verification
bundle exists:

- knowledge promotion or semantic-cache admission decisions;
- recursive retrieval verification merges;
- philosophical outputs that could be mistaken for canonical facts;
- any path that would write or mutate knowledge records.

Slugs in the machine-readable state denote risk classes, not endorsed facts.

Evidence: `core/verification/registry.py:24` canonical bundle construction and
`docs/orchestration/WAVE6_A6_PHILOSOPHICAL_ROLLOUT_W1_PACKET_2026-04-22.md`.

## Runtime-Only Default

While the semantic-cache gate remains closed, philosophical insight flows
default to `runtime_only`:

- preview/validate/rewrite metadata from `core/insight/philosophical_runtime.py`;
- offline logic+philosophy replay lanes;
- eval harness fixtures without cache serving.

No Redis imports. No GPTCache imports. No embeddings. No vector search. No
connection strings. No cache adapters. No `/insight` cache wiring is permitted
in PR-1.

## Required Rollout Order Remains

Required rollout order remains:

1. SC-G1 rollout gate contract.
2. SC-G2 exact/fuzzy cache scaffold.
3. SC-G3 observability and false-hit harness.
4. SC-G4 bounded `/insight` semantic-cache experiment.
5. SC-G5 backend selection.
6. Philosophy admission contract reconciliation (this document).

Philosophy admission does not replace SC-G2–SC-G5 contracts and does not
authorize backend selection or serving.

## Forbidden Claims

PR-1 and downstream docs must not claim:

- any live/open/approved serving status for philosophical semantic-cache paths;
- any equivalence between Philosophy PR-1 admission work and opening the global gate;
- any approved Redis/GPTCache rollout for philosophical cache paths;
- any production-live philosophical cache-key behavior;
- any skipped verification-bundle requirement for cache admission;
- any approved/enabled runtime expansion for Philosophy admission or PR-1;
- PDF/design intake overrides repo gate markers.

If PR #1742 is ever superseded or its canonical merge SHA changes, update this
contract, its JSON schema, `scripts/ci/check_semantic_cache_gate.py`, and
`tests/test_philosophy_semantic_cache_admission_contract.py` in the same PR.

## Premortem Closure

- Gate open by prose: closed markers and this contract repeat runtime false.
- SC-G5 duplication: backend selection matrix stays in SC-G5 contract only.
- Cache without verification: `verification_bundle_required` blocks promotion
  paths without bundles.
- Medical/wellness boundary drift: blocked surfaces include therapy/medical
  routing and non-wellness claims.
- Runtime expansion in PR-1: no providers, embeddings, storage, or serving.

## Machine-Readable State

```json
{
  "admission_classes": [
    "runtime_only",
    "blocked_from_cache",
    "verification_bundle_required",
    "future_cache_candidate_deferred"
  ],
  "blocked_surfaces": [
    "billing_auth_entitlement_truth",
    "auth_session_account_identity_truth",
    "medical_or_therapy_routing",
    "compliance_legal_output_cache",
    "raw_user_free_text_cache_keys",
    "advisory_wiki_product_truth",
    "workforce_memory_product_truth",
    "graphrag_product_truth",
    "plugin_control_plane_product_truth",
    "fitchef_cbt_bypassing_validators"
  ],
  "default_admission_while_gate_closed": "runtime_only",
  "does_not_duplicate_sc_g5_backend_selection": true,
  "forbidden_claims": [
    "claim_class_gate_open_equivalence",
    "claim_class_live_philosophy_cache",
    "claim_class_provider_rollout_approved",
    "claim_class_verification_bundle_skipped",
    "claim_class_production_live_cache_key_behavior",
    "claim_class_pdf_design_intake_gate_override",
    "claim_class_runtime_expansion_approved"
  ],
  "gate_status": "closed",
  "implementation_allowed": false,
  "references": [
    "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
    "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md",
    "core/insight/philosophical_runtime.py",
    "core/verification/"
  ],
  "rollout_phase": "PHILOSOPHY-PR1",
  "runtime_allowed": false,
  "sc_g5_merge_commit": "cb1db8b40",
  "runtime_only_surfaces": [
    "philosophical_runtime_preview_validate_rewrite",
    "offline_logic_philosophy_replay",
    "eval_harness_without_cache_serving"
  ],
  "verification_bundle_required_surfaces": [
    "knowledge_promotion_decisions",
    "semantic_cache_admission_decisions",
    "recursive_retrieval_verification_merges",
    "philosophical_outputs_presentation_risk_canonical_facts",
    "write_or_mutate_knowledge_records"
  ],
  "future_cache_candidate_deferred_surfaces": []
}
```

The deferred list is intentionally empty until a future reviewed gate-open PR
and admission re-check identify a specific philosophical cache candidate.
