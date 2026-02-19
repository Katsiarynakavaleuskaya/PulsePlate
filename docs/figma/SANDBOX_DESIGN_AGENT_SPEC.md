# Sandbox Design-Agent Specification (P1)

Date: 2026-02-19
Status: Spec only (implementation deferred to dedicated PoC PR)
Scope: Home + Plate + Progress (`H+P+Pr`)

## 1) Mission

Provide a deterministic assistant lane that transforms approved design tasks into:

- structured design/mapping outputs
- reproducible evidence artifacts
- implementation-ready constraints for FE/iOS teams

without direct runtime code changes.

## 2) In/Out Scope

In scope:

- Figma Make reconciliation support
- Design URL + node-id capture workflow
- Code Connect mapping proposal/verification workflow
- prompt governance pack generation for approved asset families

Out of scope:

- direct backend/frontend runtime mutations
- auto-merge or auto-release actions
- bypassing human approval gates

## 3) IO Contracts

## Input Contract

- `task_id`
- `session_id`
- `context_version`
- `surface`: `web` | `ios` | `both`
- `source_mode`: `make_only` | `design_available`
- `objective`: free text
- `constraints`: list
- `allowed_tools`: explicit allowlist

## Output Contract

- `result_status`: `done` | `partial` | `blocked`
- `decision_log`: ordered bullets
- `evidence`: command/output/exit records
- `mapping_updates`: optional list with (`cta_id`, `fileKey`, `nodeId`, `status`)
- `risk_flags`: optional list
- `next_actions`: ordered list

## 4) Tool Allowlist

Allowed:

- read/search/docs operations
- bounded browser lookup for design capture
- deterministic terminal commands for evidence capture

Forbidden:

- destructive git actions
- secret exfiltration or token logging
- direct runtime file mutation in this agent lane

## 5) Human-in-the-Loop Gates

Gate A (task start):

- Coordinator approves objective, scope, and constraints

Gate B (mapping activation):

- Design + FE confirm node-level match before `active` status

Gate C (handoff completion):

- Coordinator signs DoD and records backlog status

No gate bypass is allowed.

## 6) Risk and UQ Policy

## UQ Levels

- `low`: evidence complete, mapping verified
- `medium`: partial evidence, pending validation
- `high`: missing design URL/node id, ambiguous mapping, or drift conflicts

## Degrade Behavior

- If UQ is `high`, output must be `blocked` or `partial` with explicit blocker.
- Agent must not assert readiness/activation under high uncertainty.

## 7) Rollback / Kill-Switch

Rollback trigger conditions:

- repeated contradictory mapping outputs
- evidence contract violations
- unresolved safety violations

Kill-switch:

- set task state to `halted`
- require coordinator restart with revised constraints

## 8) Acceptance Criteria (DoD)

- Input/output contracts are documented and testable as checklist items
- All gates (A/B/C) are explicit and role-owned
- UQ policy and degrade behavior are explicit
- rollback and kill-switch conditions are explicit
- references to canonical SoT docs are complete

## 9) Implementation Hand-off (future PoC PR)

PoC must include:

- command/session/evidence schema validator
- one deterministic happy-path scenario
- one blocked-path scenario (`blocked_by_design_url`)
- no runtime perimeter expansion

## 10) Canonical References

- `docs/figma/FIGMA_CLAWBOT_OPERATING_MODEL.md`
- `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
