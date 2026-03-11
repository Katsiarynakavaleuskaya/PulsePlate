# CV Experimentation Lane Audit

**Date:** 2026-03-11

**Scope:** PR1-PR5 experimentation-lane cohesion, CV packetization drift, and local orchestration weak points.

## Summary

PR5 closes the missing CV-specific layer for the governed experimentation lane, but the audit found several small drifts that needed direct fixes or backlog capture:

- generic experimentation docs existed without a canonical CV overlay
- `cv-contract-agent` alias drifted from canonical `cv-agent`
- CV packet tooling and tests were out of sync with backlog DoD
- CV examples referenced a missing prompt surface
- the experimentation epic still had a merged PR4 item left unchecked in the ledger

## Fixed in PR5

- Added canonical CV overlay docs:
  - `docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md:1`
  - `docs/orchestration/CV_EXPERIMENT_PACKET_TEMPLATE.md:1`
  - `docs/orchestration/contracts/CV_PHOTO_FOOD_EVAL_CONTRACT.md:1`
- Added the missing prompt/program surface referenced by CV packet tests:
  - `docs/prompts/cv/program.md:1`
- Aligned `experiment_bootstrap.py` and `experiment_contract.py` around one `cv_context` shape:
  - `scripts/orchestration/experiment_bootstrap.py:129`
  - `scripts/orchestration/experiment_contract.py:281`
- Replaced stale alias usage in the iOS/frontend playbook and linked CV work back to canonical agent docs:
  - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md:91`

## Deferred / Ledger-worthy follow-ups

- First-class `cv` routing domain is still deferred. Graph routing remains `ml` and `cv-agent` stays advisory in PR5.
- iOS/client execution ownership for future CV degrade UX is still deferred. PR5 documents the gap but does not invent a new canonical implementation agent.
- Historical `docs/pr/PR-5_*` naming can still confuse humans when talking about the experimentation epic “PR5”; this remains a documentation hygiene follow-up, not a blocker for this PR.

## Evidence anchors

- PR5 backlog item: `docs/roadmap/BACKLOG_LEDGER.md:5381`
- existing photo->food backlog contract anchor: `docs/roadmap/BACKLOG_LEDGER.md:1944`
- generic CV draft before PR5: `docs/orchestration/contracts/AI_OUTPUT_CONTRACTS.md:106`
- runtime privacy/degrade pointer: `docs/orchestration/contracts/RUNTIME_CONTEXT_MEMORY_CONTRACTS.md:81`
- playbook alias drift before PR5: `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md:91`

