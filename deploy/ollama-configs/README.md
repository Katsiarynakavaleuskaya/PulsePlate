# 🦙 Ollama Configuration Files

This directory contains configuration files for different Ollama deployment scenarios.

## Files

- **`local.env`** - Local Ollama setup (development/staging)
- **`cloud.env`** - Ollama Cloud setup (production)

## Usage

### Local Development
```bash
# Use local.env for development
docker-compose --env-file deploy/ollama-configs/local.env up
```

### Production with Ollama Cloud
```bash
# Use cloud.env for production
docker-compose --env-file deploy/ollama-configs/cloud.env up
```

## Environment Variables

| Variable | Local | Cloud | Description |
|----------|-------|-------|-------------|
| `OLLAMA_ENDPOINT` | `http://host.docker.internal:11434` | `https://api.ollama.ai/v1` | Ollama server URL |
| `OLLAMA_API_KEY` | Not needed | Required | API key for Ollama Cloud |
| `OLLAMA_MODEL` | `llama3` | `llama3` | Model to use |
| `ENVIRONMENT` | `staging` | `production` | Environment type |

## Cost Comparison

### Local Ollama
- ✅ **Free** (after initial setup)
- ❌ Requires GPU/server
- ❌ Manual updates
- ❌ No scaling

### Ollama Cloud
- 💰 **$20/month** for 100k requests
- ✅ No server management
- ✅ Automatic scaling
- ✅ Always updated models
- ✅ Global CDN

**Recommendation**: Use Ollama Cloud for production - it's much more cost-effective than running your own GPU servers!
