<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Roadmap with Kill Criteria

Версия: 2026-02-20 (TZ: America/New_York)

## Назначение

Этот roadmap исключает "wishlist planning".
Каждая ставка имеет success metric и kill criteria.

## Roadmap Table

| Quarter | Bet | Success Metric | Kill Criteria | Owner | Decision Date |
|---|---|---|---|---|---|
| Q1 2026 | Investor-ready narrative + social proof | `[VERIFY_VALUE:Q1_SUCCESS]` | `<[VERIFY_VALUE:Q1_KILL_THRESHOLD]` after 2 cycles | Founder + Product | `[VERIFY_VALUE:Q1_DECISION_DATE]` |
| Q2 2026 | KPI-driven GTM machine | `[VERIFY_VALUE:Q2_SUCCESS]` | CAC/LTV gap above `[VERIFY_VALUE:Q2_KILL_CAC_LTV]` | Growth Lead | `[VERIFY_VALUE:Q2_DECISION_DATE]` |
| Q3 2026 | Monetization experiments | `[VERIFY_VALUE:Q3_SUCCESS]` | trial->paid uplift below `[VERIFY_VALUE:Q3_KILL]` | Product Marketing | `[VERIFY_VALUE:Q3_DECISION_DATE]` |
| Q4 2026 | Partnership expansion | `[VERIFY_VALUE:Q4_SUCCESS]` | pilot-to-paid below `[VERIFY_VALUE:Q4_KILL]` | Sales + Partnerships | `[VERIFY_VALUE:Q4_DECISION_DATE]` |

## Decision Rules

1. Нет метрики успеха -> ставка не стартует.
2. Нет kill criteria -> ставка не считается управляемой.
3. Decision date пропущен -> автоэскалация на founder review.

## Governance Cadence

- Monthly: проверка status всех активных bets.
- Quarterly: stop/continue/reinvest decisions.
- Ad-hoc: если breached kill criteria.

## Security Notes

- Kill criteria нужен для предотвращения затратного "scope drift".
- Любые high-cost AI инициативы должны иметь отдельный бюджетный guardrail.

## Marketing & GTM

- Roadmap должен связывать narrative, distribution и economics в одну систему.
- Без kill criteria GTM превращается в набор несвязанных активностей.
