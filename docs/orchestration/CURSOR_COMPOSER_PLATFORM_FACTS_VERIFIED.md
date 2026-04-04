# Cursor / Composer / local agent — verified + pending verification

Статус документа: часть пунктов подтверждена официальными источниками, а элементы с пометкой `[VERIFY]` остаются открытыми до ручной цитаты из Cursor Docs.

Этот файл является reference/evidence note, а не канонической policy-спецификацией репозитория.
Пока в документе остаются элементы `[VERIFY]`, он не должен использоваться как обязательный источник для always-on bootstrap rules.

**Назначение:** заменить маркеры `[VERIFY]` в опроснике по локальной агентной среде PulsePlate там, где есть **официальный текст**, доступный без авторизации.

**Ограничение среды:** запросы к `https://docs.cursor.com/...` и `https://cursor.com/help/...` из агентного окружения часто возвращают только оболочку SPA (почти пустое тело). Для страниц из раздела Docs без полного текста ниже указаны **канонические URL** и статус **«требует цитаты из Simple Browser»** — скопируйте абзац из открытой у вас документации.

**Основной источник с полным текстом (подтверждён fetch):**

- [Best practices for coding with agents · Cursor](https://www.cursor.com/blog/agent-best-practices) (официальный блог Cursor)

**Связанный архитектурный пакет (репо):** [PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md](./PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md) — CAID-style оркестрация, две дорожки (delivery / workforce platform), память и rollout.

**Rollout note (workforce track, репо):** [COMPOSER_BOOTSTRAP_KIT_PR1.md](./COMPOSER_BOOTSTRAP_KIT_PR1.md) — decomposition note для будущих bootstrap slices и follow-on PR.

---

## §1 Подтверждённые факты платформы

| Тема | Утверждение (сжато) | Источник |
|------|---------------------|----------|
| **Agent harness** | Агент строится из трёх частей: инструкции (system prompt + rules), инструменты (редактирование, поиск, терминал и т.д.), модель. | [Blog: Understanding agent harnesses](https://www.cursor.com/blog/agent-best-practices) |
| **Plan Mode** | `Shift+Tab` в поле ввода агента переключает Plan Mode: исследование кодовой базы, уточняющие вопросы, план с путями файлов и ссылками на код, **ожидание одобрения** перед реализацией. План можно сохранить в **`.cursor/plans/`** («Save to workspace»). | Там же, раздел «Using Plan Mode» |
| **Правила (Rules)** | Статичный контекст: markdown-файлы в **`.cursor/rules/`**, «always-on» в начале разговора; команды сборки/стиль/воркфлоу; не копировать целые гайды — ссылаться на файлы в репо. | Там же, «Rules: Static context for your project» |
| **Skills** | Динамические возможности: **`SKILL.md`**, кастомные команды через **`/`**, hooks, доменные инструкции; подключаются **когда агент решает, что релевантно** (в отличие от Rules). Ссылка на доки: `https://cursor.com/docs/context/skills`. Указание: **Agent Skills доступны в канале Nightly** (Settings → Beta → Nightly). | Там же, «Skills» + примечание про Nightly |
| **Hooks** | Пример: `.cursor/hooks.json` с событием `stop` и скриптом; ссылка на партнёрские интеграции: `https://cursor.com/docs/agent/hooks`. | Там же, «Example: Long-running agent loop» |
| **MCP** | Подключение внешних инструментов через **Model Context Protocol**; вход с маркетплейса: `https://cursor.com/marketplace`. | Там же, «Extending the agent» (абзац про MCP) |
| **Браузер** | Агент может работать с браузером (скриншоты, проверка UI). Док: `https://cursor.com/docs/agent/browser`. | Там же, «Including images» / browser |
| **Контекст и чаты** | Не обязательно тегать все файлы — агент использует поиск; **`@Past Chats`** для ссылки на прошлые диалоги. **`@Branch`** для контекста ветки. | Там же, «Managing context» |
| **Команды `/`** | Переиспользуемые сценарии в **`.cursor/commands/`** (markdown), вызов через `/` во вводе агента. | Там же, «Git workflows» / commands |
| **Параллельные агенты** | Нативная поддержка **git worktrees**; док: `https://www.cursor.com/docs/configuration/worktrees`. Несколько моделей из dropdown, сравнение результатов. | Там же, «Running agents in parallel» |
| **Облачные агенты** | Запуск с `https://cursor.com/agents`, из редактора или телефона; **удалённая песочница**; клон репозитория, ветка, автономная работа, **PR по завершении**; уведомления (Slack, email, web); триггер из Slack: **@Cursor** — `https://cursor.com/docs/integrations/slack`. | Там же, «Delegating to cloud agents» |
| **Ревью** | Во время работы — diff, Stop; после — **Review → Find Issues**; для локальных изменений — Agent Review относительно main; **Bugbot** на PR: `https://cursor.com/docs/bugbot`. | Там же, «Reviewing code» |
| **Debug Mode** | Гипотезы, инструментирование логами, воспроизведение, анализ поведения, точечные фиксы (описание режима в блоге). | Там же, «Debug Mode for tricky bugs» |

### Страницы Docs (URL зафиксированы в блоге; полный текст — у пользователя в браузере)

| URL | Для опросника |
|-----|----------------|
| `https://cursor.com/docs/context/skills` | Skills: формат, когда подгружаются |
| `https://cursor.com/docs/agent/hooks` | Hooks: события, безопасность запуска скриптов |
| `https://cursor.com/docs/agent/browser` | Browser tool: границы, приватность |
| `https://www.cursor.com/docs/configuration/worktrees` | Worktrees и изоляция агентов |
| `https://cursor.com/docs/bugbot` | Авторевью PR |
| `https://cursor.com/docs/integrations/slack` | Облако + Slack |

**Project Rules (иерархия `.mdc`, Team Rules, User Rules):** в блоге акцент на `.cursor/rules/` как markdown. Детальная иерархия — на странице Rules в Docs; типичные ссылки из поиска: `https://docs.cursor.com/en/context/rules`, `https://cursor.com/help/customization/rules` — **проверить и процитировать из вашего Simple Browser**.

---

## §2 Жёсткие ограничения (для PulsePlate)

- **Облачные агенты:** код и история обработки выполняются в **удалённой песочнице** Cursor — не считать это полностью «только локально» для секретов и PII.
- **Skills / Nightly:** часть возможностей Skills помечена как **Nightly** — в прод-процессах фиксировать канал обновления.
- **Hooks:** произвольные команды при остановке агента — зона **supply-chain / локального исполнения**; политика репозитория должна ограничивать содержимое `.cursor/hooks.json` и скриптов.

---

## §3 Что сделать вам (если открыт Simple Browser)

1. Открыть `https://docs.cursor.com/en/context/rules` (или актуальный раздел Rules из оглавления).
2. Скопировать **1–2 предложения** про типы правил (Always / Auto / Agent / Manual) и про **Team vs Project vs User** — вставить в чат или в конец этого файла.
3. Аналогично для **MCP**: раздел про одобрение инструментов и auto-run (если есть).

После этого строки таблицы можно пометить **Confirmed** вместо `[VERIFY]`.

---

## Decision log

| Дата | Действие |
|------|----------|
| 2026-04-04 | Зафиксированы факты по официальному блогу; Docs-страницы перечислены по ссылкам из блога; fetch HTML Docs в агентной среде не дал тела страницы. |
| 2026-04-04 | Добавлены блоки A–I опросника, таблицы §1–§7, Ollama (api.md + docs.ollama.com/openai), MCP transports по спецификации 2025-06-18. |

---

## Опросник A–I — сводка (Cursor / MCP / Ollama / PulsePlate)

**Легенда:** без пометки — есть официальный источник (ниже URL). **`[VERIFY]`** — нужна цитата из `cursor.com/docs` / настроек продукта в вашем браузере.

### Блок A — Rules / orchestration foundation

| Вопрос | Ответ (кратко) | Источник |
|--------|----------------|----------|
| Типы правил: Project / User / AGENTS.md / `.cursorrules` | **Подтверждено для репо:** статичные правила как markdown в **`.cursor/rules/`**, always-on в начале разговора; коммитить в git. **User Rules** — в настройках Cursor (глобально для пользователя; не в этом fetch). **AGENTS.md** и **`.cursorrules`** — в продукте используются сообществом и шаблонами; **точная матрица «чем отличаются» и статус legacy для `.cursorrules`** — **`[VERIFY]`** на странице Rules в Docs. | [Blog: Rules](https://www.cursor.com/blog/agent-best-practices); см. также [Rules \| Cursor Docs](https://cursor.com/docs/context/rules) (в fetch — только заголовок SPA) |
| Scoped rules / globs | **`[VERIFY]`** — уточнить в Docs (часто: `.mdc` + метаданные / glob для области применения). В блоге явно только папка `.cursor/rules/`. | Docs Rules |
| Version-control rules с репо | **Да, рекомендуется:** правила в репозитории, не раздувать; ссылаться на файлы проекта. | [Blog](https://www.cursor.com/blog/agent-best-practices) |
| Ограничения AGENTS.md vs `.cursor/rules` | **Концептуально:** Rules — провайдеры статического контекста в Cursor; **AGENTS.md** в экосистеме часто — соглашения для агентов/монорепо (как в данном репо). **Официальные ограничения Cursor** — **`[VERIFY]`**. | Repo `AGENTS.md`; Docs |
| Nested AGENTS.md | **`[VERIFY]`** — только корень vs вложенные скоупы (в форуме встречаются оба поведения; не норма для «официально»). | Docs / практика |

### Блок B — Modes (Agent / Ask / Manual / Custom)

| Вопрос | Ответ | Источник |
|--------|--------|----------|
| Какие режимы и что умеют | **Plan Mode** в агенте: `Shift+Tab` — исследование, вопросы, план, **одобрение до реализации**; сохранение в `.cursor/plans/`. **Debug Mode** — описан в блоге (гипотезы, логи, воспроизведение). Полная матрица **Agent / Ask / Manual / Custom** (имена в UI), отдельная модель, набор инструментов, read-only — **`[VERIFY]`** в Docs Chat / Custom Modes. | [Blog](https://www.cursor.com/blog/agent-best-practices) |
| Custom mode: модель, tools, instructions, security-only | **`[VERIFY]`** | Docs |
| Роли (Security, Deploy, …) как отдельные custom modes | **Да как практика** (пресеты инструкций); границы безопасности = политика репо + одобрение инструментов, не «магия» режима — **`[VERIFY]`** детали guardrails в Docs. | Архитектура + Docs |

### Блок C — MCP / tool layer

| Вопрос | Ответ | Источник |
|--------|--------|----------|
| Transport modes | **По спецификации MCP 2025-06-18:** стандартные транспорты — **stdio** и **Streamable HTTP**; **HTTP+SSE** — устаревший транспорт (2024-11-05), совместимость описана в spec. **Какой набор включён в конкретной сборке Cursor** — **`[VERIFY]`** в Cursor MCP docs. | [MCP Transports 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports) |
| Локальные MCP-серверы на машине | **Да, по смыслу stdio:** клиент запускает сервер как подпроцесс (spec). Практически — прописать команду в конфиге MCP Cursor. | MCP spec stdio |
| MCP для GitHub / FS / shell / browser / metrics / scanners / логи | **Возможно через соответствующие MCP-серверы** (маркетплейс и кастом). Ограничения и одобрение — политика Cursor + ваш конфиг. Блог: расширение агента через MCP; browser: `cursor.com/docs/agent/browser`. | [Blog MCP](https://www.cursor.com/blog/agent-best-practices); [Browser docs URL в блоге](https://cursor.com/docs/agent/browser) |
| Tool approval / auto-run / общий config с CLI | **`[VERIFY]`** | Cursor Docs MCP |

### Блок D — Memory

| Вопрос | Ответ | Источник |
|--------|--------|----------|
| Как создаются Memories; scope; approval; long-lived orchestration | **`[VERIFY]`** — в агентном fetch не получен полный текст страницы Memories. | Cursor Docs |
| Как «основная память» операционной системы | **Не рекомендуется** полагаться только на Memories для долгоживущей оркестрации: SoT = репо (ledger, runbooks, ADR) + при необходимости внешнее хранилище/вектор. | Архитектура PulsePlate |

### Блок E — Background / Cloud agents

| Вопрос | Ответ | Источник |
|--------|--------|----------|
| Локальные vs удалённые; интернет; retention | **Облачные агенты:** удалённая **песочница**, клон репо, ветка, PR, уведомления. **Интернет и хранение** в песочнице Cursor — **`[VERIFY]`** детали политики/retention в Docs/ToS. Для **privacy-sensitive local-first** облачные агенты **не** считать эквивалентом «только локально». | [Blog: Cloud agents](https://www.cursor.com/blog/agent-best-practices) |

### Блок F — Ollama (подтверждено документацией)

| Вопрос | Ответ | Источник |
|--------|--------|----------|
| Локальные API | **`POST /api/generate`**, **`POST /api/chat`**, **`POST /api/embed`** (и устаревший **`/api/embeddings`**), список моделей, pull/push, **`GET /api/ps`** (загруженные модели) и др. | [ollama/ollama docs/api.md](https://github.com/ollama/ollama/blob/main/docs/api.md) |
| Chat / generate / embeddings | Да | api.md |
| Structured outputs | В **native API**: `format: "json"` и **JSON schema** (для поддерживаемых моделей). | api.md |
| Tool calling | В **`/api/chat`**: поля **`tools`**, ответы с **`tool_calls`**, сообщения с `role: "tool"`. | api.md |
| OpenAI compatibility | **`http://localhost:11434/v1/`** — совместимость с **частью** OpenAI API: `/v1/chat/completions`, `/v1/completions`, `/v1/models`, `/v1/embeddings`, `/v1/responses`, экспериментально `/v1/images/generations`. Таблица поддерживаемых полей (в т.ч. **tools** частично, **`tool_choice`** помечен как не поддерживается в таблице) — на странице. | [docs.ollama.com/openai](https://docs.ollama.com/openai) |
| Stateful memory на стороне Ollama | **Нет как долговременной «памяти агента»:** в native API параметр **`context`** для `/api/generate` помечен **deprecated** (краткая конв. память через возвращаемый массив). **Память оркестрации** — у клиента: БД, файлы, RAG, session store. | api.md |
| `keep_alive` | Управляет, как долго модель остаётся в памяти после запроса; по умолчанию **`5m`**; **`keep_alive: 0`** — выгрузка при пустом промпте (см. доки generate/chat). | api.md |
| Держать модели прогретыми 24/7 | Технически можно увеличивать `keep_alive` и периодически пинговать; **ограничения** — RAM/VRAM, стабильность, энергопотребление; не «гарантия сервиса», а эксплуатация. | api.md + ops |
| Context size | В **Modelfile**: **`PARAMETER num_ctx`** (в таблице параметров указан пример **2048** как значение по умолчанию в описании параметра; в примерах встречается **4096**). Верхняя граница зависит от модели и железа. | [ollama modelfile docs](https://github.com/ollama/ollama/blob/main/docs/modelfile.mdx) |

### Блок G — Local workforce (рекомендации, не гарантии Cursor)

| Роль | Лучше всего | Почему |
|------|-------------|--------|
| Director / координация | Custom mode + **Plan** + правила репо | План и одобрение до массовых правок |
| Memory Librarian | **Human + ledger в репо** (+ опционально скрипты/MCP) | SoT и аудит изменений |
| Bug Hunter | Agent + тесты/CI + Debug mode | Нужны воспроизведение и доказательства |
| Security Analyst | **HITL** + SAST/Deps в CI; MCP для сканеров опционально | Риск автоприменения «фиксов» |
| Deploy/SRE | HITL для prod; cron/GitHub Actions для рутины | Секреты и blast radius |
| Backend/Frontend/iOS/QA | Agent modes + scoped rules + MCP (API, docs) | Согласовать с thin-client политикой PulsePlate |
| **Нельзя безопасно full-auto** | Security (prod), Deploy (prod), юридически значимые решения, доступ к секретам | Всегда человек в контуре |

### Блок H — PulsePlate: память и RAG

| Слой | Где хранить | Заметка |
|------|-------------|---------|
| Canonical SoT | Репо: `docs/`, контракты, **backlog ledger**, OpenAPI | Версионируется, ревью |
| Working memory | Ветка, `.cursor/plans/`, черновики PR | Временно |
| Advisory | AGENTS.md, skills, rules | Наводит агента |
| Stale / historical | Git history, `event log` при необходимости | Не смешивать с canonical без меток |
| Минимальный RAG для staff | Начать без вектора: **жёсткая навигация** (AGENT_KNOWLEDGE_MAP, пакеты PR) + полнотекстовый поиск по репо; вектор — когда объём документов оправдывает затраты | PulsePlate docs/orchestration |
| Memory Steward как роль | **Опционально:** функция команды + правила обновления ledger, не обязательно отдельный «бот» с первого дня | |

### Блок I — Старт (практика)

| Горизонт | Состав |
|----------|--------|
| **1 неделя** | Правила `.cursor/rules/`, AGENTS.md scoped, Plan Mode по умолчанию для крупных задач, 1–2 MCP (например repo-specific), Ollama для локальных экспериментов **вне** прод-секретов |
| **1 месяц** | Ledger + runbooks для повторяемых потоков, шаблоны PR packets, CI для bug/security baseline, решение по cloud agents (если нужны) с политикой данных |
| **С чего начать** | **Стабильность:** bugs + CI → **security baseline** → deploy runbooks → затем business/growth как отдельные, не смешивая с каноном кода |
| **3 агента с макс. ROI первыми** | **Bug Hunter** (регрессии), **CI/Quality gate** (как «роль» + скрипты), **Coordinator/Director** (Plan + разбиение работ) — в терминах режимов и процесса, не обязательно три MCP |

---

## Таблицы §1–§7 (шаблон PulsePlate Local Agent Workforce Discovery)

### 1. Confirmed platform facts

| Topic | Answer | Doc URL | Practical implication |
|-------|--------|---------|----------------------|
| Rules in repo | Markdown в `.cursor/rules/`, static context | https://www.cursor.com/blog/agent-best-practices | Коммитить; не раздувать |
| Plan before build | Shift+Tab, approval, `.cursor/plans/` | https://www.cursor.com/blog/agent-best-practices | Подходит для Director workflow |
| MCP | Расширение инструментов | https://www.cursor.com/blog/agent-best-practices + MCP spec | Выбор серверов = attack surface |
| MCP transports (spec) | stdio + Streamable HTTP; legacy HTTP+SSE | https://modelcontextprotocol.io/specification/2025-06-18/basic/transports | Проектировать сервера под stdio или HTTP |
| Cloud agents | Remote sandbox, PR | https://www.cursor.com/blog/agent-best-practices | Не для секретов / строгого local-first без политики |
| Ollama native API | generate, chat, embed, ps, … | https://github.com/ollama/ollama/blob/main/docs/api.md | Локальные эксперименты |
| Ollama OpenAI shim | `/v1/*` subset | https://docs.ollama.com/openai | Подключение существующих клиентов |
| Ollama structured + tools | format/json schema; tools в `/api/chat` | api.md + docs.ollama.com/openai | Проверять поддержку моделью |
| Ollama keep_alive / num_ctx | `keep_alive` default 5m; `num_ctx` in Modelfile | api.md + modelfile.mdx | Планирование VRAM и «прогрева» |

*(Строки с `[VERIFY]` для User Rules, Memories, nested AGENTS.md, tool approval, Cursor↔CLI MCP — добавьте после копирования из Simple Browser.)*

### 2. Hard constraints

| Constraint | Source | Impact on PulsePlate |
|------------|--------|----------------------|
| Cloud sandbox | Blog | Не отправлять PII/секреты без классификации данных |
| Hooks arbitrary code | Blog + common sense | Ограничить `.cursor/hooks.json` в CODEOWNERS/ревью |
| Ollama not a secure enclave | Ops | Модель и хост — ваша ответственность |
| MCP servers | MCP spec security note (Streamable HTTP) | Локальные серверы: bind localhost, auth |

### 3. Recommended local-first architecture

| Layer | Choice | Why |
|-------|--------|-----|
| Instruction SoT | `.cursor/rules/` + nested `AGENTS.md` (если подтверждено Docs) | Повторяемость |
| Planning | Plan Mode + `.cursor/plans/` | Снижение дорогих ошибок |
| Execution | Local agent + optional Ollama | Данные на машине |
| Integrations | MCP stdio к доверенным серверам | Меньше exposure чем случайный HTTP |
| Long memory | Git + orchestration ledger | Аудит и merge |

### 4. Recommended first 5 agents (роли)

| Agent | Mission | Mode | Tools | Human approval? |
|-------|---------|------|-------|-----------------|
| Coordinator | Декомпозиция, план, гейты | Plan + Agent | Read/search, plan file | Да на merge |
| Bug Hunter | Регрессии, минимальные фиксы | Agent + Debug | Tests, terminal | Да если затрагивает security |
| CI Guardian | Линты, типы, детерминизм | Scheduled CI + Agent при падении | CI logs MCP опц. | Нет на PR из форка — политика |
| Security Triage | Dependency/SAST отчёты | Ask + чеклисты | Scanner MCP опц. | Да на исключения |
| Docs/Ledger Clerk | Актуализация ledger и пакетов | Agent ограниченный | Git | Да (контент) |

### 5. Memory architecture

| Memory type | Storage | Owner | Update path |
|-------------|---------|-------|-------------|
| Canonical | `docs/orchestration/*`, contracts | Team | PR review |
| Working | Branch, plans | Dev | Daily |
| Tool/assistant | Cursor Memories | **[VERIFY] scope** | User |
| Retrieval | Optional vector store | Platform | ETL job |

### 6. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Cloud agent data exposure | High | Политика; local-only для чувствительного |
| MCP over-permission | High | Минимальные scopes; одобрение вызовов |
| Ollama resource exhaustion | Medium | Лимиты concurrency, keep_alive |
| Rules drift | Medium | Ревью AGENTS.md / rules с фичами |

### 7. Proposed Phase 0 build order

1. Зафиксировать **Plan Mode** и **правила** репо; запретить облачные агенты для секретов до политики.
2. Включить **CI gate** минимум (lint/type/tests) и роль «Bug Hunter» как процесс.
3. Один **stdio MCP** (например внутренний скрипт) + **Ollama** для офлайн-экспериментов; затем расширение.

---

## Как закрыть оставшиеся `[VERIFY]`

Откройте в Simple Browser и вставьте в этот файл цитаты для:

1. `https://cursor.com/docs/context/rules` — типы правил, globs, `.cursorrules`, AGENTS.md.
2. Раздел **Chat modes / Custom modes** в Docs.
3. **MCP** — конфиг, approval, auto-run, совместимость с Cursor CLI.
4. **Memories** — создание, scope, global vs project.

После вставки удалите пометки `[VERIFY]` в таблицах §1 и блоке D.
