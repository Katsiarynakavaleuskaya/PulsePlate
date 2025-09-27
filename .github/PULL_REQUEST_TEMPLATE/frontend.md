---
name: Frontend Feature
about: Web / SPA changes
title: "feat(frontend): "
labels: [frontend, feat]
---

## Summary
- Что меняем и зачем (ссылка на задачу).

## Scope
- Основные экраны/компоненты.
- Что осталось вне PR (коротко).

## Frontend Notes
- Маршруты / состояния / API вызовы.
- Доступность: `role`, `aria-*`, контраст ≥4.5:1.
- MSW / fallback (если затрагивали сеть).

## Testing
- [ ] `npm run lint`
- [ ] `npm test`
- [ ] `npm run build`
- Ручное тестирование / скриншоты (ниже).

```bash
cd frontend
cp .env.example .env   # если нужен VITE_API_BASE
npm ci
npm run dev
```

<details>
<summary>Assets / screenshots</summary>

_Вставь актуальные скрины/видео UI._

</details>
