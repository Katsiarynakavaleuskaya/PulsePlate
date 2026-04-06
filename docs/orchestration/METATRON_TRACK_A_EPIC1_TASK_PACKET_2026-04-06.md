# METATRON Track A — Epic 1 Task Packet (Decision + threat model)

**Effective date:** 2026-04-06 (`America/New_York`)
**Status:** Open — coordinator-led governance lane; canonical contract for Epic 1 scope.
**Mode:** coordinator-first; **no** METATRON runtime in `app.main` or product OpenAPI.
**Ledger:** [`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-metatron-offensive-lab-out-of-band`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-metatron-offensive-lab-out-of-band)

## Goal (Epic 1)

Freeze architecture and policy: METATRON-class offensive tooling is **out-of-band** only;
publish ADR, Rules of Engagement, backlog truth, and cross-links so operators and agents
share one SoT before any optional Epic 2/3 hardening.

## Task analysis (coordinator)

| Field | Value |
|-------|--------|
| **Task** | Land governance artifacts for METATRON Track A Epic 1 (decision + threat model + ledger). |
| **Domain(s)** | Security, Architecture, Orchestration, Deploy (docs-only boundary). |
| **Complexity** | Moderate (policy + multi-doc consistency). |
| **Priority** | P1 |
| **Expected outcome** | Merged docs with `file:line` anchors, Phase 1 docs gates green, no `app/` or OpenAPI changes for offensive features. |
| **Invariants** | Thin product surface; no new user pentest routes; Dockerfile policy (no offensive in app image). |

**Risks:** Scope creep into product features; unauthorized scanning. **Mitigation:** RoE + ADR + explicit OUT below.

## In scope (Epic 1)

- ADR: `docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md:1`
- RoE: `docs/security/METATRON_LAB_RULES_OF_ENGAGEMENT.md:1`
- Ledger item + status: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-metatron-offensive-lab-out-of-band`
- Runbook pointer (cross-link only; full wave doc may ship same PR as Epic 1 closeout):
  `docs/orchestration/METATRON_SECURITY_ASSESSMENT_WAVE_RUNBOOK.md:1`
- RUNBOOK_AGENT pointer: `RUNBOOK_AGENT.md` (METATRON subsection)

## Out of scope (Epic 1)

- User-facing APIs, iOS/Web UI, or OpenAPI routes for scanning/exploits.
- Adding METATRON, nmap, nikto, or MariaDB lab history to `requirements.txt` / app image.
- Mandatory Tier-1 CI jobs that run offensive tools.
- Epic 2 (isolated runner packaging) and Epic 3 (runbook-only iteration) except **links**
  from Epic 1 docs.

## Agent execution order (full roster — plan canon)

Execute in order; coordinator holds DoD until each gate is satisfied or explicitly N/A.

1. **agent-coordinator** — Preflight (`scripts/orchestration/check_preflight.py`), task packet
   authorship, IN/OUT, PR scope discipline, synthesis for PR description.
2. **security-auditor** — RoE completeness, threat model vs product boundary, secret/exfil
   paths in operator guidance.
3. **bug-hunter** — Abuse cases: fake “internal” scans, logging leaks, misuse of compose stub
   for egress without approval.
4. **architecture-specialist** — ADR evidence anchors; confirm no `app.main` coupling;
   `deploy/metatron-lab/docker-compose.yaml:1` does not build PulsePlate app.
5. **qa-engineer-agent** — If PR touches only `docs/**`, `deploy/metatron-lab/**`,
   `.gitignore`, `RUNBOOK_AGENT.md`: confirm **no** `app/` or `tests/` changes required for
   Epic 1; if later PR adds code, OpenAPI/pentest-route absence tests apply.
6. **backend-engineer** — **N/A for Epic 1** unless an explicit follow-up ticket adds
   non-user ingest (defer to ledger).

**Epic-specialists (Epic 1 touchpoints):**

7. **dev-operator** — Run validation commands below; capture exit codes for PR evidence.
8. **data-scientist-agent** — Define “good” summary structure for future lab outputs (JSON
   fields / severity rubric) in runbook or RoE appendix; no product metrics.
9. **cursor-specialist-agent** — Only if Epic 1 PR edits `.cursor/**` (default: no).
10. **epistemology-discovery-agent** (optional) — RoE claims marked falsifiable vs opinion.
11. **tutor-mentor-agent** (optional) — Short operator read order: ADR → RoE → runbook →
    `deploy/metatron-lab/README.md:1`.

**Out of roster (do not invoke for this lane):** `nutritionist-agent`, `cv-agent`,
`cbt-psychologist-agent`, `app-store-release-agent`, `creative-designer`.

## Mandatory post-open lane

`qa-engineer-agent` → `bug-hunter` (same as other orchestration lanes per
`docs/orchestration/AGENTS.md:1`).

## Deliverables checklist (Epic 1 DoD)

- [ ] ADR merged with evidence section and ledger link.
- [ ] RoE merged under `docs/security/` with `file:line` anchors (Phase 1 gates).
- [ ] Ledger item updated with link to **this packet** and Target PR number when known.
- [ ] No offensive dependencies added to application runtime.
- [ ] `make validate-min` (or stricter `make verify` if orchestration scripts touched) green
      on the PR head.

## Validation commands (evidence)

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/ci/check_docs_phase1_gates.py --files \
  docs/security/METATRON_LAB_RULES_OF_ENGAGEMENT.md \
  docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md
docker compose -f deploy/metatron-lab/docker-compose.yaml --profile metatron-lab-isolation config -q
make validate-min
```

## PR body contract (mirror)

- **Deferred / Follow-ups:** link `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-metatron-offensive-lab-out-of-band`
- **Orchestration:** this packet path + coordinator-first roster above.
- **Explicit non-goals:** no product METATRON surface.

## References

- Plan (local): user-attached METATRON × PulsePlate evaluation (Track A only).
- Upstream tool: `https://github.com/Katsiarynakavaleuskaya/metatron`
