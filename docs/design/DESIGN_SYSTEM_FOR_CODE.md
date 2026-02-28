# Design System — для написания кода

Краткий указатель: какие документы и артефакты использовать, когда дизайн нужно перенести в код.

**Если дизайнеру нужно что-то конкретное (токены, отступы, компоненты) — пусть уточнит, и можно прислать нужный кусок.**

---

## 1. Токены (цвета, отступы, радиус, тени) — код

**Источник правды в коде:** `frontend/src/styles/tokens.css`

- Бренд: `--pp-navy`, `--pp-blue`, `--pp-green`, `--pp-red`, `--pp-gold`
- Шкалы: `--color-navy-50` … `--color-navy-900`, аналогично blue/green/heart/gray
- Семантика: `--color-background`, `--color-text`, `--color-muted`, `--radius-*`, `--shadow-*`

**Правила:** `docs/design/TOKENS_SOT.md` — какие токены каноничные, что нельзя использовать (сырой hex в рантайме).

---

## 2. Визуальные правила (премиум-вид, контраст, типографика)

**Документ:** `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`

- Палитра, настроение (minimalism, cozy, luxury-clean)
- Ссылки на Apple HIG, web.dev (контраст, motion)
- Когда какой стиль применять

**Чеклист перед ревью:** `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`

---

## 3. Компоненты (кнопки, инпуты, карточки)

**Что уже есть в коде:** `frontend/src/components/ui/` (Button, Input, NumberInput, Card и др.)

**Аудит «что добавить»:** `docs/audit/FRONTEND_MODERN_COMPONENTS_AUDIT.md`
**Быстрый старт по компонентам:** `docs/audit/FRONTEND_COMPONENTS_QUICK_START.md`
**Сравнение с Component Gallery:** `docs/audit/DESIGN_SYSTEM_COMPONENT_GALLERY_AUDIT.md`

Кнопки (варианты и состояния): `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`, CTA реестр — в полной спецификации Figma/Figr (12 разделов).

---

## 4. Полная спецификация (Figma/Figr)

Визуальная спецификация на 12 разделов (бренд, цвета, типографика, спейсинг, компоненты, экраны, CTA, a11y, брейкпоинты) — в артефакте Figr, который ты передавал.
Для кода в первую очередь берём **токены из `tokens.css`** и **правила из `TOKENS_SOT.md`** и **Visual Guidelines**; остальное — как справочник по макетам и состояниям.

---

## Что кому отправлять

| Запрос дизайнера | Что дать |
|------------------|----------|
| «Нужна дизайн-система под код» | Этот файл + путь к `frontend/src/styles/tokens.css` (или выдержку из него) |
| «Цвета/отступы для вёрстки» | `tokens.css` + `TOKENS_SOT.md` |
| «Правила по виду и контрасту» | `PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md` |
| «Какие компоненты есть / чего не хватает» | `FRONTEND_MODERN_COMPONENTS_AUDIT.md` или `FRONTEND_COMPONENTS_QUICK_START.md` |
| «Полная спецификация» | Ссылка на артефакт Figr + при необходимости выдержки из пунктов 1–3 выше |

Если дизайнер уточнит задачу (токены, компоненты, экраны, стиль), по этому указателю можно сразу выбрать нужный документ или кусок кода.
