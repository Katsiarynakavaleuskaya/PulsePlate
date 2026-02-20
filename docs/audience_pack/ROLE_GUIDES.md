<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Role Guides: Clustered Onboarding Map

Дата версии: 20 февраля 2026 года (`America/New_York`)

## Что Уже Сделано Хорошо

- Рольовая карта уже описана и покрывает ключевые функции команды.
- Cross-functional зависимости уже обозначены.

## Главная Проблема

Одна большая таблица на 15 ролей перегружает onboarding.
Новый формат: 3 кластера + Day 1 checklist.

## Cluster 1: Build

### Роли

- Senior Data Scientist / ML Specialist
- Senior ML Engineer
- Senior Backend Developer
- Senior Frontend Developer
- Senior App Store Dev
- Senior QA Engineer
- Senior Cybersecurity Specialist

### Mission

Собрать надежный и безопасный продуктовый контур:
contract-first API, deterministic tests, guardrails, predictable quality.

### Day 1 Checklist (Build)

1. Прочитать `docs/audience_pack/FACTS_CANONICAL.md`.
2. Прочитать `docs/audience_pack/ENGINEERING_OVERVIEW.md`.
3. Сверить свои задачи с AGENTS policy и quality gates.
4. Проверить границы ответственности (что можно менять, что нельзя).
5. Зафиксировать owner-metric на текущий спринт.

## Cluster 2: Grow

### Роли

- Senior Marketing & Growth
- Product Designer / Creative
- Sales / Partnerships
- Support / Success

### Mission

Построить устойчивую систему acquisition -> activation -> retention -> revenue,
без overclaim и без потери доверия.

### Day 1 Checklist (Grow)

1. Прочитать `docs/audience_pack/INVESTOR_PUBLIC_OVERVIEW.md`.
2. Прочитать `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md`.
3. Прочитать `docs/audience_pack/SALES_SOCIAL_ONBOARDING_BASE.md`.
4. Согласовать гипотезы и KPI с Product/Growth owner.
5. Проверить wording на compliance (wellness-only).

## Cluster 3: Steer

### Роли

- AI Product Architect
- AI Business Strategist
- AI Trend Reporter
- AI Tutor & Mentor

### Mission

Держать стратегический вектор: где рынок, где окно возможностей,
какие ставки делаем, а какие закрываем.

### Day 1 Checklist (Steer)

1. Прочитать `docs/audience_pack/FACTS_CANONICAL.md`.
2. Прочитать `docs/audience_pack/INVESTOR_PUBLIC_OVERVIEW.md`.
3. Прочитать `docs/audience_pack/AI_REPORT_TEMPLATES.md`.
4. Согласовать decision cadence (weekly/monthly/quarterly).
5. Проверить, что roadmap имеет success + kill criteria.

## Shared Interlocks (Межкластерные Правила)

1. Build не обещает то, чего нет в контракте.
2. Grow не публикует неподтвержденные цифры.
3. Steer не принимает стратегические решения без evidence.
4. Все кластеры используют единый source of truth.

## Security Notes

- Любой публичный текст проверяется на medical-claim drift.
- Любой технический релиз проверяется через policy guards и CI.
- Любая новая инициатива должна иметь owner и kill criteria.

## Marketing & GTM

- Clustering ускоряет onboarding и снижает коммуникационные потери.
- Каждому кластеру нужен свой KPI contour и свой cadence.
- Cross-cluster sync обязателен минимум раз в неделю.
