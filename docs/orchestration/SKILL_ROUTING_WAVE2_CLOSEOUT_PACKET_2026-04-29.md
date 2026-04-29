# Skill Routing Wave 2 Closeout Packet - 2026-04-29

## Summary

This packet is the Skill routing wave 2 reconciliation closeout and marks the
ledger item for closure upon merge of PR #1570.
The implementation already exists on `main`: deterministic routing exposes a
stable explanation schema, semantic lexeme groups, approved research-only
connectors, and blocked low-fit scraping patterns.

This PR does not add skill files, product RAG, runtime scraping, hidden memory,
or a new orchestration authority layer.

## Coordinator Start

- Primary agent: `agent-coordinator`
- Branch: `codex/skill-routing-wave2-closeout`
- Worktree: `worktrees/skill-routing-wave2-closeout`
- Task packet: `artifacts/orchestration/task_packets/8ae767a14fb8.json`
- Pre-edit gates:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`

## Role Order

1. `agent-coordinator` - scope lock, ledger disposition, synthesis, DoD.
2. `architecture-specialist` - confirms this is router/docs reconciliation only.
3. `security-auditor` - confirms no runtime scraping, token use, or plugin hard dependency.
4. `qa-engineer-agent` - owns focused deterministic validation.
5. `bug-hunter` - checks false-green risk and stale-evidence gaps.
6. `data-scientist-agent` - advisory on deterministic semantics and false-positive boundaries.

Mandatory post-open lane remains `qa-engineer-agent -> bug-hunter`.

## Skills And Plugins

Required custom skills:

- `pulseplate-workflow`
- `pulseplate-ledger`
- `pulseplate-gates`
- `pulseplate-guards`
- `pulseplate-pr-review`

Additive routed skills from coordinator bootstrap:

- `docs-sync`
- `agents-md`
- `bug-triage`
- `code-review-expert`
- `security-best-practices`
- `security-threat-model`
- `pulseplate-ai-reports`

Plugin roles are governance-only in this PR:

- GitHub: PR metadata, current-head checks, and review governance.
- CodeRabbit/Sourcery/Cubic: advisory comments only when available.
- Browser Use, Computer Use, Hugging Face, Life Science Research, Expo, Figma,
  and Sentry: not runtime dependencies for this closeout.

## Evidence

- Semantic lexeme groups and approved connector catalog:
  `scripts/orchestration/skill_router.py:231` and
  `scripts/orchestration/skill_router.py:288`.
- Research connector policy builder:
  `scripts/orchestration/skill_router.py:594`.
- Blocked scraping metadata:
  `scripts/orchestration/skill_router.py:629`.
- Explanation schema:
  `scripts/orchestration/skill_router.py:695`.
- Bootstrap packet propagation:
  `scripts/orchestration/task_bootstrap.py:786` and
  `scripts/orchestration/task_bootstrap.py:922`.
- Deterministic tests:
  `tests/test_skill_router.py:1442`,
  `tests/test_skill_router.py:1510`,
  `tests/test_skill_router.py:1557`,
  `tests/test_task_bootstrap.py:163`.

## Boundaries

- No product endpoint, product RAG, vector DB, semantic cache, GraphRAG, or
  hidden memory behavior is introduced.
- No broad scraping or external data collection is added.
- `recommended_skills` remains additive packet metadata and does not become
  execution authority.
- `RAG for agent context` and Karpathy advisory wiki work remain separate
  follow-ups.

## Validation Plan

- `python3 -m pytest tests/test_skill_router.py tests/test_task_bootstrap.py -q`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/check_preflight.py`
- `pre-commit run --all-files`
- `make validate-min`

Full local `make verify` is deferred for this coordinator-owned docs/tooling
closeout unless scope expands; GitHub current-head CI remains the heavy signal.
