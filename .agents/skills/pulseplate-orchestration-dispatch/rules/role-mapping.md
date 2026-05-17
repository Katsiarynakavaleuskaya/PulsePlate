# Role-to-Qoder Type Mapping

Canonical mapping from PulsePlate agent slugs to Qoder subagent types.

## Mapping Table

| Agent slug | readonly | Default Qoder type | Override conditions |
|------------|----------|-------------------|---------------------|
| agent-coordinator | false | Research | Always analysis mode |
| architecture-specialist | true | Research | Never Coding |
| philosophy-agent | true | Research | Never Coding |
| rag-systems-agent | false | Research | Coding only if mode=runtime |
| logic-agent | true | Research | Never Coding |
| security-auditor | true | Research | Never Coding |
| qa-engineer-agent | false | Verify | Always runs tests |
| bug-hunter | false | Verify | Always runs tests |
| backend-engineer | false | Coding | Research if mode=analysis |
| frontend-engineer | false | Coding | Browser if UI validation |
| dev-operator | false | Coding | Research if mode=analysis |
| creative-designer | false | Research | Coding if mode=runtime |
| web-research-agent | true | Research | Always Research |
| cursor-specialist-agent | false | Research | Coding if mode=runtime |
| All others | varies | Research | Safe fallback |

## Special Overrides

### Reviewer slot

When an agent occupies the "reviewer" slot (as defined in
`docs/orchestration/AGENT_ROUTING_GRAPH.md`), always use **CodeReview** type
regardless of the default mapping above. The reviewer slot is determined by
the packet's review section or routing graph edge annotation.

### Mode-based resolution

The `--mode` flag (or packet `mode` field) influences type selection:

- `mode=analysis` — forces all non-readonly agents to Research type
- `mode=runtime` — allows Coding type for agents that support it
- `mode=review` — forces CodeReview type for all agents in the sequence

### Verify type agents

Agents mapped to **Verify** type (qa-engineer-agent, bug-hunter) always run
tests and validations. They receive `make verify` or specific test commands
in their prompt. They never produce code changes — only findings.

## Fallback Rule

Any agent slug not listed in this table defaults to **Research** type.
This is the safest fallback since Research agents cannot modify files.
