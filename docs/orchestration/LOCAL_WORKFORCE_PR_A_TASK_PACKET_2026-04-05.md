# Local Workforce PR-A Task Packet

**Effective date:** 2026-04-05 (`America/New_York`)
**Creation date:** 2026-04-04 (`America/New_York`)
**Status:** Active planning packet for the next repo lane after merged prerequisite baseline PRs `#1325`, `#1327`, and `#1328`.
**Mode:** coordinator-first, additive-only, canonical-bootstrap extension

## Goal

Define the narrow implementation contract for local workforce `PR-A` so the next repo lane extends the existing coordinator bootstrap seam instead of creating a second packet, schema, or support-plane truth layer.

## Relationship to Existing SoT

- [`docs/orchestration/COMPOSER_BOOTSTRAP_KIT_PR1.md`](./COMPOSER_BOOTSTRAP_KIT_PR1.md) remains the RFC/decomposition source that split the original lane into `PR-A`, `PR-B`, and `PR-C`.
- [`docs/orchestration/PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md`](./PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md) remains reference architecture only.
- [`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-local-workforce-pr-a-bootstrap-seam`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-local-workforce-pr-a-bootstrap-seam) owns backlog truth for the follow-on lane.
- This packet owns only the branch-scoped execution contract for `PR-A`: scope, seams, invariants, deliverables, and validation.

## Decision Question

What additive changes, if any, are allowed on the canonical bootstrap surfaces so local workforce semantics can be expressed through the existing coordinator task-packet flow without introducing a sibling contract?

## In Scope

- Additive extensions to the existing coordinator task packet flow in `scripts/orchestration/task_bootstrap.py`
- Additive deterministic routing changes in `scripts/orchestration/skill_router.py` when justified by the canonical packet
- Additive sync-policy matcher updates in `scripts/orchestration/bootstrap_sync_policy.py` only when the same packet surface requires them
- Docs parity updates for task-packet and routing semantics
- Deterministic tests that prove the default bootstrap path remains stable while any approved workforce path stays additive

## Out of Scope

- Any standalone `action_packet`, `event_log`, or parallel bootstrap schema tree
- `.cursor/rules/*` or `.cursor/commands/*` changes
- Reflection-contract work delegated to `PR-B`
- Experimental local support-plane storage delegated to `PR-C`
- Launcher/runtime auto-start claims or host-runtime guarantees by docs alone
- Repo-wide review-governance rewrites outside existing canonical wrappers

## Critical Surfaces

- `scripts/orchestration/task_bootstrap.py`
  - Canonical task-packet builder and PR lifecycle bridge
- `scripts/orchestration/skill_router.py`
  - Deterministic skill classification and requested-agent fit logic
- `scripts/orchestration/bootstrap_sync_policy.py`
  - Canonical backlog/docs/agents/security sync-policy helpers
- `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
  - `TASK_PACKET_V1` field-level contract
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
  - Canonical routing-policy explanation for bootstrap output
- `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
  - Boundary between repo policy and launcher/runtime enforcement
- `tests/test_task_bootstrap.py`
- `tests/test_skill_router.py`
- `tests/test_bootstrap_sync_policy.py`

## Hard Constraints

1. `PR-A` must reuse the existing `TASK_PACKET_V1` protocol envelope contract defined in `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`; it must not introduce a sibling packet type or a second canonical schema tree.
2. The bootstrap packet `schema_version` field emitted by `scripts/orchestration/task_bootstrap.py` must remain stable unless a separate versioned migration packet explicitly authorizes a change.
3. Any local workforce semantics must be additive and optional; the default bootstrap path must remain valid without workforce-only caller requirements.
4. Docs parity is mandatory: if packet or routing semantics change, `AGENT_MESSAGE_PROTOCOL.md` and/or `AGENT_SKILL_ROUTING_POLICY.md` must be updated in the same PR.
5. Because the touched surfaces sit under `scripts/orchestration/**` and `docs/orchestration/**`, the lane remains privileged and must keep the security review path plus the mandatory post-open `qa-engineer-agent -> bug-hunter` lane.
6. No doc in this lane may claim launcher-enforced auto-start or host-runtime guarantees that belong outside repo SoT.

## Routing

- Primary: `agent-coordinator`
- Secondary: `backend-engineer`
- Reviewer: `security-auditor`
- Additional review lane: `qa-engineer-agent -> bug-hunter`
- Execution helper: `dev-operator`

## Recommended Skills

### Always

- `pulseplate-workflow`
- `docs-sync`
- `pulseplate-gates`

### Conditional

- `pulseplate-guards` for privileged-surface contract changes
- `create-pr` only after local readiness is established

## Planned PR-A Deliverables

- A narrowly scoped additive update to `scripts/orchestration/task_bootstrap.py` if workforce semantics require explicit packet metadata beyond the current baseline
- Matching additive updates to `scripts/orchestration/skill_router.py` and/or `scripts/orchestration/bootstrap_sync_policy.py` only when required by the same canonical packet change
- Parity updates in:
  - `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
  - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- Deterministic tests covering:
  - unchanged default bootstrap behavior
  - the newly approved local-workforce additive path

## Acceptance Criteria

- `PR-A` lands only on the current coordinator bootstrap seam
- No new files appear under `docs/orchestration/LOCAL_AGENT_*`, `docs/orchestration/schemas/*`, or analogous parallel packet directories as part of `PR-A`
- `build_task_packet(...)` remains deterministic for existing callers
- Any new local-workforce bootstrap semantics are optional, documented, and test-backed
- Skill-routing changes do not broaden unrelated task classes by accident
- Merge/readiness and current-head review governance remain inherited from the existing canonical wrapper path

## Validation Commands

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `pytest -q tests/test_task_bootstrap.py`
- `pytest -q tests/test_skill_router.py`
- `pytest -q tests/test_bootstrap_sync_policy.py`
- `pytest -q tests/test_repo_policy_guards.py`
- `make verify`

## Risks

- Workforce semantics could drift into a parallel schema instead of staying additive on the canonical packet
- Packet fields and docs parity can drift if protocol docs are not updated with code changes
- Deterministic skill routing can accidentally widen classification for non-workforce tasks
- Docs may over-claim launcher/runtime automation that still belongs to host-local tooling

## Deferred / Follow-Ups

- Reflection-protocol extensions move to `PR-B`
- Experimental local support-plane/storage moves to `PR-C`
- Launcher rollout remains outside repo PR chain per the automation readiness matrix
