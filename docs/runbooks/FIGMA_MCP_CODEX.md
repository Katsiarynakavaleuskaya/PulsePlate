# Figma MCP for Codex / Claude Code

<!-- markdownlint-disable MD013 -->

This runbook standardizes Figma MCP setup for code-to-canvas workflow:

1. build UI prototype in code,
2. push variant to Figma canvas,
3. iterate visual versions in Figma with stable node references.

## Scope

### IN

- Codex/Claude Code MCP setup for Figma.
- Verification checklist and troubleshooting.
- Minimal safe workflow for sending local prototypes to Figma.

### OUT

- Product-specific visual decisions.
- Figma design-system governance.
- Runtime app behavior changes.

## Prerequisites

- Valid Figma OAuth token.
- Access to MCP-enabled Codex/Claude environment.
- Local project running (if exporting from localhost route).

## Option A: Claude plugin install flow

If your Claude Code runtime supports plugin install command:

```bash
/plugin install figma@claude-plugin-directory
```

After install:

- Restart Claude Code session.
- Verify Figma tools are visible.

## Option B: Codex MCP config flow (explicit)

Add this to `~/.codex/config.toml`:

```toml
[features]
rmcp_client = true

[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"
bearer_token_env_var = "FIGMA_OAUTH_TOKEN"
http_headers = { "X-Figma-Region" = "us-east-1" }
```

Set token in shell before launching Codex:

```bash
export FIGMA_OAUTH_TOKEN="<your_token>"
echo "$FIGMA_OAUTH_TOKEN"
```

Restart Codex/Cursor after config changes.

## Verification Checklist

- Figma MCP server appears in connected MCP list.
- Figma tools are callable (metadata/context/screenshot/export tools).
- No auth errors in first tool call.
- Region header matches your Figma org region.

## Canonical code-to-Figma flow

1. Implement working UI variant locally.
2. Provide exact page/frame/node link to MCP request.
3. Pull design context and screenshot for that node.
4. Push generated variant to Figma canvas.
5. Create named variants in Figma (A/B/C) with fixed node IDs.
6. Capture mapping in docs (`design URL`, `node ID`, `variant ID`).

## Security Notes

- Never commit `FIGMA_OAUTH_TOKEN` to repo.
- Use environment variables only; rotate token if exposed.
- Keep token scope minimal (design operations only).

## Troubleshooting

- **Token empty:** export token in the same shell that launches Codex.
- **OAuth fails:** ensure `rmcp_client = true` and token has no extra quotes.
- **Server missing in MCP list:** restart IDE/session after config update.
- **Region mismatch:** update `X-Figma-Region` to your account region.

## Evidence Commands

```bash
echo "$FIGMA_OAUTH_TOKEN"
```

Expected:

- non-empty token output in active shell session.
