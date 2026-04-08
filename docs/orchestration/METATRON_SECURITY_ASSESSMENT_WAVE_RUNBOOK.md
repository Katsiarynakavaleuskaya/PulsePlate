# METATRON security assessment wave (coordinator-led)

**Purpose:** Repeatable, **internal-only** workflow for authorized offensive-lab work using
METATRON-class tooling that stays **out of band** from PulsePlate product code.

**Hard gates:**

- Epic 1 task packet (scope + agent order): `docs/orchestration/METATRON_TRACK_A_EPIC1_TASK_PACKET_2026-04-06.md:1`
- RoE: `docs/security/METATRON_LAB_RULES_OF_ENGAGEMENT.md:1`
- Architecture boundary: `docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md:1`
- Deploy stub: `deploy/metatron-lab/README.md:1`

## Agent roster (subagent types)

Lead: `agent-coordinator` — task analysis, scope, handoffs, synthesis.

Core review: `security-auditor`, `bug-hunter`, `architecture-specialist`, `qa-engineer-agent`;
`backend-engineer` only if a non-user-facing ingest path is explicitly in scope.

Epic-specific: `dev-operator`, `data-scientist-agent`, `ml-engineer-agent`,
`cursor-specialist-agent`, optional `epistemology-discovery-agent`, `tutor-mentor-agent`.

## Wave phases

1. **Preflight** — Run `python3 scripts/orchestration/check_preflight.py` from repo root; confirm
   written target authorization per RoE.
2. **Plan** — Coordinator records IN/OUT: no edits under `app/` for offensive features; no
   OpenAPI changes for pentest endpoints.
3. **Execute (off-box)** — Operator runs upstream METATRON (or equivalent) on an isolated
   host/network; see `deploy/metatron-lab/README.md:1`. PulsePlate production containers are
   not used as scan launchers.
4. **Capture** — Store raw tool output under `artifacts/security_lab/<run-id>/` (gitignored).
   Never commit secrets or full third-party dumps.
5. **Synthesize** — Coordinator produces a short summary (Markdown or JSON) with: targets,
   date, tools, high-severity themes, remediation pointers. Link evidence commands in the
   summary (verified-audit style when labeled “Verified”).
6. **QA gate** — If any PR touches `app/` or OpenAPI, `qa-engineer-agent` proves absence of
   pentest routes (`tests/test_openapi_determinism.py:1` remains the determinism SoT).

## Artifact contract

- **Path:** `artifacts/security_lab/` only (see `.gitignore`).
- **Retention:** Operator responsibility; repo policy treats these as local-only.

## Deferred / follow-ups

Track product-facing “user pentest” features under a **separate** PRD; they are **out of
scope** for this wave per ADR.
