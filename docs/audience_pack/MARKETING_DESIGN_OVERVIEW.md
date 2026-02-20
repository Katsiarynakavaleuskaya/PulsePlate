<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Marketing + Design + Growth Overview

Дата версии: 20 февраля 2026 года (`America/New_York`)

## Что Уже Сделано Хорошо

- Четкая сегментация аудитории и единый language framework.
- Wellness-safe wording уже встроен в коммуникацию.
- Базовая структура каналов (ASO/SEO/Social/Product Hunt) уже есть.

## Главная Проблема Текущей Версии GTM

90-дневный блок был описан как список активностей.
Для роста нужен формат гипотез с KPI и правилами решений.

## GTM North Star

PulsePlate: "метрики -> интерпретация -> ежедневное действие".

Основной North Star KPI:
`[VERIFY_VALUE:NORTH_STAR_KPI]`

## 90-Day GTM Hypotheses (Вместо Activity-List)

| Hypothesis | Metric | Baseline | Target | Owner | Check Date | Decision Rule |
|---|---|---|---|---|---|---|
| ASO subtitle A/B (3 варианта) поднимет install CVR | Impressions -> Install rate | `[VERIFY_VALUE:ASO_BASELINE]` | `+15%` | Growth Lead | 12 марта 2026 | Scale если uplift >= 10%, stop если < 5% |
| Landing SEO-кластер "AI wellness + habit" даст органический signup рост | Organic sessions -> Signup CVR | `[VERIFY_VALUE:SEO_BASELINE]` | `+20% signup` | Content Lead | 26 марта 2026 | Continue если CAC <= `[VERIFY_VALUE:CAC_SEO_LIMIT]` |
| Short-form UGC (3 формата) улучшит activation quality | Install -> D1 activation | `[VERIFY_VALUE:D1_BASELINE]` | `+12%` | Social Lead | 2 апреля 2026 | Keep 2 лучших формата, 1 отключить |
| Product Hunt launch week увеличит qualified waitlist | Qualified waitlist/week | `[VERIFY_VALUE:PH_BASELINE]` | `x2` | Founder + Marketing | 16 апреля 2026 | Expand если quality score >= `[VERIFY_VALUE:PH_QUALITY]` |
| Lifecycle onboarding copy снизит early churn | D7 retention | `[VERIFY_VALUE:D7_BASELINE]` | `+8 p.p.` | Product Marketing | 30 апреля 2026 | Ship globally если D7 uplift >= 5 p.p. |

## ICP / JTBD (Уточненный)

| ICP | JTBD | Pain | Value Message |
|---|---|---|---|
| Новички в wellness | "Хочу начать без перегруза" | Не понимаю, что делать с цифрами | "Первый actionable шаг за одну сессию" |
| Fitness users | "Хочу управлять прогрессом, а не только смотреть графики" | Много данных, мало решений | "Понятная интерпретация + daily loop" |
| Занятые профессионалы | "Хочу меньше ручных решений" | Decision fatigue | "Автоматизированный daily contour" |

## Activation & Retention Mini Playbook

### Aha Moment

Пользователь за первую сессию получает:
- ясную интерпретацию состояния,
- первый персональный action,
- понятный следующий шаг на завтра.

### Trigger Map

- Day 1: "первый actionable plan".
- Day 3: "подтверждение прогресса / корректировка".
- Day 7: "weekly continuity и закрепление привычки".

### Churn Signals

- отсутствие completion ключевого шага в первые 48 часов;
- нулевая реакция на Day 3 touchpoint;
- падение открытия приложения к Day 7.

### Re-engagement

- push/email сценарий с одним понятным действием;
- без guilt messaging;
- с безопасной wellness формулировкой.

## Second-Order Distribution Layer

| Блок | Кто делает | Бюджет/ресурс | Частота решения |
|---|---|---|---|
| Контент production | Content + Designer | `[VERIFY_VALUE:CONTENT_BUDGET]` | Weekly review |
| Канальный приоритизатор | Growth + Product | `[VERIFY_VALUE:GROWTH_BUDGET]` | Bi-weekly |
| Масштабирование winners | Founder + Growth | По факту KPI | Monthly |
| Kill/Stop решения | Product Council | N/A | Monthly |

## Monetization Experiments (Верхний Уровень)

| Эксперимент | KPI | Статус | Следующий шаг |
|---|---|---|---|
| Soft vs hard paywall | Trial start, Paid conversion | `[VERIFY_VALUE:PAYWALL_STATUS]` | Подтвердить baseline |
| Pricing ladder test | ARPU, churn | `[VERIFY_VALUE:PRICING_STATUS]` | Подготовить A/B дизайн |
| B2B pilot offer | Pilot-to-paid | `[VERIFY_VALUE:B2B_STATUS]` | 2 целевых пилота |

## Security Notes

- Коммуникация остается wellness-only; medical claims запрещены.
- Любой KPI без источника должен быть placeholder.
- Маркетинг не публикует цифры без верификации владельцем метрики.

## Marketing & GTM

- GTM считается системой гипотез, а не списком задач.
- Каждый канал обязан иметь baseline, target и decision rule.
- Все решения о масштабировании принимаются только по данным и cadence-ревью.
