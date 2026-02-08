# Memory Capsule: OpenAPI determinism + side‑effect‑free generation

**Topic:** Deterministic OpenAPI artifacts for frontend types
**Type:** Invariant + commands
**Last updated:** 8 February 2026

---

## What

OpenAPI generation is **determinism-gated** and must be **side-effect-free** on the import path.
This protects CI and prevents accidental ORM/model side effects when generating schema.

---

## Why

If OpenAPI generation drifts or triggers side effects:

- frontend generated types (`schema.ts`) drift unpredictably
- CI fails on OpenAPI sync/determinism checks
- imports may trigger ORM table registration (breaking “schema-only” assumptions)

---

## Invariants (SoT)

- Canonical section header: `AGENTS.md:668`
- Must use `make openapi` (not direct script): `AGENTS.md:675`
- Side-effect free requirement wording: `AGENTS.md:682`
- Determinism test gate: `AGENTS.md:688`
- Update flow (artifacts to commit): `AGENTS.md:703`, `AGENTS.md:706`, `AGENTS.md:707`, `AGENTS.md:709`

---

## Commands (local workflow)

- Generate OpenAPI + regenerate frontend artifacts:

```bash
make openapi
```

- Verify artifacts are in sync:

```bash
make openapi-check
```

- Run determinism test directly (debug):

```bash
pytest -q tests/test_openapi_determinism.py
```

---

## Links (canonical artifacts)

- Generated artifacts: `frontend/src/api/openapi.json`, `frontend/src/api/schema.ts`
- Generator entrypoint: `scripts/generate_openapi.py` (invoked via `make openapi`)
