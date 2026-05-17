# PR #1762 — Fixed in Commit Mapping

**PR:** feat(orchestration): add Qoder dispatch bridge for auto-dispatching role agents
**Branch:** `codex/orchestration-qoder-dispatch-bridge`

## Discussion Thread Pass

All blocking bot review findings addressed. Deferred items tracked in BACKLOG_LEDGER.md.

## Fixed in Commit Mapping

### FIXED

- Sourcery: slug vs name resolution in `resolve_qoder_type()` — prefers `slug` over `name` -> e1929c405
- Sourcery: preflight success message prints unconditionally when spec is None -> e1929c405
- Sourcery: documentation path mismatch `.github/agents/` to `.cursor/agents/` -> e1929c405
- Sourcery: `frontend-engineer` unreachable code in type mapping -> ffab3c2eb
- CodeRabbit: `sys.path.insert` violates import hygiene guard -> e1929c405
- CodeRabbit: non-deterministic glob ordering in test -> e1929c405
- Cubic: slug vs name resolution (same as Sourcery) -> e1929c405
- Cubic: `frontend-engineer` unreachable (same as Sourcery) -> ffab3c2eb
- Cubic: documentation path mismatch (same as Sourcery) -> e1929c405

### DEFERRED

- CodeRabbit: type annotations for internal functions — docs/roadmap/BACKLOG_LEDGER.md
- Cubic: parallelizable_groups heuristic improvements — docs/roadmap/BACKLOG_LEDGER.md
- Codex QA: full QA pass skipped (pilot scope) — docs/roadmap/BACKLOG_LEDGER.md
- Codex: readonly derivation from frontmatter — docs/roadmap/BACKLOG_LEDGER.md
- Codex: fenced code extraction from packet — docs/roadmap/BACKLOG_LEDGER.md
- Codex: reviewer slot auto-detection — docs/roadmap/BACKLOG_LEDGER.md
- Codex: mode=review support — docs/roadmap/BACKLOG_LEDGER.md
- Codex: coordinator de-dup logic — docs/roadmap/BACKLOG_LEDGER.md
- Codex: post-open chain notation parsing — docs/roadmap/BACKLOG_LEDGER.md

### NOT-A-BUG

- PM-1: Routing graph loader silent fallback — intentional design for optional dependency
- PM-2: YAML frontmatter edge cases — manual fallback acceptable for internal tooling
- PM-3: Skill auto-discovery — `_SKILL_MAP` is a static recommendation heuristic
