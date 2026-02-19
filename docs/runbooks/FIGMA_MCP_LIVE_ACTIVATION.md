# Figma MCP Live Activation (Code -> Canvas)

<!-- markdownlint-disable MD013 -->

This runbook is a practical execution protocol for the first real
`local prototype -> Figma canvas` session after setup.

## Goal

- Verify Figma MCP is reachable in the active IDE session.
- Verify token and region settings are valid.
- Execute one real push cycle from local prototype to Figma.
- Capture reproducible evidence for future sessions.

## Preconditions

- `docs/runbooks/FIGMA_MCP_CODEX.md` already completed.
- `FIGMA_OAUTH_TOKEN` exists in the environment that launches IDE/Codex.
- Figma MCP server is connected in runtime tools list.
- You have one target Figma file/frame URL for variant placement.

## Step-by-Step Session Protocol

### Step 1: Environment sanity

Run locally:

```bash
test -n "$FIGMA_OAUTH_TOKEN" && echo "FIGMA_OAUTH_TOKEN is set"
printf "FIGMA_OAUTH_TOKEN length: %s\n" "${#FIGMA_OAUTH_TOKEN}"
```

Expected:

- both commands succeed,
- length > 0.

### Step 2: MCP visibility check

In IDE/Codex MCP panel:

- confirm `figma` server exists,
- confirm Figma tools are callable (context/screenshot/metadata-like tools).

### Step 3: Pick one source route/frame

- open a concrete local screen variant (example: Home/Progress card state),
- define one canonical target frame in Figma,
- prepare a single variant label (for example: `v1_compact_live`).

### Step 4: Push first variant

- request MCP flow: fetch context -> screenshot -> push variant to canvas,
- avoid parallel variant pushes in first session,
- record returned frame/node references.

### Step 5: Validate in Figma

- visual parity check (layout/text/spacing),
- node naming sanity (`variant_id`, `source_route`, `date`),
- no duplicate unnamed layers.

### Step 6: Capture evidence

Do not edit `docs/runbooks/FIGMA_MCP_SESSION_EVIDENCE_TEMPLATE.md` directly.
For each live session, copy it to a session file under:

- `docs/runbooks/sessions/FIGMA_MCP_SESSION_<YYYY-MM-DD>_<slug>.md`

Then store:

- source route,
- target Figma URL,
- created node/frame IDs,
- success/failure notes,
- next action.

## Failure Modes and Fast Recovery

1. **Token missing**
   - Re-export token and fully restart IDE session.
2. **Figma server not listed**
   - Re-check plugin/config and restart MCP runtime.
3. **Region/header mismatch**
   - Remove header temporarily, then re-add confirmed region.
4. **Push succeeded but wrong frame**
   - verify exact target URL/node before push; retry with strict mapping.
5. **Visual mismatch**
   - keep same node and iterate variant naming (`v2`, `v3`) with diffs logged.

## Security Notes

- Never paste raw token into logs, comments, or PR text.
- Evidence must include token presence/length only, never token value.
- If accidental leak happens, rotate token immediately.

## Definition of Done (Live Activation)

- [ ] one variant is pushed from local prototype to Figma canvas,
- [ ] node/frame references are captured in evidence template,
- [ ] no secrets leaked in commands/logs/comments,
- [ ] first iteration loop (`v1 -> v2`) is reproducible by another teammate.
