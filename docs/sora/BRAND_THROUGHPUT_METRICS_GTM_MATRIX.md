# Brand Throughput Metrics + GTM Matrix (P2)

Date: 2026-02-19
Scope: HPP visual workflow acceleration

## 1) Throughput Metrics

Track weekly:
- Lead time (brief -> approved visual)
- Iteration count per approved asset
- Reject rate by failure tag
- Rework rate after FE/iOS handoff

## 2) Quality Metrics

- QA pass rate on first review
- Token drift incidents per sprint
- Accessibility rejection rate
- Mapping blockage rate (`blocked_by_design_url`, `blocked_by_node_id_capture`)

## 3) Product/Growth Metrics (where applicable)

- `hpp_live_cta_click_rate_by_variant`
- `paywall_open_from_live_by_variant`
- CTR uplift of updated visual treatments vs baseline

## 4) GTM Channels and Experiments

| Channel | Asset family | Primary metric | Cadence |
| --- | --- | --- | --- |
| App store screenshots | onboarding/paywall visuals | install-to-open uplift proxy | per release |
| Product Hunt / launch posts | hero + social cards | click-through rate | per campaign |
| Social short-form | mascot + CTA cards | engagement rate | weekly |
| In-app surfaces | home/plate/progress cards | CTA click rate | continuous |

## 5) Decision Gates

- Promote only assets that pass `SORA_STYLE_QA_CHECKLIST.md`
- Block rollout if safety/compliance checks fail
- Require coordinator sign-off for cross-channel release packs

## 6) Reporting Template

For each reporting cycle:
- what shipped
- throughput numbers
- quality failures by tag
- growth deltas vs baseline
- next corrective action
