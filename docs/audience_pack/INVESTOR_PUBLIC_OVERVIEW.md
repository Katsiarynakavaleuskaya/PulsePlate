<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Investor + Public Overview (Простым Языком)

Дата версии: 20 февраля 2026 года (`America/New_York`)

## Что Уже Сделано Хорошо

- Структура по аудиториям уже разделена: инвесторы, инженеры, маркетинг.
- `FACTS_CANONICAL.md` уже работает как единый источник правды.
- Wellness-only позиционирование и запрет medical claims уже встроены.

## 90-Second Pitch (Обновленная Версия)

PulsePlate решает проблему, которую не решают обычные fitness-трекеры:
пользователь видит BMI/калории, но не понимает, что делать завтра.

Рынок растет, но большинство решений останавливаются на уровне "показать цифры".
PulsePlate делает следующий шаг: превращает метрики в ежедневный контур действий.

Конкуренты дают данные. Мы даем действие:
- интерпретация,
- ежедневный план,
- shopping list,
- повторяемый ритм прогресса.

Модель: freemium -> подписка (`FREE -> PRO -> VIP`; evidence: `app/middleware/api_tiers.py:43`).
Текущее состояние: backend/web/iOS и quality-process подтверждаются репо-артефактами;
runtime-статус выносится в placeholder `[VERIFY_VALUE:RUNTIME_STATUS]`
(evidence: `app/main.py:1`, `frontend/src/main.tsx:2`, `ios/README.md:1`, `Makefile:134`,
`tests/test_repo_policy_guards.py:657`).

Ask:
- пилот с измеримым KPI,
- стратегическое партнерство,
- или инвестиционный раунд под масштабирование.

## Прозрачность По Цифрам (Claim Hygiene)

Ниже используются только:
- подтвержденные показатели, или
- placeholders до верификации.

| Показатель | Значение в коммуникации | Статус | Источник |
|---|---|---|---|
| TAM wellness software 2028 | `[VERIFY_VALUE:TAM_2028]` | Требует верификации | `[VERIFY_SOURCE:TAM_2028]` |
| Growth YoY | `[VERIFY_VALUE:WELLNESS_YOY]` | Требует верификации | `[VERIFY_SOURCE:WELLNESS_YOY]` |
| Subscription ARPU | `[VERIFY_VALUE:SUBSCRIPTION_ARPU]` | Требует верификации | `[VERIFY_SOURCE:ARPU]` |
| Pilot conversion uplift | `[VERIFY_VALUE:PILOT_UPLIFT]` | Требует верификации | `[VERIFY_SOURCE:PILOT]` |

## Почему Сейчас

- Пользовательский спрос на wellness AI растет, но доверие к "магическим" обещаниям падает.
- Рынок сдвигается к продуктам с прозрачной логикой и измеримым результатом.
- У PulsePlate уже есть продуктовый каркас; тезис "масштабирование без смены архитектуры"
  фиксируется как гипотеза до верификации: `[VERIFY_VALUE:SCALING_WITHOUT_REWRITE]`.

## Почему Мы

- Единый backend для web + iOS с контрактным подходом (evidence: `app/main.py:1`,
  `frontend/src/main.tsx:2`, `ios/README.md:1`).
- Tier-модель монетизации встроена через `FREE/PRO/VIP`
  (evidence: `app/middleware/api_tiers.py:43`).
- Безопасность и claim-discipline формализованы; внешний эффект подтверждается только после
  проверки: `[VERIFY_VALUE:SECURITY_AND_CLAIMS_EFFECTIVENESS]`.
- Policy-first процессы (guard tests + CI gates) зафиксированы в репо
  (evidence: `tests/test_repo_policy_guards.py:657`, `Makefile:134`).

## Competitive Angle (На Одной Странице)

| Вопрос | Типичный трекер | PulsePlate |
|---|---|---|
| Показывает метрики | Да | Да (у обоих) |
| Объясняет смысл для пользователя | Частично | Да |
| Дает ежедневный action layer | Редко | Да |
| Структура для роста по tier-модели | Частично | Да |
| Wellness-safe коммуникация | Непоследовательно | Да, как политика |

## Текущее Состояние Продукта

- Backend: FastAPI entrypoint + core domain module
  (evidence: `app/main.py:1`, `core/bmi/engine.py:1`).
- Клиенты: web (React/TypeScript) + iOS (SwiftUI structure)
  (evidence: `frontend/src/main.tsx:2`, `ios/README.md:1`).
- Операционная дисциплина: `make verify` (lint/type/test-fast/diff-cov) + policy guards
  (evidence: `Makefile:134`, `tests/test_repo_policy_guards.py:657`).
- Продуктовый контур "метрики -> интерпретация -> ежедневные действия" публикуется как
  управленческая формулировка до доп.метрик adoption: `[VERIFY_VALUE:ACTION_LAYER_ADOPTION]`.

## Ask Framework (Для Инвестора Или Партнера)

1. Вариант "Pilot":
- Срок: `[VERIFY_VALUE:PILOT_DURATION]`
- KPI: `[VERIFY_VALUE:PILOT_KPI]`
- Success threshold: `[VERIFY_VALUE:PILOT_SUCCESS_THRESHOLD]`

2. Вариант "Partnership":
- Канал: `[VERIFY_VALUE:PARTNER_CHANNEL]`
- Совместный KPI: `[VERIFY_VALUE:PARTNER_KPI]`

3. Вариант "Investment":
- Размер раунда: `[VERIFY_VALUE:ROUND_SIZE]`
- Основные статьи использования: продукт, дистрибуция, безопасность.

## Security Notes

- PulsePlate — wellness-продукт, не медицинская диагностика и не лечение.
- Формулировки "лечит", "диагностирует", "предотвращает болезнь" запрещены.
- Любые внешние численные claims публикуются только с source или placeholder.

## Marketing & GTM

- Ключевая коммуникация: "from numbers to daily action".
- Внешние материалы должны отвечать на три вопроса:
  - почему сейчас,
  - почему мы,
  - почему экономика может сойтись.
