# Welcome Gate Copy Deck (RU/EN/ES) — `onboarding.welcome.*`

**Date:** 6 February 2026
**Scope:** Welcome Gate (PR-653) copy system + future-safe extensions
**Tone:** wellness-first, trust-first, **no medical claims**, short sentences (VoiceOver-friendly)

> Canonical key set for PR-653 is documented in `docs/audit/PR_653_P0_WELCOME_ONBOARDING_4SCREENS_AUDIT.md`.

---

## 0) How to use this deck

- **Variant A vs B** is meant for *client-side* A/B (TestFlight cohorts) without backend changes.
- Keep strings **short** (small screens + better a11y cadence).
- Avoid “diagnose / treat / cure / medical advice”.

---

## 1) Required keys (P0) — 2 variants each

### Screen 1

- `onboarding.welcome.screen1.title`
  - **EN A**: PulsePlate — your nutrition on track
  - **EN B**: PulsePlate — stay on track
  - **RU A**: PulsePlate — питание под контролем
  - **RU B**: PulsePlate — держим курс легко
  - **ES A**: PulsePlate — tu nutrición bajo control
  - **ES B**: PulsePlate — mantén el rumbo

- `onboarding.welcome.screen1.body`
  - **EN A**: Set your goals once. Your plan and progress stay aligned.
  - **EN B**: Simple setup now. Clear progress later.
  - **RU A**: Настрой цели один раз. План и прогресс будут согласованы.
  - **RU B**: Простая настройка сейчас — ясный прогресс потом.
  - **ES A**: Configura tus objetivos una vez. Plan y progreso en sintonía.
  - **ES B**: Configura hoy. Ve tu progreso mañana.

### Screen 2 (privacy / trust)

- `onboarding.welcome.screen2.title`
  - **EN A**: Private by default
  - **EN B**: Your data, your control
  - **RU A**: Приватность по умолчанию
  - **RU B**: Ваши данные — ваш контроль
  - **ES A**: Privado por defecto
  - **ES B**: Tus datos, tu control

- `onboarding.welcome.screen2.body`
  - **EN A**: Your inputs stay on your device unless you choose to export.
  - **EN B**: You decide what to share and when.
  - **RU A**: Данные остаются на устройстве, пока вы сами не экспортируете.
  - **RU B**: Вы решаете, чем делиться и когда.
  - **ES A**: Tus datos quedan en tu dispositivo hasta que decidas exportar.
  - **ES B**: Tú decides qué compartir y cuándo.

### Screen 3 (setup)

- `onboarding.welcome.screen3.title`
  - **EN A**: Pick your setup
  - **EN B**: Make it yours
  - **RU A**: Выберите настройки
  - **RU B**: Сделайте под себя
  - **ES A**: Elige tu configuración
  - **ES B**: Hazlo tuyo

- `onboarding.welcome.screen3.body`
  - **EN A**: Language, units, and goals — you can change this anytime.
  - **EN B**: Set your preferences now. Update them anytime.
  - **RU A**: Язык, единицы и цель можно изменить в любой момент.
  - **RU B**: Настройте сейчас. Измените когда угодно.
  - **ES A**: Idioma, unidades y objetivo: puedes cambiarlo cuando quieras.
  - **ES B**: Ajusta ahora. Cambia cuando quieras.

### Screen 4 (start)

- `onboarding.welcome.screen4.title`
  - **EN A**: Ready to start
  - **EN B**: Let’s begin
  - **RU A**: Можно начинать
  - **RU B**: Поехали
  - **ES A**: Listo para empezar
  - **ES B**: Empecemos

- `onboarding.welcome.screen4.body`
  - **EN A**: Build a simple plan you can follow today.
  - **EN B**: Start small. Stay consistent.
  - **RU A**: Соберём простой план, который реально выполнить уже сегодня.
  - **RU B**: Начните с малого. Держите ритм.
  - **ES A**: Hagamos un plan simple que puedas seguir hoy.
  - **ES B**: Empieza pequeño. Sé constante.

### CTAs

- `onboarding.welcome.cta.continue`
  - **EN A**: Continue
  - **EN B**: Next
  - **RU A**: Дальше
  - **RU B**: Далее
  - **ES A**: Continuar
  - **ES B**: Siguiente

- `onboarding.welcome.cta.back`
  - **EN A**: Back
  - **EN B**: Previous
  - **RU A**: Назад
  - **RU B**: Вернуться
  - **ES A**: Atrás
  - **ES B**: Volver

- `onboarding.welcome.cta.start`
  - **EN A**: Get started
  - **EN B**: Start now
  - **RU A**: Начать
  - **RU B**: Начать сейчас
  - **ES A**: Empezar
  - **ES B**: Empezar ahora

### Accessibility format

- `onboarding.welcome.stepA11y` (format string)
  - **EN A**: Step %d of %d
  - **EN B**: Screen %d of %d
  - **RU A**: Шаг %d из %d
  - **RU B**: Экран %d из %d
  - **ES A**: Paso %d de %d
  - **ES B**: Pantalla %d de %d

---

## 2) Optional extensions (future-safe keys)

These keys are optional; add them only when the UI truly needs them.

- `onboarding.welcome.disclaimer`
  - **EN**: For wellness purposes only. Not medical advice.
  - **RU**: Для велнес-целей. Не медицинский совет.
  - **ES**: Solo para bienestar. No es consejo médico.

- `onboarding.welcome.privacy.note`
  - **EN**: You can export anytime.
  - **RU**: Экспорт — когда захотите.
  - **ES**: Puedes exportar cuando quieras.
