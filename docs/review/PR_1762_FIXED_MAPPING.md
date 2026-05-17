# PR #1762 - Fixed in Commit Mapping

**PR:** feat(orchestration): add Qoder dispatch bridge for auto-dispatching role agents
**Branch:** `codex/orchestration-qoder-dispatch-bridge`

## Discussion Thread Pass

All blocking bot review findings addressed with code fixes.

## Fixed in Commit Mapping

### FIXED

- Sourcery: slug vs name resolution in `resolve_qoder_type()` - prefers `slug` over `name` -> e1929c405
- Sourcery: preflight success message prints unconditionally when spec is None -> e1929c405
- Sourcery: documentation path mismatch `.github/agents/` to `.cursor/agents/` -> e1929c405
- Sourcery: `frontend-engineer` unreachable code in type mapping -> ffab3c2eb
- CodeRabbit: `sys.path.insert` violates import hygiene guard -> e1929c405
- CodeRabbit: non-deterministic glob ordering in test -> e1929c405
- CodeRabbit: type annotations for test functions -> 11944728f
- Cubic: slug vs name resolution (same as Sourcery) -> e1929c405
- Cubic: `frontend-engineer` unreachable (same as Sourcery) -> ffab3c2eb
- Cubic: documentation path mismatch (same as Sourcery) -> e1929c405
- Cubic: parallelizable_groups bracket syntax parsing -> 11944728f
- Codex: mode=review support in CLI and type resolver -> 11944728f
- Codex: fenced code extraction from packet (skip code blocks) -> 11944728f
- Codex: coordinator de-dup logic (preserve intentional repeats) -> 11944728f
- Codex: post-open QA chain always included in manifest -> 11944728f
- Codex: readonly derivation from Qoder type mapping -> 11944728f
- Codex: reviewer slot auto-detection (name-based) -> 11944728f

### NOT-A-BUG

- PM-1: Routing graph loader silent fallback - intentional design for optional dependency
- PM-2: YAML frontmatter edge cases - manual fallback acceptable for internal tooling
- PM-3: Skill auto-discovery - `_SKILL_MAP` is a static recommendation heuristic
