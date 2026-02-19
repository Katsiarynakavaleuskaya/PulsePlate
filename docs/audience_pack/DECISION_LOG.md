<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Decision Log: Audience Documentation Pack

Дата: 19 февраля 2026 года (`America/New_York`)

## Контекст
Пользовательский запрос: подготовить детальный обзор проекта для нескольких аудиторий как основу для продажи, рекламы, соцсетей и onboarding, с работой в отдельном worktree и многоагентным брейнштормингом.

## Принятые Решения
1. Создан отдельный `git worktree` для изоляции задач документирования.
2. Введен единый фактовый слой `FACTS_CANONICAL.md`, чтобы все аудитории опирались на одну правду.
3. Документация разделена на 3 основные аудитории + рольовой cross-functional слой.
4. Добавлен прикладной GTM блок (`SALES_SOCIAL_ONBOARDING_BASE.md`) с готовыми шаблонами, а не только обзорный текст.
5. Добавлены reusable-шаблоны AI-репортов (daily/weekly/monthly/quarterly).
6. В каждом документе есть секции `Security Notes` и `Marketing & GTM`.

## Агентный Вклад (Brainstorming)
В рамках задачи использованы специализированные агентные треки:
- coordinator track: task analysis, routing, DoD.
- architecture track: factual architecture summary.
- investor track: one-pager + FAQ + pitch.
- marketing track: ICP/JTBD + channel strategy + KPI frame.
- security/compliance track: safe wording + risk template.
- sales track: demo/objections/outreach.
- ai-reporting track: cadence templates.

## Ограничения
- PR-level bot comments недоступны до фактического открытия PR в remote.
- "Зеленое" состояние PR требует полного цикла локальных и удаленных проверок; локально можно выполнить hard gates и pre-commit.

## Что Нуждается В Следующей Итерации
1. Дополнить пакет конкретными скриншотами и визуальными примерами для media kit.
2. Связать каждый GTM тезис с текущими dashboard метриками команды.
3. Сверить пакет с актуальным roadmap перед внешним использованием.
4. Добавить версию на английском для международных партнеров/инвесторов.

## Security Notes
- Публичные материалы должны регулярно проходить compliance-проверку формулировок.
- Любые численные claims без проверяемого источника должны быть удалены.

## Marketing & GTM
- Пакет рассчитан как baseline и должен обновляться по cadence: weekly (операционные блоки), monthly (позиционирование и KPI narrative).
- Перед запуском кампании проводить short alignment с product + legal + security.
