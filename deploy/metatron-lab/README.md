# METATRON lab — deploy stub (out-of-band)

**Purpose:** Optional **isolated** Docker network placeholder for internal offensive-lab
workflows. This directory does **not** build the PulsePlate application image or add
METATRON to product runtime.

**Governance:**

- ADR: `docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md:1`
- RoE: `docs/security/METATRON_LAB_RULES_OF_ENGAGEMENT.md:1`
- Task packet: `docs/orchestration/METATRON_TRACK_A_EPIC1_TASK_PACKET_2026-04-06.md:1`

## Usage

Validate compose (no containers started):

```bash
docker compose -f deploy/metatron-lab/docker-compose.yaml --profile metatron-lab-isolation config -q
```

Operators attach METATRON or other lab containers to the `lab_internal` network only after
written authorization per RoE. Raw outputs belong under `artifacts/security_lab/` (gitignored).
