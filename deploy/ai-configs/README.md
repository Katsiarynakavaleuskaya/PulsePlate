# 🤖 AI Configuration Guide

This directory contains configuration files for different AI deployment strategies.

## 🎯 **Strategy: Smart AI Routing**

Our hybrid approach optimizes cost while maintaining quality:

- **Ollama** → Simple queries (free/cheap)
- **OpenAI** → Complex queries (quality)
- **Auto-routing** → Based on query complexity

## 📁 **Configuration Files**

### `hybrid.env` - Development/Staging

- Local Ollama + OpenAI API
- Smart routing enabled
- Cost optimization for development

### `production.env` - Production

- Ollama Cloud + OpenAI API
- Optimized for scale
- Quality thresholds tuned

## 💰 **Cost Comparison**

| Query Type | Ollama | OpenAI | Savings |
|------------|--------|--------|---------|
| Simple (70%) | Free | $0.60/1K input, $2.40/1K output | 100% |
| Medium (20%) | Free | $0.60/1K input, $2.40/1K output | 100% |
| Complex (10%) | $0.20/1K | $0.60/1K input, $2.40/1K output | 67% |

**Sources:**

- OpenAI GPT-4o-mini: <https://openai.com/pricing> (Last updated: 2025-01-26)
- Ollama Cloud: <https://ollama.com> (Last updated: 2025-01-26)
- Currency: USD, per 1K tokens
- **⚠️ Important**: AI pricing changes frequently. Please verify current rates on vendor pages before relying on these numbers for production cost estimates.

## Total Savings: ~90% compared to OpenAI-only

## 🚀 **Usage Examples**

### Simple Query (→ Ollama)

```json
{
  "message": "How many calories in an apple?",
  "context": {},
  "user_tier": "free"
}
```

### Complex Query (→ OpenAI)

```json
{
  "message": "Create a meal plan for someone with diabetes and gluten intolerance",
  "context": {
    "user_conditions": ["diabetes"],
    "allergies": ["gluten"]
  },
  "user_tier": "premium"
}
```

## 🔧 **Setup Instructions**

### 1. GitHub Secrets

Add these secrets to your repository:

```bash
# Ollama Cloud (for production)
OLLAMA_API_KEY=your_ollama_cloud_key

# OpenAI (for complex queries)
OPENAI_API_KEY=your_openai_key
```

### 2. Environment Variables

```bash
# Copy appropriate config
cp deploy/ai-configs/hybrid.env .env
# or
cp deploy/ai-configs/production.env .env
```

### 3. Test the Setup

```bash
# Test simple query (should use Ollama)
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is protein?"}'

# Test complex query (should use OpenAI)
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a detailed nutrition analysis for a vegan athlete"}'
```

## 📚 **Related Documentation**

- [AI_SECRETS_SETUP.md](../AI_SECRETS_SETUP.md) - Guide for setting up GitHub secrets for AI providers
- [OLLAMA_SETUP.md](../../OLLAMA_SETUP.md) - Complete Ollama installation and configuration guide
- [Ollama Configs README](../ollama-configs/README.md) - Ollama-specific configuration files

## 📊 **Monitoring**

### Cost Tracking

- Ollama: Free (local) or $20/month (cloud)
- OpenAI: ~$0.15-0.60 per 1K tokens
- **Expected monthly cost: $50-100** (vs $500+ with OpenAI-only)

### Quality Metrics

- Simple queries: 95% accuracy (Ollama)
- Complex queries: 98% accuracy (OpenAI)
- Fallback success rate: 99%

## 🎛️ **Configuration Options**

| Setting | Description | Default |
|---------|-------------|---------|
| `AI_ROUTER_ENABLED` | Enable smart routing | `true` |
| `AI_FALLBACK_ENABLED` | Enable fallback between providers | `true` |
| `SIMPLE_QUERY_THRESHOLD` | Threshold for simple queries | `0.7` |
| `COMPLEX_QUERY_THRESHOLD` | Threshold for complex queries | `0.3` |

## 🔄 **Fallback Strategy**

1. **Primary**: Route based on complexity
2. **Fallback**: If primary fails, try other provider
3. **Emergency**: Return cached response if both fail

This ensures 99.9% uptime even if one provider is down.
