# Deployment Docs (Index)

Здесь живёт вся документация по деплою и прод-эксплуатации.

## Start here

1. `DEPLOYMENT.md` (repo root) — краткий обзор и ссылки
2. `RUNBOOK_AGENT.md` (repo root) — triage/CI/debug playbook
3. `docs/deploy/*` — подробные гайды

## Guides

- `OVERVIEW.md` — общая схема окружений, домены, секреты (без секретов в репо)
- `PRODUCTION.md` — production setup и конфигурация
- `DIGITALOCEAN.md` — provisioning и инфраструктура (droplet, firewall, volumes)
- `DOCKER.md` — docker compose / сервисы / команды / best practices
- `SOLO.md` — solo deployment setup (single-server deployment)
- `READING_LIST.md` — список документации для изучения

## Where things live

- `deploy/` — конфиги/скрипты (infra-as-code)
- `docs/deploy/` — инструкции/рукбуки (человекочитаемые)

## Conventions

- Keep docs operational and actionable.
- Avoid including secrets. Use placeholder values.
- Prefer copy/paste-able commands.
