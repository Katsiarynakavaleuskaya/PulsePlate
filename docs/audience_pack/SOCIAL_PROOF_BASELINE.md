<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Social Proof Baseline

Дата версии: 20 февраля 2026 года (`America/New_York`)

## Назначение

Этот файл нужен, чтобы внешние материалы не выглядели как "только планы".
Он задает единый шаблон для доказательной базы: отзывы, usage metrics,
competitive proof.

## 1) Testimonial Templates

### Template A: Product user

- Persona: `[VERIFY_VALUE:PERSONA_NAME]`
- Context: `[VERIFY_VALUE:USE_CASE]`
- Before: `[VERIFY_VALUE:BEFORE_STATE]`
- After: `[VERIFY_VALUE:AFTER_STATE]`
- Quote (wellness-safe): `[VERIFY_VALUE:USER_QUOTE]`
- Consent status: `[VERIFY_VALUE:CONSENT_STATUS]`

### Template B: Pilot partner

- Partner type: `[VERIFY_VALUE:PARTNER_TYPE]`
- KPI objective: `[VERIFY_VALUE:PILOT_KPI]`
- Pilot period: `[VERIFY_VALUE:PILOT_PERIOD]`
- Observed change: `[VERIFY_VALUE:OBSERVED_CHANGE]`
- Quote: `[VERIFY_VALUE:PARTNER_QUOTE]`
- Approval status: `[VERIFY_VALUE:APPROVAL_STATUS]`

## 2) Usage Metrics Baseline Template

| Metric | Current Value | Source | Last Updated | Owner |
|---|---|---|---|---|
| DAU | `[VERIFY_VALUE:DAU]` | `[VERIFY_SOURCE:DAU]` | `[VERIFY_VALUE:DAU_DATE]` | `[VERIFY_VALUE:DAU_OWNER]` |
| Session Length | `[VERIFY_VALUE:SESSION_LENGTH]` | `[VERIFY_SOURCE:SESSION_LENGTH]` | `[VERIFY_VALUE:SESSION_DATE]` | `[VERIFY_VALUE:SESSION_OWNER]` |
| D1 Activation | `[VERIFY_VALUE:D1_ACTIVATION]` | `[VERIFY_SOURCE:D1_ACTIVATION]` | `[VERIFY_VALUE:D1_DATE]` | `[VERIFY_VALUE:D1_OWNER]` |
| D7 Retention | `[VERIFY_VALUE:D7_RETENTION]` | `[VERIFY_SOURCE:D7_RETENTION]` | `[VERIFY_VALUE:D7_DATE]` | `[VERIFY_VALUE:D7_OWNER]` |
| Trial -> Paid | `[VERIFY_VALUE:TRIAL_TO_PAID]` | `[VERIFY_SOURCE:TRIAL_TO_PAID]` | `[VERIFY_VALUE:TRIAL_DATE]` | `[VERIFY_VALUE:TRIAL_OWNER]` |

## 3) Competitor Comparison Placeholder

| Capability | PulsePlate | Competitor A | Competitor B | Evidence |
|---|---|---|---|---|
| Metric tracking | `[VERIFY_VALUE:PULSE_METRIC_TRACKING]` | `[VERIFY_VALUE:COMP_A_TRACKING]` | `[VERIFY_VALUE:COMP_B_TRACKING]` | `[VERIFY_SOURCE:COMP_TRACKING]` |
| Action layer | `[VERIFY_VALUE:PULSE_ACTION_LAYER]` | `[VERIFY_VALUE:COMP_A_ACTION]` | `[VERIFY_VALUE:COMP_B_ACTION]` | `[VERIFY_SOURCE:COMP_ACTION]` |
| Tier model | `[VERIFY_VALUE:PULSE_TIER]` | `[VERIFY_VALUE:COMP_A_TIER]` | `[VERIFY_VALUE:COMP_B_TIER]` | `[VERIFY_SOURCE:COMP_TIER]` |
| Compliance wording | `[VERIFY_VALUE:PULSE_COMPLIANCE]` | `[VERIFY_VALUE:COMP_A_COMPLIANCE]` | `[VERIFY_VALUE:COMP_B_COMPLIANCE]` | `[VERIFY_SOURCE:COMP_COMPLIANCE]` |

## 4) Evidence Quality Rules

1. Нет source -> нет публичного claim.
2. Нет consent -> нет публикации testimonial.
3. Любая метрика имеет owner и дату обновления.
4. Любое сравнение с конкурентами опирается на проверяемый источник.

## 5) Proof Pack Minimum

Перед external коммуникацией должны быть готовы минимум:
- 2 пользовательских testimonial draft,
- 1 партнерский pilot snippet,
- 5 базовых метрик с owner/date,
- 1 конкурентная таблица с source.

## Security Notes

- Любой social proof должен быть wellness-safe и без medical claims.
- Личные данные и чувствительные health детали не публикуются.
- Consent status обязателен для каждого кейса.

## Marketing & GTM

- Social proof — это инфраструктура доверия для sales и investor narratives.
- Proof stack обновляется по cadence, а не перед запуском в последний день.
- Все внешние one-pagers должны ссылаться на этот baseline-файл.
