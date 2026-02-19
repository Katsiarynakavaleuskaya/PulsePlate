<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Role Guides: Что Это За Проект Для Каждой Специальности

Дата версии: 19 февраля 2026 года (`America/New_York`)

## Назначение
Этот файл объясняет PulsePlate с позиции разных профессиональных ролей, чтобы:
- быстрее подключать новых участников,
- снизить рассинхрон между командами,
- держать единое понимание продукта.

## Карта Ролей

| Роль | Как Видит Проект | Главная Ответственность | Ключевые Артефакты |
|---|---|---|---|
| Senior Data Scientist / ML Specialist | Система поведенческих и health-сигналов с интерпретацией | Метрики качества, валидность гипотез, аналитические выводы | `core/*`, аналитика cohort/retention, eval reports |
| Senior ML Engineer | Production ML integration layer с cost/risk constraints | Надежная интеграция моделей, latency/cost контроль, fallback | `core/insight/*`, provider loaders, quota/rate limits |
| Senior Backend Developer | API + domain orchestration с четкими контрактами | API consistency, tier gating, runtime stability | `app/`, `core/`, schemas, routers, middleware |
| Senior Frontend Developer | Thin client для web с contract-first подходом | UX delivery без business-logic drift на клиенте | `frontend/src/api/*`, pages/features, generated types |
| Senior App Store Dev (iOS) | SwiftUI thin adapter поверх backend contracts | стабильный mobile UX, app-store readiness, release hygiene | `ios/PulsePlate/*`, networking layer, app metadata |
| Cursor Senior Specialist | Engineering productivity + workflow governance | стандартизация агентного workflow, соблюдение gate-политик | AGENTS/runbooks, CI triage, orchestration docs |
| Senior QA Engineer | Policy-as-tests система с guard invariants | детерминированные тесты, regression shielding | `tests/*`, guard suites, smoke + diff coverage |
| Senior Cybersecurity Specialist | API security + abuse prevention in wellness AI | auth, privacy, rate limiting, quota, threat boundaries | `app/security/*`, middleware, privacy endpoint, audit docs |
| Senior Marketing & Growth | freemium growth engine | acquisition->activation->retention->revenue pipeline | GTM plan, content matrix, channel KPI dashboards |
| AI Product Architect | целостная продуктовая система | roadmap, capability boundaries, value ladder | cross-functional specs, API contracts, role maps |
| AI Tutor & Mentor | образовательный слой для команды/пользователя | простые объяснения сложных тем, onboarding knowledge | explainers, onboarding scripts, FAQ materials |
| AI Wellness Analyst | wellness safety and applicability | корректное wellness positioning, безопасные рекомендации | disclaimer policy, wording library, risk notes |
| AI Trend Reporter | внешний сигнал для продуктовых решений | регулярные daily/weekly/monthly/quarterly AI reports | trend briefs, competitor scans, synthesis notes |
| AI Business Strategist | low-capex entry and monetization | быстрые гипотезы, каналы монетизации, unit economics | market options, pricing hypotheses, launch checklists |
| Product Designer / Creative | визуальная система ценности и доверия | ясный UX narrative, конверсионные сценарии | design system, creative briefs, onboarding flows |
| Sales / Partnerships | коммерциализация ценности | discovery, demo, objection handling, pilot conversion | sales scripts, proof pack, outreach templates |
| Support / Success | удержание и доверие пользователей | ясные ответы, снижение churn, escalation flow | help docs, response templates, issue taxonomy |

## Как Каждой Роли Быстро Войти В Проект (Первые 7 Дней)
1. Прочитать `docs/audience_pack/FACTS_CANONICAL.md`.
2. Прочитать профильный документ:
- инженерам: `docs/audience_pack/ENGINEERING_OVERVIEW.md`,
- маркетингу/дизайну: `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md`,
- внешним стейкхолдерам: `docs/audience_pack/INVESTOR_PUBLIC_OVERVIEW.md`.
3. Согласовать свою роль с KPI и owner-моделью.
4. Проверить, что любые публичные claim-ы соответствуют реальным capability.

## Межролевые Зависимости (Критические)
- Product/Architecture -> Engineering: определяют boundaries и backlog.
- Engineering -> Marketing/Sales: дает доказуемые capability и limits.
- Security/QA -> все роли: не дают нарушать безопасные и quality invariants.
- Marketing/Design -> Product: возвращают market signal для roadmap.
- Trend/Business roles -> Product/Growth: поставляют внешние возможности и риски.

## Decision Rules Для Конфликтных Ситуаций
1. Если маркетинговый claim конфликтует с кодом, приоритет у `FACTS_CANONICAL.md`.
2. Если фича нарушает guard/policy, релиз блокируется до исправления.
3. Если гипотеза дорогая и рискованная, запуск только через ограниченный пилот с KPI.
4. Если формулировка тянет в medical claim, переводим в wellness-safe wording.

## Security Notes
- Любая роль, работающая с коммуникацией, обязана соблюдать medical-claim boundaries.
- Любая роль, работающая с кодом, обязана сохранять quota/rate/auth guardrails.
- Для AI-инициатив всегда фиксировать privacy impact и abuse risk заранее.

## Marketing & GTM
- Каждая роль влияет на GTM: инженерия через надежность, дизайн через ясность, support через доверие.
- GTM-процесс должен быть кросс-функциональным: message, capability, proof, KPI.
- Единый формат доставки ценности: "что умеем -> зачем пользователю -> как измеряем".
