---
description: Create a reviewed PulsePlate reflection packet after execution
---

# Create Reflection Packet

Use this after a bounded task, incident, or review cycle.

## Required fields

- `reflection_id`
- `task_id`
- `owner`
- `context`
- `what_worked`
- `what_failed`
- `root_cause`
- `repeat_risk`
- `proposed_improvement`
- `promotion_target`
- `human_review_required`

## Output format

```yaml
reflection_id: REF-...
task_id: TASK-...
owner: ...
context: ...
what_worked:
  - ...
what_failed:
  - ...
root_cause:
  - ...
repeat_risk: low|medium|high
proposed_improvement:
  kind: docs|rule|schema|tooling|process
  summary: ...
promotion_target:
  path: ...
human_review_required: true
notes:
  - ...
```

## Hard rule

Reflection can propose improvement, but it cannot silently change canonical policy.
