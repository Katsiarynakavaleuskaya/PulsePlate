# 🦙 Ollama Configuration Files

This directory contains configuration files for different Ollama deployment scenarios.

## Files

- **`local.env.example`** - Local Ollama setup (development/staging)
- **`cloud.env`** - Ollama Cloud setup (production)

## Usage

### Local Development

```bash
# Use local.env.example for development
# Note: Add env_file: deploy/ollama-configs/local.env.example to your docker-compose.yml
docker-compose up
```

### Production with Ollama Cloud

```bash
# Use cloud.env for production
# Note: Add env_file: deploy/ollama-configs/cloud.env to your docker-compose.yml
docker-compose -f deploy/docker-compose.production.yaml up
```

## Environment Variables

| Variable | Local | Cloud | Description |
|----------|-------|-------|-------------|
| `OLLAMA_ENDPOINT` | `http://host.docker.internal:11434` | `https://ollama.com/v1` | Ollama server URL |
| `OLLAMA_API_KEY` | Not needed | Required | API key for Ollama Cloud |
| `OLLAMA_MODEL` | `llama3:8b` | `llama3:8b` | Model to use (pinned for stability) |
| `ENVIRONMENT` | `staging` | `production` | Environment type |

## Cost Comparison

### Local Ollama

- ✅ **Free** (after initial setup)
- ❌ Requires GPU/server
- ❌ Manual updates
- ❌ No scaling

### Ollama Cloud

- 💰 **Pro tier: $20/month** — usage-based metered pricing coming soon
- ✅ No server management
- ✅ Automatic scaling
- ✅ Always updated models
- ✅ Global CDN

**Recommendation**: Use Ollama Cloud for production - it's much more cost-effective than running your own GPU servers!
