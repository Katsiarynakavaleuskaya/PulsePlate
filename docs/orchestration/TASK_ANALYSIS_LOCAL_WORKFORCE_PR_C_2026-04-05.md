# Task Analysis — Local Workforce PR-C (Support Plane)

**Lane SoT:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-local-workforce-pr-c-support-plane`
**RFC decomposition:** `docs/orchestration/COMPOSER_BOOTSTRAP_KIT_PR1.md` (PR-A/B closed on `main`; next repo slice = PR-C).

---

## Task Analysis

**Task:** Land experimental **non-canonical** local support-plane storage that reuses Agent Control Plane policy, execution-mode, and signed audit primitives; no launcher/host-runtime claims from repo markdown alone (`docs/orchestration/AUTOMATION_READINESS_MATRIX.md`).

**Domain(s):** Security, Architecture, Multiple (orchestration scripts)

**Complexity:** Moderate

**Priority:** P2

- **Priority track (P0-A / P0-B / P1):** P1 (governed experimentation / support infrastructure)

**Expected Outcome:** Deterministic module + tests under `scripts/orchestration/local_support_plane.py` and `tests/test_local_support_plane.py`; documentation cross-links in `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`; default storage under gitignored `artifacts/orchestration/local_support_plane/` (override via `LOCAL_SUPPORT_PLANE_ROOT`).

**Invariants Affected:**

- [ ] One BMI Engine
- [ ] Thin HTTP Adapter Policy
- [x] Layer Separation — support plane is not orchestration SoT
- [x] Contract-First — no new public API surface
- [x] Other: Automation readiness matrix — no repo-only launcher guarantees

**Risks:**

1. **Path escape / abuse** — Mitigation: strict key regex, single-level files under resolved root only.
2. **Audit log growth** — Mitigation: bounded value size; operators rotate/clean `artifacts/` per runbooks.

**Proposed Approach:**

1. Add `local_support_plane.py` with `put_record` / `get_record` / `delete_record` gated by `evaluate_policy` / `require_policy_allow` and `require_execution_mode(allow_review_required=True)`.
2. Optional signed audit line via `sign_audit_envelope` + `persist_audit_envelope` on mutating ops.
3. Deterministic pytest with `tmp_path` overrides (no committed artifacts).

**Agent Assignment:**

- **Primary:** backend-engineer / security-aware implementer — script + control-plane integration
- **Post-open (mandatory per workflow):** qa-engineer-agent, bug-hunter
- **Privileged paths:** `scripts/orchestration/**` → security-auditor advisory pass
- **Secondary:** N/A unless RAG/metrics scope appears (not in this slice)

**Constraints:**

- Non-canonical semantics must remain explicit in module docstring and security baseline.
- Reuse `app/security/agent_control_plane.py` — no parallel policy engine.
- Do not assert launcher auto-start or host-runtime enforcement from this PR.

---

**Analysis by:** agent-coordinator (session)
**Date:** 2026-04-05
