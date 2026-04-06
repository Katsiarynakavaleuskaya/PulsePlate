# ADR: METATRON-class offensive lab out-of-band (2026-04-06)

- Status: Accepted
- Owner: @katsiaryna_kavaleuskaya
- Related ledger item: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-metatron-offensive-lab-out-of-band`
- Related policy: `docs/security/METATRON_LAB_RULES_OF_ENGAGEMENT.md:1`
- Epic 1 task packet (coordinator roster + order): `docs/orchestration/METATRON_TRACK_A_EPIC1_TASK_PACKET_2026-04-06.md:1`

## Context

[METATRON](https://github.com/Katsiarynakavaleuskaya/metatron) and similar stacks combine
local LLMs with offensive reconnaissance tooling (e.g. port scans, web fingerprints) and
exploit-oriented analysis. PulsePlate is a wellness/nutrition product; its runtime
(`app.main:app`, OpenAPI surface, user clients) must not become a carrier for arbitrary
offensive automation or third-party target execution.

Defensive posture already lives in-repo (e.g. Trivy, pre-commit, guards). This ADR draws a
hard boundary for **offensive lab** work.

## Evidence

- Product entrypoint and coupling risk are centralized in `app/main.py:1` (bootstrap and
  route registration); METATRON-class tooling must not register routes here.
- AI guardrails for product insight surfaces live in `app/security/agent_input_guard.py:1`;
  they do not replace legal authorization for offensive testing.
- Local-only artifacts policy: `AGENTS.md` forbids committing `artifacts/` run outputs;
  lab outputs must follow the same rule via `artifacts/security_lab/` (see `.gitignore`).
- Deploy boundary stub documents isolation: `deploy/metatron-lab/docker-compose.yaml:1`.

## Decision

1. **Excluded from product layer:** No METATRON-class runner, offensive CLI orchestration,
   or lab database may ship inside the PulsePlate application image, `app/` routers,
   OpenAPI, iOS/Web clients, or user-authenticated API paths.
2. **Allowed lane:** Internal, authorized operators may run METATRON (or forks) **out of
   band** — separate clone/build, isolated network, subject to
   `docs/security/METATRON_LAB_RULES_OF_ENGAGEMENT.md`.
3. **Repository may contain** governance docs, runbooks, and **non-runtime** deploy stubs
   (e.g. isolated Compose network placeholders) that do **not** build the app image or
   add application dependencies for offensive tools.

## Consequences

- Positive: Clear legal/engineering boundary; reduced abuse and store-policy risk.
- Positive: Operators have a canonical place for RoE and orchestration (runbook).
- Negative: No “one click” METATRON inside the product; operators maintain a separate lab
  workspace or upstream compose.

## Exit criteria

This ADR is **closed** when governance artifacts are merged (ADR, RoE, ledger, runbook,
deploy stub, gitignore). Retire or amend only via a new ADR if product scope changes.
