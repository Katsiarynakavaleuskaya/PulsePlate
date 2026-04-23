<!-- markdownlint-disable MD013 -->
# Figma MCP Setup Guide

**Date:** 2026-02-24
**Scope:** PulsePlate Figma Remote MCP integration

## Overview

This guide explains how to set up Figma MCP for agent-driven design execution in PulsePlate.

## Prerequisites

- Figma account with full or dev seat access
- Edit/view permissions on PulsePlate Figma file
- Cursor IDE installed

## Setup Steps

### Step 1: Verify MCP Configuration

The tracked template lives at `.cursor/mcp.json.example`.
Create your local `.cursor/mcp.json` from that template.
Note: `.cursor/mcp.json` is gitignored and is expected to remain local-only.

```json
{
  "mcpServers": {
    "figma": {
      "url": "https://mcp.figma.com/mcp"
    }
  }
}
```

### Step 2: Connect Figma in Cursor

1. Open Cursor IDE
2. Open the Dev Mode MCP menu (Cmd/Ctrl + Shift + P → "MCP")
3. Find `figma` in the server list
4. Click "Connect"
5. Complete Figma OAuth authentication when prompted

### Step 3: Verify Connection

After connecting, verify the MCP is working:

1. In Cursor, invoke the Figma MCP tool
2. Test command: `whoami`
3. Expected: authenticated identity payload

## Figma File Requirements

### Page Structure

Your Figma file should have the following page structure (per governance index):

```text
00_Foundation_Tokens
01_Components
10_iOS_Home
11_iOS_Plate
12_iOS_Progress
20_Web_Parity
```

### Access Permissions

- **Minimum:** View access (for reading design structure)
- **Recommended:** Edit access (for creating/updating designs via MCP)

## Environment Variables (Optional)

For advanced scripting, you may need:

```bash
# Figma file key (extract from URL)
export FIGMA_FILE_KEY="your_file_key"

# Team ID (for enterprise accounts)
export FIGMA_TEAM_ID="your_team_id"
```

### Extracting File Key from URL

Figma URL format: `https://www.figma.com/design/{FILE_KEY}/{FILE_NAME}`

Example:
- URL: `https://www.figma.com/design/ABC123xyz/PulsePlate-Design-System`
- File Key: `ABC123xyz`

## Available MCP Tools

Once connected, the following Figma MCP tools are the canonical verification set:

| Tool | Description |
|------|-------------|
| `whoami` | Verify auth and workspace seat/plan |
| `get_metadata` | Fetch file/page/node metadata |
| `get_design_context` | Fetch implementation context for a design node |
| `get_screenshot` | Capture a design node screenshot |
| `generate_figma_design` | Discover capture modes and push supported pages/files |

## Troubleshooting

### Connection Failed

1. Verify you have a full or dev seat in Figma
2. Check that local `.cursor/mcp.json` exists and matches `.cursor/mcp.json.example`
3. Try disconnecting and reconnecting in Cursor MCP menu
4. Clear Cursor cache and restart

### Authentication Issues

1. Ensure you're logged into Figma in your browser
2. Check Figma account permissions
3. Revoke and re-grant OAuth access if needed

### File Not Found

1. Verify you have access to the target Figma file
2. Check file URL for correct file key
3. Ensure file is not in a restricted team

## Security Notes

- `.cursor/mcp.json` is in `.gitignore` (not committed)
- OAuth tokens are managed by Cursor, not stored in config
- Never commit authentication tokens to repository
- Use `.cursor/mcp.json.example` as reference template

## Integration with Design Pipeline

After MCP is connected, you can use design execution scripts:

```bash
# Validate design instructions
python scripts/design/generate_figma_instructions.py --screen ios.home --validate

# Execute design (create in Figma)
python scripts/design/execute_design.py --screen ios.home --execute

# Verify created design
python scripts/design/verify_design.py --screen ios.home
```

## Canonical References

- **MCP Config:** `.cursor/mcp.json`
- **Figma Governance:** `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
- **Implementation Runbook:** `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- **Design Execution Index:** `docs/figma/EXECUTABLE_DESIGN_INDEX.md`
- **Instruction Format:** `docs/figma/FIGMA_AI_INSTRUCTION_FORMAT.md`

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review [Figma MCP documentation](https://help.figma.com/hc/en-us/articles/35281350665623)
3. Check `.cursor/mcp.json.example` for configuration reference
<!-- markdownlint-enable MD013 -->
