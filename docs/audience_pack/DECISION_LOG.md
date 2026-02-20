<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Decision Log: Audience Documentation Pack

Дата: 20 февраля 2026 года (`America/New_York`)

## Контекст

Исходный пакет хорошо объяснял, что сделано в продукте, но недостаточно отвечал
на критичные внешние вопросы:
- почему именно PulsePlate,
- почему именно сейчас,
- почему это должно работать экономически и коммерчески.

## Ключевой Вывод

Пакет должен отвечать не только "что сделано", но и
"почему нам / почему сейчас".

## Что Было Сохранено

1. Разделение по аудиториям.
2. `FACTS_CANONICAL.md` как единый source of truth.
3. Wellness-only language и запрет medical claims.
4. AI report cadence (daily/weekly/monthly/quarterly).

## Что Было Изменено (Set A)

1. Investor doc: обновлен 90-second pitch, why-now, why-us, ask framework.
2. Marketing doc: activity-list заменен на KPI hypothesis board.
3. Role guides: 15 ролей перегруппированы в Build/Grow/Steer + day-1 checklists.
4. Sales doc: generic outreach заменен на ICP-specific варианты.
5. AI report templates: добавлены заполненные daily/weekly demo examples.
6. Добавлен `SOCIAL_PROOF_BASELINE.md` как отдельный доказательный слой.

## Decision Rules

1. Любая цифра без источника маркируется placeholder (`[VERIFY_*]`).
2. Любой внешний claim проходит claim-hygiene проверку.
3. Любой GTM тезис должен иметь KPI, owner и decision rule.
4. Любой docs пакет должен иметь owner и cadence обновления.

## Приоритизация Следующих Шагов

Высокий приоритет (минимум усилий, максимум эффекта):
1. Pitch с цифрами и конкурентным углом.
2. GTM гипотезы вместо activity-list.
3. Social proof baseline для sales/investor коммуникации.

Средний/долгий контур:
- unit economics,
- activation/retention playbook,
- monetization log,
- roadmap with kill criteria.

## Агентный Вклад

- Coordinator: split на docs-only поток без вмешательства в runtime PR.
- Docs track: переработка narrative для инвестора, маркетинга и sales.
- Ledger track: deferred элементы вынесены в backlog для управляемого follow-up.

## Security Notes

- Дисциплина wellness-safe wording сохраняется как обязательная.
- Неподтвержденные рыночные/финансовые значения не публикуются как факты.

## Marketing & GTM

- Пакет переводится в режим living-doc, ориентированный на KPI и decision cycles.
- Основной фокус: быстрее закрывать вопросы "почему сейчас" и "чем лучше X".
