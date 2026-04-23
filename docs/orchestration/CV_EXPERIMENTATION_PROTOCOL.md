# CV Experimentation Protocol (Offline, packetized, privacy-first)

<!-- markdownlint-disable MD013 -->

**Purpose:** Define the canonical CV-specific overlay for governed experimentation packets.

**Status:** Canonical overlay for the governed CV experimentation lane. This file extends, and does not replace,
`docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`.

**Hard rule:** This protocol is offline-evaluation-only. It does not authorize runtime
photo ingestion, image retention, model serving, OpenAPI changes, or client-visible
feature activation.

---

## Canonical references

- Base experimentation SoT: `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
- CV output contract: `docs/orchestration/contracts/CV_PHOTO_FOOD_EVAL_CONTRACT.md`
- CV packet template: `docs/orchestration/CV_EXPERIMENT_PACKET_TEMPLATE.md`
- Cross-client thin-client playbook: `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`
- Agent guidance: `.cursor/agents/cv-agent.md`, `.cursor/agents/bayesian-uq-agent.md`, `.cursor/agents/data-scientist-agent.md`
- Privacy boundary pointer: `docs/orchestration/contracts/RUNTIME_CONTEXT_MEMORY_CONTRACTS.md`

---

## 1. Scope

### In scope

- Offline `photo -> food` evaluation packets.
- Dataset selection, provenance, licensing, and split documentation.
- Confidence/uncertainty buckets for deterministic review and future UX mapping.
- Degrade-state definitions for future runtime/client PRs.
- Privacy packet requirements for image-derived content.

### Out of scope

- Runtime photo upload endpoints.
- Storage or retention of raw user images.
- Client-side CV UX implementation in `frontend/` or `ios/`.
- Model-hosting decisions, inference budgets, or serving providers.

---

## 2. CV packet contract

CV-oriented experiment packets must include a `cv_context` object in addition to the
generic packet fields from `AGENT_EXPERIMENTATION_PROTOCOL.md`.

Required `cv_context` fields:

- `dataset`
  - `id`
  - `version`
  - `source`
  - `license`
  - `split_strategy`
  - `label_provenance`
- `sensor_conditions`
- `uncertainty_band_policy`
- `degrade_state_matrix`
- `privacy_packet`

Rule:

- If an experiment question or mutable surface is CV-oriented, missing `cv_context`
  is a fail-closed validation error.
- Non-CV packets remain backward compatible and must not be forced to include
  CV metadata.

---

## 3. Uncertainty and degrade rules

### Qualitative confidence only for this lane

CV confidence remains qualitative in this phase:

- `high`
- `medium`
- `low`
- `unknown`

This lane does not canonize numeric thresholds, calibration cutoffs, or production scoring
policy. Those remain future evaluation hooks only.

### Canonical degrade states

Every CV packet must carry the full deterministic degrade-state set:

- `show_ranked_candidates`
- `confirm_top_candidate`
- `manual_entry_required`
- `reject_unusable_image`
- `privacy_blocked`

Interpretation:

- This protocol defines the states and their semantics only.
- Future frontend/iOS/runtime PRs may map these states to concrete UI and API flows.
- Runtime ownership for client-visible CV UX remains deferred and must be tracked in
  `docs/roadmap/BACKLOG_LEDGER.md`.

---

## 4. Dataset and oracle expectations

Every CV packet must document:

- dataset provenance and license
- split strategy
- label provenance
- sensor conditions / known capture limitations
- immutable oracle commands
- negative controls

Canonical negative controls for the lane:

- non-food image
- empty or invalid image
- ambiguous multi-item image
- low-light / blur / occlusion
- out-of-distribution image

Rule:

- Nutrition values remain deterministic lookup outputs only.
- No packet may imply “LLM-guessed calories” or medical-grade recognition accuracy.

---

## 5. Privacy packet rules

Every CV packet must include a privacy packet with, at minimum:

- raw-image retention default
- logging policy
- consent policy
- deletion policy

Default posture for this lane:

- raw user images are sensitive by default
- raw-image retention defaults to none
- no raw-image logging
- offline evaluation should use approved public datasets or local untracked fixtures

---

## 6. Routing and ownership

For PR13 and later:

- generic coordinator routing resolves CV-first work through `domain=cv`,
  `cluster=ml`
- governed experimentation packets remain `ml`-scoped for backward compatibility
- `cv-agent` is graph-primary for routed CV tasks
- `data-scientist-agent` and `bayesian-uq-agent` remain expected secondary/advisory tracks

When defining future degrade UX states, required context expands to:

- `frontend/AGENTS.md`
- `ios/AGENTS.md`
- `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`

This is a documentation requirement only. It does not assign runtime implementation
ownership in PR13.
