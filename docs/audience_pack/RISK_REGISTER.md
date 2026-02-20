<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Risk Register

Дата версии: 20 февраля 2026 года (`America/New_York`)

## Назначение

Риск-реестр нужен для управляемых решений, а не для абстрактного "риски есть".

## Canonical Risk Table

| Risk | Probability | Impact | Mitigation | Owner | Kill Criteria |
|---|---|---|---|---|---|
| Wellness -> medical drift in messaging | Medium | High | claim-hygiene policy + compliance review | Product + Marketing | regulatory trigger `[VERIFY_VALUE:REG_TRIGGER]` |
| LLM cost spike | High | Medium | hard monthly quota + rate limits | Backend | `>$[VERIFY_VALUE:LLM_COST_LIMIT]/user/month` |
| App Store rejection | Medium | High | pre-review checklist + wording validation | iOS Lead | critical rejection reason unresolved > `[VERIFY_VALUE:STORE_WINDOW]` days |
| KPI vanity bias (no true growth) | Medium | Medium | KPI board with decision rules | Growth Lead | 2 cycles without causal uplift |
| Data privacy incident | Low | High | access controls + minimization + audit trail | Security Lead | severity `[VERIFY_VALUE:SEC_SEVERITY]` incident |
| Team scope drift across PRs | High | Medium | docs-only/runtime split + branch policy | Coordinator | > `[VERIFY_VALUE:SCOPE_DRIFT_THRESHOLD]` mixed files per PR |

## Risk Review Cadence

- Weekly: operational risks (cost, KPI drift, rollout issues).
- Monthly: strategic risks (regulation, market, positioning).
- Quarterly: portfolio risks and kill/reinvest decisions.

## Escalation Rules

1. High impact + medium/high probability -> review within 24h.
2. Любой риск с kill criteria breach -> stop/rollback decision mandatory.
3. Любой внешний claim conflict -> immediate content freeze до исправления.

## Security Notes

- Риск-реестр должен ссылаться на факты, а не на мнения.
- Privacy/security риски не закрываются текстом, только процессом и контролями.

## Marketing & GTM

- Risk register защищает GTM от "growth любой ценой".
- Kill criteria должны быть видимы для founders, sales и growth.
