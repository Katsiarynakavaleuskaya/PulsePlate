# Agent Model Selection Policy

This document owns model guidance for `.cursor/agents/*.md` and native Codex
role dispatch. It does not select a model in the host, run a provider service,
or change the packet's role order, ownership or permissions.

## Inherited dispatch by default

Frontmatter `model: auto` is role metadata. For ordinary Codex native dispatch,
omit both `model` and `reasoning_effort` from child arguments so the host's
selected model and effort are inherited. Do not restart an active task to change
its model. Templates are examples, not active host configuration.

An explicit operator lock covering all children takes precedence over the
optional mode below. Choosing the coordinator's baseline model in the UI alone
does not cancel an explicitly enabled routing mode. If an explicit lock conflicts
with the protected-work boundary, report the conflict instead of granting Sol
that work or silently overriding the lock.

Model pinning does not prove deterministic output, correct reasoning or absence
of drift. Retain concrete inputs, versions, decisions, tests and observed results
for reproducibility claims. Do not claim speed, accuracy or cost improvement
without a relevant measurement.

## Explicitly enabled Astra/Sol mode

Enable only through a direct operator instruction for native dispatch. The
Astra coordinator applies the following guidance to each new child after
canonical role routing; this is not an executable risk classifier.

| Admitted work | Native selection |
| --- | --- |
| Finite, positively bounded low-risk reads or focused tests/checks | `gpt-5.6-sol`, `reasoning_effort=medium` |
| Bounded low-risk implementation with an existing explicit role owner | `gpt-5.6-sol`, `reasoning_effort=high` |
| Protected, unknown-risk or final work | Astra, retaining the coordinator's selected effort |

Protected work includes auth, billing, security policy, CI/workflows, deployment,
validators/authority mechanisms, final review, synthesis and merge-readiness
judgments. Apparent simplicity, a small diff or a worker transport does not make
such work eligible for Sol. Unclear classification stays with Astra. In this
mode the coordinator remains Astra; its current model/effort and active children
are not changed in place.
Protected classification takes precedence over both low-risk rows, including
read/check tasks on those surfaces.

For a Sol override, use `fork_turns="none"` or a host-supported positive bounded
history fork. Full-history inheritance cannot be combined with model/effort
overrides. Explicitly deliver the full role definition, applicable instructions,
packet, accepted criteria and predecessor evidence; a reduced history fork does
not reduce required context. Preserve the manifest's type, occurrence, serial
order, readonly flag and sole implementation owner.

Allow at most one substantive escalation from an insufficient Sol result,
through the Astra coordinator, with the attempted work, evidence and unresolved
question. The coordinator retains the accepted scope and decides the Astra
handoff. Sol must not recursively spawn a replacement or initiate a model loop.
A service HTTP 403 is an access/service failure, not permission for model
roulette. Diagnose that prerequisite and retain its error. If Sol itself is
unavailable at child creation, report the availability failure and use inherited
model/effort for a new child unless an explicit operator lock forbids fallback;
an unresolved lock stops that dispatch. Do not reclassify an HTTP 403 as model
unavailability.

## Native argument examples

The reference basis is OpenAI's [Astra model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra),
[scoped skills and prompting guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra),
and [native subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents).
Their guidance informs explicit task boundaries, focused instructions and testing;
the exact policy above is the operator-approved repository choice.
DeepLearning.AI's public [Evaluating AI Agents course outline](https://www.deeplearning.ai/courses/evaluating-ai-agents)
lists router/skill and trajectory evaluations, while its [error-analysis article](https://www.deeplearning.ai/the-batch/improve-agentic-performance-with-evals-and-error-analysis-part-2/)
motivates examining failures before changing components. Here that supports
separate step/example checks and observed complete task traces. The public
outline is reference evidence, not a claim that the full course was reviewed
or that this routing improves performance.

These are illustrative arguments to the existing native spawn tool, not a new
configuration schema or runtime router. The coordinator must supply the actual
full required context in `message`; these short examples do not constitute its
delivery. The packet's native binding still owns `agent_type`.

### Sol read/check example

With the mode explicitly enabled and this documentation-link check classified
as bounded low-risk work, a Cursor specialist uses its native explorer binding:

```json
{
  "task_name": "bounded_link_check",
  "message": "You are PulsePlate custom role cursor-specialist-agent. Check only the assigned documentation links using the supplied full required context; return evidence without edits.",
  "agent_type": "explorer",
  "fork_turns": "none",
  "model": "gpt-5.6-sol",
  "reasoning_effort": "medium"
}
```

### Sol implementation example

For an already-authorized low-risk client copy change with frontend-engineer
as the packet's implementation owner:

```json
{
  "task_name": "bounded_copy_change",
  "message": "You are PulsePlate custom role frontend-engineer. Apply only the approved client copy change within your packet-owned files using the supplied full required context.",
  "agent_type": "worker",
  "fork_turns": "none",
  "model": "gpt-5.6-sol",
  "reasoning_effort": "high"
}
```

### Protected/unknown/final work example

With an Astra coordinator, inherit its model and selected effort. This example
uses the security role's reviewer-slot binding and grants no permission to edit:

```json
{
  "task_name": "security_review",
  "message": "You are PulsePlate custom role security-auditor. Perform the assigned read-only review using the supplied full required context, packet and predecessor evidence.",
  "agent_type": "explorer"
}
```

## Provider and authority boundary

Native child arguments do not activate
`scripts/orchestration/provider_model_tier_policy.py` or the packet's inert
`provider_model_tier_routing` telemetry. That separate surface remains
`gate_status=closed`, `provider_calls_allowed=false`, `runtime_allowed=false`
and `selected_route=no_runtime_selection`. No provider wiring, semantic cache,
model service, scan, approval or merge authority follows from this guidance.

Root `AGENTS.md` owns role gates, validation budgets and protected human actions.
Follow `docs/orchestration/workflow.md` for phase admission and the dispatch
skill for existing packet/context consumption. Model choice never replaces any
required role, review, test or current-head gate.
