<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# PulsePlate Audience Pack

Дата версии: 20 февраля 2026 года (`America/New_York`)

## Назначение

Этот пакет объясняет PulsePlate для разных аудиторий:
- инвесторы и публичные стейкхолдеры,
- инженерные команды,
- маркетинг/дизайн/growth,
- sales/onboarding/support.

## Что Внутри

- `docs/audience_pack/FACTS_CANONICAL.md` — единые факты и архитектурные ограничения.
- `docs/audience_pack/INVESTOR_PUBLIC_OVERVIEW.md` — investor/public narrative + ask framework.
- `docs/audience_pack/ENGINEERING_OVERVIEW.md` — технический срез для разработчиков.
- `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md` — GTM с KPI-гипотезами.
- `docs/audience_pack/ROLE_GUIDES.md` — Build/Grow/Steer кластеры + day-1 checklist.
- `docs/audience_pack/SALES_SOCIAL_ONBOARDING_BASE.md` — demo/outreach/onboarding playbook.
- `docs/audience_pack/AI_REPORT_TEMPLATES.md` — шаблоны + заполненные daily/weekly demo samples.
- `docs/audience_pack/SOCIAL_PROOF_BASELINE.md` — testimonials/metrics/competitor proof baseline.
- `docs/audience_pack/DECISION_LOG.md` — почему пакет перестроен в сторону "почему мы/почему сейчас".

## Owner & Cadence Protocol

| Документ | Primary Owner | Cadence | Review Gate |
|---|---|---|---|
| FACTS_CANONICAL | Product + Backend | Monthly | architecture + compliance |
| INVESTOR_PUBLIC_OVERVIEW | Founder + Product Marketing | Monthly | claim hygiene + strategy |
| MARKETING_DESIGN_OVERVIEW | Growth + Design | Bi-weekly | KPI board review |
| ROLE_GUIDES | Operations + Leads | Monthly | onboarding sync |
| SALES_SOCIAL_ONBOARDING_BASE | Sales Lead | Weekly | message + KPI review |
| AI_REPORT_TEMPLATES | AI Trend Reporter | Monthly | reporting quality |
| SOCIAL_PROOF_BASELINE | Growth Ops + Sales | Weekly | source + consent validation |
| DECISION_LOG | Coordinator | Per major update | decision traceability |

## Как Использовать

1. Начинать с `FACTS_CANONICAL.md` перед любыми внешними материалами.
2. Для investor/sales коммуникации использовать в связке:
- `INVESTOR_PUBLIC_OVERVIEW.md`,
- `SOCIAL_PROOF_BASELINE.md`,
- `SALES_SOCIAL_ONBOARDING_BASE.md`.
3. Для GTM-операций использовать:
- `MARKETING_DESIGN_OVERVIEW.md`,
- `AI_REPORT_TEMPLATES.md`.
4. Для onboarding команды использовать `ROLE_GUIDES.md`.

## Claim Hygiene Standard

- Подтвержденная цифра: source обязателен.
- Неподтвержденная цифра: только placeholder (`[VERIFY_SOURCE:*]`, `[VERIFY_VALUE:*]`).
- Без source/placeholder — claim удаляется.

## Security Notes

- PulsePlate позиционируется как wellness-продукт, не медицинская диагностика.
- Медицинские обещания в маркетинговых/инвесторских текстах запрещены.
- Social proof публикуется только при соблюдении consent и privacy требований.

## Marketing & GTM

- Пакет используется как operating system для внешней коммуникации.
- Каждая гипотеза должна иметь KPI, owner и decision rule.
- Главный нарратив: "данные -> интерпретация -> ежедневное действие".
