---
name: pulseplate-ai-reports
description: Produce PulsePlate AI reports in daily, weekly, monthly, and quarterly formats with wellness and GTM focus.
---

# PulsePlate AI Reports

## When to use

- Creating recurring AI market and product intelligence reports.
- Preparing wellness/fitness/psychology AI trend summaries.
- Identifying low-capex, low-regulatory entry opportunities.

## Inputs required

- Report period (`daily`, `weekly`, `monthly`, `quarterly`).
- Audience (`product`, `engineering`, `marketing`, `founder`).
- Geographic focus and language requirements.

## Procedure (commands)

1. Collect validated repo context first:

   ```bash
   ls docs/roadmap docs/audit docs/security
   ```

2. Produce report using canonical structure:
   - Title
   - Highlights (3-7)
   - Tech Trends
   - Wellness AI
   - Easy Entry (3-5 ideas)
   - Marketing and Growth Tips
   - Next Steps
3. Add date and timezone explicitly:
   - Use absolute dates and `America/New_York` when needed.
4. For web research workflows, use bounded evidence and source logs.

## Output format

- `Title`
- `Highlights`
- `Tech Trends`
- `Wellness AI`
- `Easy Entry`
- `Marketing and Growth Tips`
- `Next Steps`

Always include:

- Concrete dates.
- Risk notes (regulatory, ethics, safety language).

## Guardrails

- No medical claims presented as diagnosis/treatment advice.
- No unsupported trend claims without evidence.
- Keep easy-entry ideas non-licensed by default unless explicitly requested otherwise.

## SoT links

- `.cursor/agents/web-research-agent.md`
- `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
- `AGENTS.md`
