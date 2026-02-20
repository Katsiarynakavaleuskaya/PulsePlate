<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Sales + Social + Onboarding Base

Дата версии: 20 февраля 2026 года (`America/New_York`)

## Что Уже Сделано Хорошо

- Есть базовый demo flow и objection handling.
- Есть стартовые outreach шаблоны и social pillars.

## Что Улучшаем Сейчас

- Убираем generic outreach.
- Добавляем 2 отраслевых шаблона с понятным пилотным CTA.
- Добавляем anti-generic правила для команды.

## Demo Script (20-25 минут)

### 00:00-03:00: Framing

- Цель встречи: один пилот, один KPI, одна дата решения.
- Фраза: "Покажу, где у вас теряется действие после метрик и как это измерить за 14 дней".

### 03:00-08:00: Discovery

Вопросы:
- "Где у вас главный drop-off после первого check-in?"
- "Какая метрика сейчас приоритет: activation, D7 retention, paid conversion?"
- "Какой KPI достаточен для решения масштабировать?"

### 08:00-16:00: Product Narrative

Показать путь:
- данные пользователя,
- интерпретация,
- daily action layer,
- weekly continuity.

### 16:00-21:00: Pilot Offer

- срок: 14 дней,
- scope: 1 сценарий,
- KPI: 1 primary + 1 guardrail,
- owner: по одному с каждой стороны.

### 21:00-25:00: Next Step

- фиксируем стартовую дату,
- фиксируем формат weekly review,
- фиксируем decision rule.

## Anti-Generic Outreach Rules

1. Запрещено отправлять шаблон без отраслевого pain.
2. Запрещено писать "AI улучшит всё" без конкретного KPI.
3. Каждый outreach должен содержать:
- наблюдение,
- гипотезу,
- предложение пилота,
- критерий успеха.

## Outreach Variant 1: Fitness App (B2B)

Тема: `14-day pilot: reduce post-check-in drop-off`

Текст:
"Замечаю, что у большинства fitness-приложений drop-off происходит после первого check-in:
пользователь видит цифру, но не понимает следующий шаг.

У PulsePlate есть готовый модуль: интерпретация + daily action layer.
Предлагаю пилот на 14 дней с одним KPI:
`[VERIFY_VALUE:B2B_PILOT_KPI]`.

Если интересно, пришлю one-pager и пилотный план на 1 страницу".

## Outreach Variant 2: Wellness Coach (B2C Individual)

Тема: `Автоматизировать daily контур клиентов за 2 недели`

Текст:
"Если вы ведете клиентов вручную через таблицы или spreadsheets,
мы можем автоматизировать ежедневный контур:
план + shopping list + прогресс.

Стартуем с 1 сценария и одним KPI:
`[VERIFY_VALUE:B2C_PILOT_KPI]`.

Если ок, отправлю короткий onboarding flow и пилотный чеклист".

## Objection Handling (Обновленный)

| Возражение | Ответ | Evidence |
|---|---|---|
| "У нас уже есть трекер" | "Мы не дублируем трекер, мы закрываем gap между цифрой и действием" | demo flow + pilot KPI |
| "AI ненадежен" | "Работаем через guardrails, quotas, deterministic review" | policy + CI artifacts |
| "Слишком дорого" | "Начинаем с узкого пилота и проверяем экономику до scale" | pilot economics sheet |
| "Риски по claims" | "Wellness-only wording, без medical обещаний" | compliance rules |

## Social Content Engine

| Pillar | Формат | KPI |
|---|---|---|
| Practical wellness | short video, carousel | saves, shares |
| Product proof | before/after narrative | click-to-signup |
| Founder insight | weekly post | engaged reach |
| Pilot outcomes | case snippet | demo requests |

## Onboarding Script (Day 1 User)

- "Где вы сейчас".
- "Что это значит".
- "Что сделать сегодня".
- "Как закрепить на неделе".

Обязательная строка:
"PulsePlate — wellness-инструмент и не заменяет консультацию лицензированного
медицинского специалиста".

## Security Notes

- Никаких медицинских обещаний в outreach и social.
- Никаких неподтвержденных цифр без placeholder/source.
- Любой кейс публикуется только после review owner + compliance owner.

## Marketing & GTM

- Outreach = hypothesis-driven, не mass template blast.
- Каждому шаблону нужен ICP, KPI и decision rule.
- Пилотные кейсы должны превращаться в repeatable sales playbook.
