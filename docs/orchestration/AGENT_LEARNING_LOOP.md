# Agent Learning Loop

The repo-governed agent learning loop converts repeated role-agent, review,
premortem, workflow, architecture, and successful-iteration patterns into
redacted, deterministic proposals for future instruction or skill updates.

Shared helper: `scripts/orchestration/agent_learning_loop.py`.
Extractor CLI: `scripts/orchestration/agent_lesson_extractor.py`.
Promoter CLI: `scripts/orchestration/agent_lesson_promoter.py`.
Schema: `docs/orchestration/contracts/agent_learning_record.v1.json`.
Records must declare `pattern_kind` as either `failure` or
`successful_iteration` so negative and positive lessons do not collapse into the
same fingerprint.
Records must also include `learning_metrics` with bounded process metrics:
`repeat_failure_reduction`, `successful_pattern_reuse`,
`premortem_code_closure_rate`, `review_actionable_escape_reduction`,
`agent_iteration_quality`, `user_impact_clarity`, `business_risk_clarity`, and
`project_development_signal`. These metrics are proposal metrics only: they do
not write runtime telemetry, product runtime truth, semantic cache, or graph
truth.

In the Experiment Runner creative-context line, this learning loop is the
feedback rail for both blind spots and effective creative iteration patterns.
It complements premortem: premortem forecasts future user/business/project/
security/governance failures on the actual diff, while learning-loop records
repeatable patterns and the process metrics that would show whether later
promotion improved agent behavior.

Learning-loop output is not runtime truth, not product behavior, and not
canonical governance until a reviewed repo diff promotes it into the smallest
authoritative surface, such as a scoped `AGENTS.md`, an orchestration contract,
or a repo-tracked Codex skill.

Promotion is proposal-only. The promoter must emit review evidence, not mutate
repo instructions, fixed mapping, branch protection, semantic cache, graph
truth, review threads, or product runtime. If a lesson affects the current PR
scope, the PR must close that issue with code, schema, tests, guards, or policy
changes; a learning record alone is not closure.
