# METATRON lab — Rules of Engagement (RoE)

**Scope:** Internal operators only. This document does not authorize any activity against
systems without explicit written permission from the asset owner.

**Canonical architecture decision:** `docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md:1`

**Epic 1 coordinator packet (roster + order):** `docs/orchestration/METATRON_TRACK_A_EPIC1_TASK_PACKET_2026-04-06.md:1`

## Evidence anchors (repo policy)

- Product AI input guard (wellness surfaces, not pentest): `app/security/agent_input_guard.py:1`
- Artifact hygiene (never commit lab dumps): `AGENTS.md` (Local-only artifacts), `.gitignore` entry `artifacts/security_lab/`
- Orchestration procedure: `docs/orchestration/METATRON_SECURITY_ASSESSMENT_WAVE_RUNBOOK.md:1`
- Isolated network stub (no `app.main` coupling): `deploy/metatron-lab/docker-compose.yaml:1`

## Allowed targets

**Written authorization is mandatory for every engagement.** Inventory membership,
same-team ownership, or “lab” labels **do not** replace an explicit scope approval
(engagement letter / ticket) naming targets, CIDRs, and the time window.

- Hostnames and IP ranges may appear in an internal asset inventory **only after** they
  are **named in written authorization** for that assessment.
- **Staging / lab** hosts are in scope **only when** that environment is explicitly
  approved in the same authorization (not merely because it shares team ownership).

## Forbidden

- Scanning or exploiting **third-party** or **unknown** assets “by user input” from
  PulsePlate product surfaces (forbidden by ADR; no such API shall be added).
- Using production customer data or production PII as scan fodder.
- Storing raw scan outputs containing secrets in git; use `artifacts/security_lab/`
  (gitignored) or encrypted operator storage outside the repo.
- Routing lab traffic through the PulsePlate production API or shared DB credentials.

## Operator checklist (minimum)

1. Confirm written authorization for each target scope (name, CIDR, time window).
2. Run METATRON / offensive tools only from an **isolated** environment (see
   `deploy/metatron-lab/README.md:1`).
3. Keep local LLM and tool logs inside operator-controlled storage; redact before sharing.
4. Record high-level outcomes in your ticket system; do not paste full exploit chains into
   public issues.

## Escalation

Ambiguous scope → stop and obtain legal/security sign-off before running tools.
