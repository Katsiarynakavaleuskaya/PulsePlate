# Docs-only PR Policy

**Status:** Mandatory
**Scope:** All repositories and subprojects
**Applies to:** All contributors, agents, CI reviewers

---

## 1. Definition

**Docs-only PR** — это pull request, цель которого **исключительно**:

* структурирование документации,
* исправление ссылок,
* обновление README / AGENTS / RUNBOOK,
* добавление policy / reports / specs в формате Markdown.

Docs-only PR **НЕ ИМЕЕТ ПРАВА** изменять код, CI, инфраструктуру или поведение приложения.

---

## 2. Allowed changes (docs-only)

Разрешены **только** следующие файлы:

* `*.md`
* `README.md`
* `AGENTS.md`
* `RUNBOOK_AGENT.md`
* `DEPLOYMENT.md`
* `.github/*.md` (issue / PR templates, instructions)

> Примечание: перемещения файлов (`git mv`) допустимы **только** для Markdown-документов.

---

## 3. ❌ Forbidden changes (strict)

В docs-only PR **строго запрещены** любые изменения:

### Source code

* `*.py`, `*.js`, `*.ts`, `*.swift`, `*.sql`, etc.

### CI / Infra

* `*.yml`, `Dockerfile`, `Makefile`, `requirements*`

### Runtime configuration

* Imports, shims, adapters, compat layers

### Any behavior changes

**Любые изменения поведения**, даже если они выглядят как:

* "cleanup"
* "revert"
* "formatting"
* "temporary fix"

### Explicitly forbidden

* `legacy_app.py`
* `app/*`
* `core/*`
* `tests/*`

> Даже если изменение "возвращает файл к main" — это **НЕ docs-only**.

---

## 4. Enforcement (mandatory before push)

Перед **каждым push** docs-only PR автор **обязан** выполнить:

```bash
git diff --name-only origin/main...HEAD \
  | rg -v "\.md$|README\.md$|AGENTS\.md$|RUNBOOK_AGENT\.md$|DEPLOYMENT\.md$"
```

### Expected result

* **Empty output**

### If output is NOT empty

* PR **must be stopped**
* All non-doc files **must be reverted to `origin/main`**
* A fixing commit like the following is required:

```bash
git checkout origin/main -- <file>
git add <file>
git commit -m "chore(docs): keep docs PR docs-only"
```

---

## 5. Separation of concerns (hard rule)

* **Docs PRs**: documentation governance only
* **Feature / Refactor PRs**: code, tests, runtime, CI

Mixing documentation restructuring with code changes:

* increases regression risk,
* breaks CI isolation,
* makes reviews unreliable,
* is considered a **policy violation**.

---

## 6. Rationale

This policy exists to ensure:

* clean and reviewable PRs,
* predictable CI behavior,
* no accidental regressions,
* strict separation between **documentation governance** and **runtime evolution**.

This is not a stylistic guideline — it is an **engineering safety rule**.

---

## 7. Relationship to AGENTS.md

* `AGENTS.md` **enforces** this rule at execution time (agents / contributors).
* This document is the **canonical policy source of truth**.
* In case of conflict, **this policy wins**.
