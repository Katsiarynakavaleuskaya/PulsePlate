<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# PulsePlate Audience Pack

Версия: 2026-02-20 (TZ: America/New_York)

## Назначение

Этот пакет объясняет PulsePlate для разных аудиторий:
- инвесторы и публичные стейкхолдеры,
- инженерные команды,
- маркетинг/дизайн/growth,
- sales/onboarding/support.

## Layer 1: Core Pack (Set A)

- `docs/audience_pack/FACTS_CANONICAL.md` — фактовый source of truth.
- `docs/audience_pack/INVESTOR_PUBLIC_OVERVIEW.md` — pitch, why-now, why-us, ask.
- `docs/audience_pack/ENGINEERING_OVERVIEW.md` — техническая архитектура.
- `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md` — GTM гипотезы и KPI.
- `docs/audience_pack/ROLE_GUIDES.md` — Build/Grow/Steer + day-1 checklists.
- `docs/audience_pack/SALES_SOCIAL_ONBOARDING_BASE.md` — outreach/demo/onboarding base.
- `docs/audience_pack/AI_REPORT_TEMPLATES.md` — templates + filled daily/weekly samples.
- `docs/audience_pack/SOCIAL_PROOF_BASELINE.md` — testimonials/metrics/competitor placeholders.
- `docs/audience_pack/DECISION_LOG.md` — ключевые решения по пакету.

## Layer 2: Strategic Pack (Set B)

- `docs/audience_pack/COMPETITIVE_INTELLIGENCE.md` — direct competitors + gap map + parity.
- `docs/audience_pack/RISK_REGISTER.md` — risk table with mitigation/owner/kill criteria.
- `docs/audience_pack/PROOF_PACK.md` — beta metrics, demo assets, mini-case templates.
- `docs/audience_pack/ROADMAP_KILL_CRITERIA.md` — roadmap with success + kill rules.
- `docs/audience_pack/NARRATIVE_AND_TEAM.md` — story arc, credibility, anti-portfolio.
- `docs/audience_pack/LIVING_DOCUMENT_PROTOCOL.md` — owner/cadence/review/expiry protocol.

## Layer 3: Business Collateral Pack

- `docs/audience_pack/B2B_PARTNERSHIP_PROPOSAL_SPEC.md` — canonical proposal source for partner-facing DOCX outputs.
- `docs/audience_pack/B2B_PITCH_DECK_SPEC.md` — canonical slide-by-slide source for partner/investor PPTX outputs.
- `docs/audience_pack/BUSINESS_COLLATERAL_AUTOMATION.md` — builder contract, output policy, and placeholder hygiene.
- `docs/executive/PR_PORTFOLIO_BRIEF_DIRECTORS_2026-03.md` — thin executive brief linked back to audience-pack fact/narrative SoT.

## Deferred Layer (Set C)

Пункты Set C зафиксированы в `docs/roadmap/BACKLOG_LEDGER.md`.
Без записи в ledger deferred-работа считается несуществующей.

## Owner & Cadence Protocol (Canonical SoT)

- Каноническая owner/cadence матрица находится в
  `docs/audience_pack/LIVING_DOCUMENT_PROTOCOL.md`.
- Любое изменение owner/cadence сначала вносится в этот документ, чтобы избежать drift.

## Claim Hygiene Standard

- Подтвержденная цифра -> source обязателен.
- Неподтвержденная цифра -> placeholder (`[VERIFY_SOURCE:*]`, `[VERIFY_VALUE:*]`).
- Без source/placeholder -> claim удаляется.

## Как Использовать

1. Перед любой коммуникацией начать с `FACTS_CANONICAL.md`.
2. Для investor/sales использовать связку:
- `INVESTOR_PUBLIC_OVERVIEW.md`,
- `SOCIAL_PROOF_BASELINE.md`,
- `PROOF_PACK.md`,
- `COMPETITIVE_INTELLIGENCE.md`.
3. Для GTM управления использовать:
- `MARKETING_DESIGN_OVERVIEW.md`,
- `ROADMAP_KILL_CRITERIA.md`,
- `RISK_REGISTER.md`.
4. Для обновляемости пакета следовать `LIVING_DOCUMENT_PROTOCOL.md`.
5. Для partner-ready collateral использовать markdown specs above and generate binaries locally rather than editing `.docx` / `.pptx` by hand.

## Security Notes

- PulsePlate — wellness-продукт, не медицинская диагностика.
- Медицинские обещания в маркетинговых/инвесторских текстах запрещены.
- Proof/data блоки публикуются только при соблюдении consent и source policy.

## Marketing & GTM

- Пакет работает как operating system для внешней коммуникации.
- Каждый GTM тезис должен иметь KPI, owner и decision rule.
- Главный нарратив: "данные -> интерпретация -> ежедневное действие".
