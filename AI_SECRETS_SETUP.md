# 🔐 AI Secrets Setup Guide

## 📋 **Required Secrets**

The following GitHub Secrets are required for the hybrid AI system to work:

### ✅ **Already Configured:**

- `PULSEPLATE_OPENAI` - OpenAI API key (already configured)

### 🔧 **Need to Configure:**

#### 1. **OLLAMA_API_KEY**

⚠️ **SECURITY WARNING**: Never commit secrets to source control! Avoid pasting secret values in unsecured channels (chat, email, issue trackers). Always use GitHub Secrets or environment variables/secret managers. If secrets are accidentally exposed, rotate them immediately.

```bash
# For Ollama Cloud (recommended for production)
gh secret set OLLAMA_API_KEY --body "REPLACE_WITH_ACTUAL_API_KEY"

# Or for local Ollama (leave empty)
gh secret set OLLAMA_API_KEY --body ""
```

#### 2. **HUGGINGFACE_API_TOKEN** (optional, for embeddings)

```bash
# Hugging Face API token for embeddings and specialized models
gh secret set HUGGINGFACE_API_TOKEN --body "REPLACE_WITH_ACTUAL_HF_TOKEN"
```

#### 3. **GHCR_READ_TOKEN** (for Docker images)

```bash
# Personal Access Token with read:packages permissions
gh secret set GHCR_READ_TOKEN --body "REPLACE_WITH_ACTUAL_GITHUB_PAT"
```

## 🚀 **Quick Setup Commands**

### **Option 1: Ollama Cloud (Recommended)**

```bash
# 1. Get Ollama Cloud API key from [Ollama Cloud sign-in](https://ollama.com/signin)
# 2. Set the secret
gh secret set OLLAMA_API_KEY --body "REPLACE_WITH_ACTUAL_OLLAMA_KEY"

# 3. Verify secrets
gh secret list
```

### **Option 2: Local Ollama (Development)**

```bash
# 1. Leave Ollama API key empty for local development
gh secret set OLLAMA_API_KEY --body ""

# 2. Verify secrets
gh secret list
```

## 🔍 **Verify Configuration**

```bash
# Check all secrets
gh secret list

# Expected output (only AI-related secrets shown):
# NAME                            UPDATED
# OLLAMA_API_KEY                  just now
# PULSEPLATE_OPENAI               about 20 days ago
# HUGGINGFACE_API_TOKEN           just now
# GHCR_READ_TOKEN                 just now

# Note: Only these 4 secrets are required for AI routing setup.
# Other secrets (CODECOV, GROK_API, etc.) are optional and not used by the AI system.
# SOURCERY                        about 1 month ago
# WINDSURF                        about 1 month ago
```

## 🧪 **Test the Setup**

### **1. Test Simple Query (should use Ollama)**

```bash
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many calories in an apple?",
    "context": {},
    "user_tier": "free"
  }'
```

### **2. Test Complex Query (should use OpenAI)**

```bash
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a detailed meal plan for someone with diabetes and gluten intolerance",
    "context": {
      "user_conditions": ["diabetes"],
      "allergies": ["gluten"]
    },
    "user_tier": "premium"
  }'
```

### **3. Test Cost Estimation**

```bash
curl "http://localhost:8000/api/ai/cost-estimate?message=How%20many%20calories%20in%20an%20apple?&provider=auto"
```

## 💰 **Cost Monitoring**

### **Expected Costs:**

- **Simple queries (60%)**: Ollama (free)
- **Embedding queries (20%)**: Hugging Face (free tier: rate limits apply)
- **Medium queries (15%)**: Ollama (free) or OpenAI ($0.15/1M input, $0.60/1M output tokens)
- **Complex queries (5%)**: OpenAI ($0.15/1M input, $0.60/1M output tokens)

⚠️ **PRICING WARNING**: Provider pricing is volatile and changes frequently. Always verify current pricing on the provider's official site before making decisions.

**Sources:**

- OpenAI GPT-4o-mini pricing: <https://openai.com/pricing> (Last updated: 2025-01-25)
- Ollama Cloud: <https://ollama.com> (Launched: October 2025)
- Assumptions: ~100 tokens per simple query, ~500 tokens per complex query

> **Note**: This document was last reviewed on 2025-01-25. Prices may have changed since then.

### **Monthly Estimate:**

- **600 simple queries**: $0 (Ollama)
- **200 embedding queries**: $0 (Hugging Face free tier)
- **150 medium queries**: $0-0.1 (Ollama/OpenAI)
- **50 complex queries**: $0.05 (OpenAI)
- **Total**: ~$0.05-0.15/month (vs $3+ with OpenAI-only)

## 🔧 **Environment Variables**

The system uses these environment variables:

```bash
# Ollama Configuration
OLLAMA_ENDPOINT=https://ollama.com  # or http://localhost:11434
OLLAMA_API_KEY=your_ollama_cloud_key
OLLAMA_MODEL=llama3

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini

# Hugging Face Configuration
HUGGINGFACE_API_TOKEN=your_huggingface_token
HUGGINGFACE_MODEL=nvidia/llama-embed-nemotron-8b

# AI Router Settings
AI_ROUTER_ENABLED=true
AI_FALLBACK_ENABLED=true
```

## 🚨 **Troubleshooting**

### **Common Issues:**

1. **"Missing API key" error**
   - Check if secrets are set: `gh secret list`
   - Verify secret names match workflow

2. **"Ollama connection failed"**
   - For local: ensure Ollama is running
   - For cloud: verify API key is correct

3. **"OpenAI rate limit"**
   - Check OpenAI API key validity
   - Monitor usage in OpenAI dashboard

### **Debug Commands:**

```bash
# Check workflow logs
gh run list
gh run view <run-id>

# Test API endpoints
curl http://localhost:8000/api/ai/providers
curl http://localhost:8000/health
```

## 📊 **Monitoring Dashboard**

After setup, monitor:

- **Cost per request** in API responses
- **Provider usage** in logs
- **Fallback frequency** in metrics
- **Response quality** in user feedback

## 🎯 **Next Steps**

1. ✅ Set up secrets
2. ✅ Deploy to staging
3. ✅ Test AI routing
4. ✅ Monitor costs
5. ✅ Optimize thresholds
6. ✅ Scale to production

