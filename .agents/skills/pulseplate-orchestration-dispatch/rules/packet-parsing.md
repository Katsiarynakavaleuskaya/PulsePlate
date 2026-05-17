# Packet Parsing Rules

How to extract the role order from a governance packet file.

## Locating the Role Order Section

Scan the packet for a heading (any level) containing one of:
- "Coordinator Role Order"
- "Role Order"
- "Role-Agent Order"

The section immediately following this heading contains the ordered list.

## Parsing the List

Role order is expressed as a numbered Markdown list:

```markdown
1. agent-coordinator — scope analysis and task decomposition
2. architecture-specialist — verify structural alignment
3. philosophy-agent — validate epistemic invariants
4. qa-engineer-agent -> bug-hunter — post-open mandatory pass
```

### Extraction rules

1. **Strip numbering**: Remove leading `N.` or `N)` prefix
2. **Extract slug**: The agent slug is the first token (hyphenated-lowercase word)
3. **Strip description**: Everything after ` — ` (em-dash) or ` - ` is description, ignore it
4. **Handle chain notation**: `slug-a -> slug-b` means two agents in strict sequence
   - Both are separate dispatch entries
   - Second depends on first (`depends_on_previous: true`)
5. **Handle group notation**: `[slug-a, slug-b]` means parallelizable group
   - Both are separate entries with same `parallelizable_groups` id

## Post-open Mandatory Pass

The notation `qa-engineer-agent -> bug-hunter` (or any `->` chain at the end)
indicates the mandatory post-open pass. This pair:
- Always appears last in the dispatch sequence
- Is never parallelized with other agents
- Is never skipped regardless of packet scope

## Validation

After parsing, verify:
1. First entry is `agent-coordinator` (or coordinator-equivalent)
2. Last entry includes the QA mandatory pass
3. No duplicate slugs (except in chain notation)
4. All slugs resolve to known agent definitions in `.github/agents/`

If validation fails, emit a warning but proceed with best-effort parsing.
