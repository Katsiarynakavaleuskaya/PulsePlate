# feat(frontend): <scope>

## Goal
Что даёт пользователю/разработчику. Ссылка на задачу.

## Files
Ключевые файлы/папки, в т.ч. стили/tokens, роутер, компоненты.

## Acceptance Criteria
- Роуты/состояния/видимость
- a11y: `role`, `aria-*`, контраст ≥4.5:1
- MSW-фоллбек (если API)

## Tests
- Vitest + @testing-library/react
- MSW: 500/timeout → фоллбек
- axe a11y проверки

## Run locally
```bash
cd frontend
cp .env.example .env # заполни VITE_API_BASE при необходимости
npm ci
npm run dev
```

## Security
- Нет секретов в репо
- Аналитика — только агрегаты

## Screenshots
(вставь)
