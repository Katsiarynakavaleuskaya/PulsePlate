# 🔑 Manual API Key Setup for Cursor MCP

## Step 1: Get OpenAI API Key

1. **Open**: https://platform.openai.com/api-keys
2. **Login** with your ChatGPT Pro account
3. **Click** "Create new secret key"
4. **Name it**: "Cursor MCP Integration"
5. **Copy** the key: `sk-proj-...` (starts with sk-proj-)
6. **Save** it securely

## Protocol note (MCP)

MCP uses **JSON-RPC 2.0**. Requests must include `jsonrpc: "2.0"` and a string `method`.

Example request (list tools):

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

## Step 2: Update Configuration Files

### Update MCP Configuration
```bash
# Edit the MCP config file
nano ~/.cursor/mcp.json
```

Replace `"your_openai_api_key_here"` with your actual API key:
```json
{
  "mcpServers": {
    "pulseplate-chatgpt": {
      "command": "python",
      "args": [
        "/ABSOLUTE/PATH/TO/BMI-App_2025_clean/mcp_pulseplate_server.py"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-proj-YOUR_ACTUAL_KEY_HERE"  # pragma: allowlist secret
      }
    }
  }
}
```

### Update Environment File
```bash
# Edit the environment file
nano ~/.cursor/.env
```

Replace `your_openai_api_key_here` with your actual API key:
```
# OpenAI API Configuration
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_KEY_HERE

# MCP Configuration
MCP_ENABLED=true
```

### Update Cursor Settings
```bash
# Edit Cursor settings
nano ~/.cursor/settings.json
```

Replace `your_openai_api_key_here` with your actual API key:
```json
{
  "cursor.ai.enabled": true,
  "cursor.ai.primaryModel": "gpt-4",
  "cursor.ai.secondaryModel": "gpt-3.5-turbo",
  "cursor.ai.openaiApiKey": "sk-proj-YOUR_ACTUAL_KEY_HERE",  // pragma: allowlist secret
  "cursor.ai.openaiBaseUrl": "https://api.openai.com/v1",
  "mcp.enabled": true,
  "mcp.servers": ["pulseplate-chatgpt"]
}
```

## Step 3: Test Integration

1. **Restart Cursor**
2. **Open Command Palette**: Cmd+Shift+P
3. **Run**: "MCP: List Tools"
4. **Verify**: ChatGPT tools are available

## Step 4: Verify API Key

Test your API key:
```bash
# Test API key
curl -H "Authorization: Bearer sk-proj-YOUR_KEY_HERE" \
     https://api.openai.com/v1/models
```

## Troubleshooting

### If MCP tools don't appear:
1. Check API key format (should start with `sk-proj-`)
2. Verify all configuration files are updated
3. Restart Cursor completely
4. Check Cursor logs for errors

### If API key doesn't work:
1. Verify key is correct
2. Check OpenAI account has credits
3. Ensure Pro subscription is active
4. Try creating a new API key

## Security Notes

- Never commit API keys to Git
- Use environment variables in production
- Rotate keys regularly
- Monitor usage in OpenAI dashboard
