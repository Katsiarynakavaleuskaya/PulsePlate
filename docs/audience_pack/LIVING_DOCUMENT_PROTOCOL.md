<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Living Document Protocol

Версия: 2026-02-20 (TZ: America/New_York)

## Purpose

Нужен единый протокол, чтобы пакет не устаревал через 2-3 месяца.

## Version Header Standard

- Для всех audience-pack документов используется формат:
  `Версия: YYYY-MM-DD (TZ: America/New_York)`.

## Ownership Matrix

| Document | Primary Owner | Backup Owner | Update Cadence |
|---|---|---|---|
| FACTS_CANONICAL | Product Architect | Backend Lead | Monthly |
| INVESTOR_PUBLIC_OVERVIEW | Founder | Product Marketing | Monthly |
| MARKETING_DESIGN_OVERVIEW | Growth Lead | Design Lead | Bi-weekly |
| ROLE_GUIDES | Operations Lead | Coordinator | Monthly |
| SALES_SOCIAL_ONBOARDING_BASE | Sales Lead | Growth Lead | Weekly |
| AI_REPORT_TEMPLATES | AI Trend Reporter | Product Ops | Monthly |
| SOCIAL_PROOF_BASELINE | Growth Ops | Sales Lead | Weekly |
| COMPETITIVE_INTELLIGENCE | Product Marketing | Strategy Lead | Monthly |
| RISK_REGISTER | Security Lead | Product Architect | Monthly |
| PROOF_PACK | Growth Ops | Founder | Bi-weekly |
| ROADMAP_KILL_CRITERIA | Product Architect | Founder | Monthly |
| NARRATIVE_AND_TEAM | Founder | Marketing Lead | Monthly |

## Review Gates

1. Claim Hygiene Gate:
- source present or placeholder present.
2. Compliance Gate:
- no medical claims, wellness-safe wording.
3. Decision Gate:
- KPI/owner/check date present for GTM sections.
4. Freshness Gate:
- any section older than cadence window is flagged.

## Expiry / Refresh Rules

- Weekly docs: stale if > 10 days.
- Bi-weekly docs: stale if > 21 days.
- Monthly docs: stale if > 40 days.

Stale doc action:
1. auto-flag in weekly sync,
2. assign owner refresh window,
3. freeze external usage if high-risk stale.

## Change Logging Standard

Каждое существенное обновление фиксируется:
- in-file date,
- short change note,
- decision reference (`DECISION_LOG.md`).

## Cross-Team Workflow

1. Build updates factual capability.
2. Grow updates GTM + proof layers.
3. Steer validates strategy and kill criteria.
4. Coordinator signs off consistency.

## Security Notes

- Living-doc protocol предотвращает устаревшие claims во внешней коммуникации.
- Любой stale high-risk section должен быть заблокирован для external use.

## Marketing & GTM

- Обновляемость документов — часть distribution quality.
- Плохой cadence бьет по доверию сильнее, чем отсутствие нового слайда.
