# Figma MCP for Codex / GPT-5.4 Pro

<!-- markdownlint-disable MD013 -->

This runbook standardizes Figma MCP setup for the PulsePlate
`Codex + GPT-5.4 Pro` workflow:

1. build UI prototype in code,
2. push variant to Figma canvas,
3. iterate visual versions in Figma with stable node references.

## Scope

### IN

- Codex MCP setup for Figma.
- Verification checklist and troubleshooting.
- Minimal safe workflow for sending local prototypes to Figma.

### OUT

- Product-specific visual decisions.
- Figma design-system governance.
- Runtime app behavior changes.

## Prerequisites

- Valid Figma OAuth token.
- Access to MCP-enabled Codex runtime.
- Local project running (if exporting from localhost route).

## Codex MCP config flow (explicit)

Add this to `~/.codex/config.toml`:

```toml
[features]
rmcp_client = true

[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"
bearer_token_env_var = "FIGMA_OAUTH_TOKEN"
http_headers = { "X-Figma-Region" = "us-east-1" }
```

If you are unsure about region:

- confirm your org region in Figma admin/workspace settings, or
- omit the `X-Figma-Region` header initially and add it only if required by
  your tenant/network policy.

Set token in shell before launching Codex:

```bash
export FIGMA_OAUTH_TOKEN="<your_token>"
test -n "$FIGMA_OAUTH_TOKEN" && echo "FIGMA_OAUTH_TOKEN is set"
```

Restart Codex after config changes.

## Verification Checklist

- Figma MCP server appears in connected MCP list.
- Figma tools are callable (metadata/context/screenshot/export tools).
- No auth errors in first tool call.
- Region header matches your Figma org region.
- Runtime capability expectations are confirmed against
  [`FIGMA_MCP_RUNTIME_MATRIX.md`](FIGMA_MCP_RUNTIME_MATRIX.md).
- `generate_figma_design` is checked in discovery mode before claiming
  `code -> Figma` push support.

## Canonical code-to-Figma flow

1. Implement working UI variant locally.
2. Provide exact page/frame/node link to MCP request.
3. Pull design context and screenshot for that node.
4. If capture is needed, call `generate_figma_design` in discovery mode.
5. Choose `existingFile`, `newFile`, or `clipboard`.
6. Push generated variant to Figma canvas when the chosen mode allows it.
7. Create named variants in Figma (A/B/C) with fixed node IDs.
8. Capture mapping in docs (`design URL`, `node ID`, `variant ID`).

## PulsePlate Runtime Baseline

As of `2026-03-08`, this repo treats `Codex + GPT-5.4 Pro` as the primary
agent runtime for Figma MCP. Do not document a separate Claude-only lane for
design push unless a future session proves a Codex regression.

## Security Notes

- Never commit `FIGMA_OAUTH_TOKEN` to repo.
- Use environment variables only; rotate token if exposed.
- Keep token scope minimal (design operations only).

## Troubleshooting

- **Token empty:** export token in the same shell that launches Codex.
- **OAuth fails:** ensure `rmcp_client = true` and token has no extra quotes.
- **Server missing in MCP list:** restart IDE/session after config update.
- **Region mismatch:** update `X-Figma-Region` to your account region.
- **`generate_figma_design` unavailable:** fall back to
  `get_design_context + get_screenshot + Code Connect` and record the runtime
  limitation in the session evidence.

## Evidence Commands

```bash
test -n "$FIGMA_OAUTH_TOKEN" && echo "FIGMA_OAUTH_TOKEN is set"
printf "FIGMA_OAUTH_TOKEN length: %s\n" "${#FIGMA_OAUTH_TOKEN}"
```

Expected:

- token presence check passes in active shell session.
- length is greater than zero.
