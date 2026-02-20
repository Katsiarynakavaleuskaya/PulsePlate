<!-- markdownlint-disable MD013 MD022 MD032 MD024 MD029 MD031 MD060 -->

# Proof Pack

Дата версии: 20 февраля 2026 года (`America/New_York`)

## Назначение

Proof Pack дает sales и investor-стороне пакет доказательств:
не "мы планируем", а "вот что уже видно и как это проверено".

## 1) Beta Metrics Block (Template)

| Metric | Value | Source | Confidence | Last Updated |
|---|---|---|---|---|
| Beta users | `[VERIFY_VALUE:BETA_USERS]` | `[VERIFY_SOURCE:BETA_USERS]` | `[VERIFY_VALUE:BETA_USERS_CONF]` | `[VERIFY_VALUE:UPDATE_DATE]` |
| Plans created | `[VERIFY_VALUE:PLANS_CREATED]` | `[VERIFY_SOURCE:PLANS_CREATED]` | `[VERIFY_VALUE:PLANS_CONF]` | `[VERIFY_VALUE:UPDATE_DATE]` |
| D7 return rate | `[VERIFY_VALUE:D7_RATE]` | `[VERIFY_SOURCE:D7_RATE]` | `[VERIFY_VALUE:D7_CONF]` | `[VERIFY_VALUE:UPDATE_DATE]` |
| Trial start rate | `[VERIFY_VALUE:TRIAL_RATE]` | `[VERIFY_SOURCE:TRIAL_RATE]` | `[VERIFY_VALUE:TRIAL_CONF]` | `[VERIFY_VALUE:UPDATE_DATE]` |

## 2) Demo Assets Checklist

- [ ] Web screenshots (real product, no mock).
- [ ] iOS screenshots (real product, no mock).
- [ ] 1 short demo GIF for onboarding-to-action flow.
- [ ] 1 short demo GIF for weekly continuity flow.
- [ ] Caption template with wellness-safe wording.

## 3) Mini Case Study Template

### Case Card

- ICP: `[VERIFY_VALUE:CASE_ICP]`
- Starting problem: `[VERIFY_VALUE:CASE_BEFORE]`
- Pilot setup: `[VERIFY_VALUE:CASE_SETUP]`
- Observed change: `[VERIFY_VALUE:CASE_AFTER]`
- Why it happened (hypothesis): `[VERIFY_VALUE:CASE_CAUSE]`
- What scales next: `[VERIFY_VALUE:CASE_NEXT]`

## 4) Technical Credibility Signals

| Signal | Value | Source |
|---|---|---|
| Coverage gate | `[VERIFY_VALUE:COVERAGE]` | `[VERIFY_SOURCE:COVERAGE]` |
| CI pass rate | `[VERIFY_VALUE:CI_PASS_RATE]` | `[VERIFY_SOURCE:CI]` |
| Release stability | `[VERIFY_VALUE:RELEASE_STABILITY]` | `[VERIFY_SOURCE:RELEASE]` |
| Security controls | quota/rate/auth guardrails | `app/security/*`, policy docs |

## 5) External Use Rules

1. Нет source -> не выносить в one-pager/pitch deck.
2. Demo assets должны быть из актуальной версии продукта.
3. Case study публикуется после owner approval и compliance check.

## Security Notes

- Удалять PII из скриншотов и case snippets.
- Использовать только wellness-safe wording.

## Marketing & GTM

- Proof Pack — основной мост между GTM гипотезой и доверительным продажным сигналом.
- Минимально обновлять раз в 2 недели в активной фазе роста.
