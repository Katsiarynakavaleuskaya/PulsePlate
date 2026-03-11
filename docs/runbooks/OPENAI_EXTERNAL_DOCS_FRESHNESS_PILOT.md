# OpenAI External Docs Freshness Pilot (Codex / Cursor)

<!-- markdownlint-disable MD013 -->

This runbook standardizes a **local-only** OpenAI docs freshness workflow for
PulsePlate dev agents.

The goal is narrow:

1. keep repo-native context canonical,
2. use official OpenAI docs as the truth source for OpenAI behavior,
3. add an optional external docs lane for live agent sessions.

## Scope

### IN

- Local dev-agent setup for OpenAI docs freshness
- Codex/Cursor examples
- One shared prompt pack for spot-checking tool quality
- Governance rules for external doc tools

### OUT

- CI integration
- Runtime app behavior changes
- Product-facing RAG
- Automatic promotion of external notes into repo canon

## Canonical Baseline

Before any MCP or CLI docs helper:

- repo context stays canonical through `context_pack` and task bootstrap
- OpenAI tasks should prefer official OpenAI docs
- durable findings must be promoted through KPP

Canonical references:

- `scripts/orchestration/context_pack.py`
- `scripts/orchestration/task_bootstrap.py`
- `docs/memory/kpp_knowledge_promotion_pipeline.md`
- `docs/dev/CODEX_SKILLS.md`

## Recommendation

### Primary optional pilot: Context7

Use `Context7` first when you want live MCP-backed docs in Codex/Cursor.

Why this lane won the pilot:

- it is packaged directly as an MCP server
- its published setup covers Codex and Cursor explicitly
- it fits the repo's dev-agent runtime shape better than a CLI-only lookup flow

### Secondary comparator: Context Hub

Use `Context Hub` as the OSS comparator when you want:

- CLI lookup from terminal
- skill-file copy into agent tooling
- local annotations for personal notes

Do **not** treat `chub annotate` notes as canonical project memory.

## Codex Setup (Context7)

Add this to your Codex MCP config:

```toml
[mcp_servers.context7]
args = ["-y", "@upstash/context7-mcp", "--api-key", "ctx7-demo-value"]
command = "npx"
startup_timeout_ms = 20_000
```

Remote alternative:

```toml
[mcp_servers.context7]
url = "https://mcp.context7.com/mcp"
http_headers = { "<context7-auth-header>" = "ctx7-demo-value" }
```

Notes:

- do not commit API keys
- replace `<context7-auth-header>` with the provider's documented auth header
- restart Codex after config changes
- if `npx` startup times out, raise `startup_timeout_ms` before changing lanes

## Cursor Setup (Context7)

Prefer a **project-scoped** config when testing inside this repo.

Example `.cursor/mcp.json` shape:

```json
{
  "mcpServers": {
    "figma": {
      "url": "https://mcp.figma.com/mcp"
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp", "--api-key", "ctx7-demo-value"]
    }
  }
}
```

Remote alternative:

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "<context7-auth-header>": "ctx7-demo-value"
      }
    }
  }
}
```

## Context Hub Comparator Setup

Install:

```bash
npm install -g @aisuite/chub
```

CLI checks:

```bash
chub --help
chub search openai --json
chub search responses openai --json
```

Cursor skill copy flow:

```bash
mkdir -p .cursor/rules
cp $(npm root -g)/@aisuite/chub/skills/get-api-docs/SKILL.md .cursor/rules/get-api-docs.md
```

Terminal-first usage:

```bash
chub get openai/chat
```

Use this lane as advisory tooling only. If it finds a useful workaround, move
the durable conclusion into git through KPP.

## OpenAI-First Prompt Pack

Use the same prompt when comparing lanes:

```text
Implement a minimal Python example that calls the current OpenAI Responses API
for text generation. Cite the official OpenAI documentation link you used and
do not fall back to legacy Chat Completions unless the docs explicitly require
it.
```

Optional JavaScript variant:

```text
Implement a minimal JavaScript example that calls the current OpenAI Responses
API for text generation. Cite the official OpenAI documentation link you used
and do not use legacy Chat Completions.
```

## Verification Checklist

- The answer uses **Responses API**.
- The answer includes an official OpenAI docs link.
- The answer does not invent parameters.
- Any reusable insight is promoted into a repo artifact through KPP.
- No CI/runtime files are modified just to enable local docs tooling.

## Governance Rules

- External docs tools are advisory, not canonical.
- Local caches, MCP outputs, and `chub annotate` notes do not override repo SoT.
- If a rule, workaround, or stable instruction is worth keeping, promote it
  into exactly one repo artifact.
- Keep external docs tooling out of CI and production app paths.

## Security Notes

- Never commit `CONTEXT7_API_KEY` or any other token.
- Prefer project-scoped MCP config where supported.
- Treat external retrieved docs like any other untrusted input: verify against
  official sources before promotion into repo memory.

## Troubleshooting

- **Context7 server missing:** restart the client after adding MCP config.
- **Context7 startup timeout:** increase `startup_timeout_ms` first.
- **Context Hub returns generic OpenAI hits only:** fall back to official
  OpenAI docs for the task and record the limitation in the pilot notes.
- **Agent answer is unsourced:** reject the answer and rerun with the prompt
  pack requirement to cite official docs.

## Evidence Commands

```bash
npx -y @upstash/context7-mcp --help
npx -y @aisuite/chub --help
npx -y @aisuite/chub search openai --json
npx -y @aisuite/chub search responses openai --json
```
