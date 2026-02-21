# Analytics (Vendor-agnostic)

**Purpose:** Provide repo-native, vendor-agnostic artifacts for product analytics and experimentation so that:

- metric definitions do not drift silently
- experiments are tracked end-to-end (hypothesis → decision → promotion)
- analysis requests and outputs are reproducible (query/pseudocode + assumptions + caveats)

**Non-goal:** This folder does not prescribe a specific vendor stack (Amplitude/Mixpanel/Grafana/etc.).
Integrations and runtime telemetry changes must land in separate runtime PRs with privacy decisions.

---

## Files (canonical surfaces)

- `ANALYTICS_INDEX.md` — catalog of metrics / dashboards / data sources (high-level, “what exists”)
- `METRICS_CATALOG.md` — formal metric definitions and event taxonomy (SoT for semantics)
- `DATA_CATALOG.md` — data source and schema semantics (SoT for fields/meaning)
- `EXPERIMENT_REGISTRY.md` — active + completed experiments and decisions
- `DASHBOARD_BASELINE_REQUIREMENTS.md` — Wave 1 dashboard goals, segments, data sources, KPI

---

## Ownership (recommended)

- **Primary owner:** `data-scientist-agent` (drafting hub; see `.cursor/agents/data-scientist-agent.md`)
- **Reviewers (task-dependent):**
  - `marketing-strategist` for growth funnels/CTA experiments
  - `epistemology-discovery-agent` for falsifiability + negative controls
