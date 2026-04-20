# WAVE6 K1 Synthesis

## Synthesis

**Task:** Implement `PR-K1` as a bounded post-A5 runtime slice for knowledge contracts and promotion from validated RAG evidence.

**Final Decision:**
K1 proceeds as a bounded internal runtime seam: `core/knowledge/*`, `core/ai/insight_runtime.py`, `core/rag/orchestration.py`, `core/insight/philosophical_runtime.py`, `app/services/insight_runtime.py`, and `app/services/insight_application_service.py`.

**Rationale:**
This preserves the plan’s core intent: policy is decided in `prepare_insight_runtime(...)`, candidates are built only from validated RAG evidence before prompt formatting becomes the output path, and the service layer remains thin. The only additional seam is the existing traced adapter, which is required to pass the policy through the current app-layer telemetry handoff without reopening routes or `legacy_app.py`.

**Alternatives Considered:**
1. Remove `app/services/insight_runtime.py` changes entirely.
   Reason not chosen: `knowledge_policy` would then bypass the existing traced handoff and force worse drift elsewhere.
2. Store raw chunk content as canonical fact values.
   Reason not chosen: violates the invariant that retrieval artifacts are evidence, not canonical facts.

**Follow-ups:**
- [ ] semantic cache remains deferred to its own gated lane → `BACKLOG_LEDGER.md`
- [ ] persistent knowledge storage remains deferred to a dedicated storage/migration lane → `BACKLOG_LEDGER.md`

**Postponed Items:**
- Semantic-cache admission/hit logic - Reason: explicitly out of K1 scope → recorded as deferred in roadmap packeting.
- DB-backed knowledge store - Reason: storage/migration lane is intentionally closed for K1 → keep deferred.

---

**Synthesis by:** agent-coordinator
**Date:** 2026-04-19
