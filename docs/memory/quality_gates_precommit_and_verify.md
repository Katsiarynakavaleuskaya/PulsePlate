# Memory Capsule: Quality gates (`pre-commit` + `make verify`)

**Topic:** When we can say “ready” and how to avoid CI failures
**Type:** Hard gates + commands
**Last updated:** 8 February 2026

---

## What

PulsePlate has non-negotiable local gates for readiness claims:

- `make verify` is the canonical “all gates” command
- `pre-commit run --all-files` must run locally before push

---

## Why

These gates prevent:

- false-green PRs
- CI failures due to uncommitted hook fixes
- coverage drift below required thresholds

---

## Invariants (SoT)

- “Don’t claim green unless `make verify` passes”: `AGENTS.md:5`, `AGENTS.md:8`
- `pre-commit run --all-files` mandatory before push: `AGENTS.md:25`, `AGENTS.md:27`
- Coverage gate commands: `AGENTS.md:200`, `AGENTS.md:201`
- Coverage rule (only cov-check + diff-cov counts): `AGENTS.md:206`, `AGENTS.md:207`

---

## Commands (local)

```bash
pre-commit run --all-files
make verify
```

If you need to break it down:

```bash
make lint
make typecheck
make test-fast
make diff-cov
```

---

## Links (canonical)

- `AGENTS.md` → “Hard Gates (Non-negotiable)”
- `AGENTS.md` → coverage policy section
