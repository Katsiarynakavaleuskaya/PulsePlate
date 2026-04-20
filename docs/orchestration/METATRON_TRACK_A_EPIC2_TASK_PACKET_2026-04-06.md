# METATRON Track A — Epic 2 Task Packet (isolated runner)

**Effective date:** 2026-04-06 (`America/New_York`)
**Status:** Open — coordinator-led infra/scripts lane; canonical contract for Epic 2 scope.
**Mode:** coordinator-first; **no** METATRON runtime in `app.main` or product OpenAPI.
**Ledger:** [`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-metatron-offensive-lab-out-of-band`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-metatron-offensive-lab-out-of-band)

## Goal (Epic 2)

Ship an **isolated runner** boundary: operators can validate and extend the METATRON
out-of-band lab using **only** `deploy/metatron-lab/**` and narrow `scripts/metatron_lab/**`,
without building the PulsePlate app image, without new product routes, and without OpenAPI
or `frontend/src/api/*` changes.

## Task analysis (coordinator)

| Field | Value |
|-------|--------|
| **Task** | Epic 2 — compose profiles + deterministic validate/checklist CLI + tests. |
| **Domain(s)** | Security, Deploy, Orchestration (scripts), QA. |
| **Complexity** | Low–moderate (compose + subprocess guard + tests). |
| **Priority** | P1 |
| **Expected outcome** | Merged PR with `make validate-min` green; `docker compose … config -q` for both profiles; no `app/` diff. |
| **Invariants** | ADR + RoE; Dockerfile policy; artifacts only under `artifacts/security_lab/` (gitignored). |

**Risks:** Scope creep into product; CI running offensive tools. **Mitigation:** IN/OUT below + profile-gated compose + no Tier-1 offensive jobs.

## In scope (Epic 2)

- Compose: `deploy/metatron-lab/docker-compose.yaml:1` — `metatron-lab-runner` profile and
  documented sidecar stub (Alpine placeholder, resource limits, `lab_internal` only).
- Scripts: `scripts/metatron_lab/compose_guard.py:1`, `scripts/metatron_lab/__main__.py:1` —
  `validate` (absolute-path `docker` via `shutil.which`) and `checklist` (operator reminders).
- Tests: `tests/test_metatron_lab_compose_guard.py:1` — deterministic subprocess mocks.
- Docs: this packet; `deploy/metatron-lab/README.md:1` cross-links; ledger Target PR line update.

## Out of scope (Epic 2)

- `app/`, `core/` business logic, product routers, OpenAPI, `frontend/src/api/*`.
- Adding METATRON/offensive dependencies to `requirements.txt` or the application image.
- Mandatory Tier-1 CI that runs lab scans or starts long-lived lab containers.

## Agent execution order (full roster — plan canon)

Execute in order; coordinator holds DoD until each gate is satisfied or explicitly N/A.

1. **agent-coordinator** — Preflight (`scripts/orchestration/check_preflight.py:1`), IN/OUT,
   PR scope discipline, synthesis for PR description.
2. **security-auditor** — Network isolation (`internal: true`), volumes/paths, secrets, RoE
   alignment (`docs/security/METATRON_LAB_RULES_OF_ENGAGEMENT.md:1`).
3. **bug-hunter** — Abuse: running without profile, path leaks in logs, bypassing RoE via
   “convenience” flags.
4. **architecture-specialist** — ADR evidence (`docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md:1`);
   runner not registered in `app.main`; no `COPY` of PulsePlate app in lab compose.
5. **qa-engineer-agent** — Tests for scripts; subprocess + absolute binary policy; no dead-code-only tests.
6. **backend-engineer** — **N/A** unless a future ticket adds a thin HTTP-free CLI contract.

**Epic 2 touchpoints:**

7. **dev-operator** — Raw exit codes for `docker compose … config -q`, `python3 -m scripts.metatron_lab validate`,
   `make validate-min`.
8. **ml-engineer-agent** (optional) — If a sidecar LLM is documented later: CPU/RAM limits, non-product paths only.
9. **tutor-mentor-agent** (optional) — Read order: this packet → `deploy/metatron-lab/README.md:1` → RoE.

**Out of roster (do not invoke for this lane):** `nutritionist-agent`, `cv-agent`,
`cbt-psychologist-agent`, `app-store-release-agent`, `creative-designer`.

## Coordinator synthesis (Epic 2)

| Gate | Owner | Evidence |
|------|--------|----------|
| Scope | coordinator | Diff ⊆ `{deploy/metatron-lab/**, scripts/metatron_lab/**, tests/test_metatron_lab_*, docs/orchestration/METATRON_TRACK_A_EPIC2_*, docs/roadmap/BACKLOG_LEDGER.md, deploy/metatron-lab/README.md}` |
| Isolation | security-auditor | `lab_internal.internal: true`; profiles prevent default `compose up` |
| Abuse paths | bug-hunter | Checklist + tests for missing `docker` → exit 2 |
| Architecture | architecture-specialist | No app image build in lab compose file |

## Mandatory post-open lane

`qa-engineer-agent` → `bug-hunter` (per `docs/orchestration/AGENTS.md:1`).

## Deliverables checklist (Epic 2 DoD)

- [ ] This packet merged and linked from ledger + lab README.
- [ ] `metatron-lab-runner` profile validates with `docker compose … config -q`.
- [ ] `python3 -m scripts.metatron_lab validate` exits 0 when Docker is available and compose is valid.
- [ ] No `app/` or OpenAPI artifact changes.
- [ ] `make validate-min` green on PR head (or full `make verify` if repo policy requires).

## Validation commands (evidence)

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
docker compose -f deploy/metatron-lab/docker-compose.yaml --profile metatron-lab-isolation config -q
docker compose -f deploy/metatron-lab/docker-compose.yaml --profile metatron-lab-runner config -q
python3 -m scripts.metatron_lab validate
python3 -m scripts.metatron_lab checklist
pytest -q tests/test_metatron_lab_compose_guard.py
make validate-min
```

## PR body contract (mirror)

- **Deferred / Follow-ups:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-metatron-offensive-lab-out-of-band`
- **Orchestration:** this packet path + roster above.
- **Explicit non-goals:** no product METATRON surface; no OpenAPI sync.

## References

- Epic 1 packet: `docs/orchestration/METATRON_TRACK_A_EPIC1_TASK_PACKET_2026-04-06.md:1`
- ADR: `docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md:1`
- RoE: `docs/security/METATRON_LAB_RULES_OF_ENGAGEMENT.md:1`
