# Update Instructions (Agents + Orchestration Surfaces)

**Status:** Canonical operating instructions
**Scope:** Agent registration + orchestration doc updates (docs-only changes)
**Last updated:** 8 February 2026 (PR #691)

---

## 1) Registration checklist (single path)

When adding or updating an agent, keep changes **explicit**, **evidence-driven**, and **SoT-safe**.

Update exactly these surfaces:

1. **Agent spec**: `.cursor/agents/<agent>.md`
2. **Agent index**: `docs/agents/index.md`
3. **Context map** (required reading): `docs/orchestration/AGENT_CONTEXT_MAP.md`
4. **Capability matrix** (routing guide): `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`

If any durable rule or workflow is introduced/changed:

- Add/adjust a canonical policy doc (single SoT), and link to it from the above surfaces.

---

## 2) Expected fields in agent specs (minimum)

Each `.cursor/agents/<agent>.md` must include:

- **Frontmatter**:
  - `name` (stable identifier)
  - `model` (usually `auto` unless explicitly justified)
  - `description` (1–2 lines, concrete)
- **Mission** (what outcomes the agent produces)
- **Hard boundaries** (what the agent must not do)
- **When invoked** (routing guidance)
- **Context to load** (SoT inputs, task-dependent)
- **Deliverable** (what returns to `agent-coordinator`)
- **Evidence contract**:
  - repo-policy claims must cite `file:line` (single-line anchors), and/or
  - reproducible commands + raw output + exit code

---

## 3) Operating rules (non-negotiable)

- **Final authority**: `agent-coordinator` synthesizes and finalizes.
- **Language policy**: RU-first; English terms may appear in parentheses or `code` on first mention.
- **No SoT drift**: do not duplicate canonical wording across multiple docs; prefer a single SoT doc + links.
- **Disclaimer SoT**: use the canonical wellness disclaimer only via:
  - `docs/safety/WELLNESS_DISCLAIMER_CANONICAL.md`

---

## 4) Rollout / permission notes

- Docs-only agent registration **does not** grant runtime permissions or change application behavior.
- Any runtime behavior change must land in a separate runtime PR with tests/guards and required quality gates.
