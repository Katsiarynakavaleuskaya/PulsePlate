# Agent Learning Loop

The repo-governed agent learning loop converts repeated review failures into
redacted, deterministic proposals for future instruction or skill updates.

Shared helper: `scripts/orchestration/agent_learning_loop.py`.
Extractor CLI: `scripts/orchestration/agent_lesson_extractor.py`.
Promoter CLI: `scripts/orchestration/agent_lesson_promoter.py`.
Schema: `docs/orchestration/contracts/agent_learning_record.v1.json`.

Learning-loop output is not runtime truth, not product behavior, and not
canonical governance until a reviewed repo diff promotes it into the smallest
authoritative surface, such as a scoped `AGENTS.md`, an orchestration contract,
or a repo-tracked Codex skill.

Promotion is proposal-only. The promoter must emit review evidence, not mutate
repo instructions, fixed mapping, branch protection, or product runtime.
