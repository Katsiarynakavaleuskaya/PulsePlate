# 🔐 AI Secrets Setup Guide

## 📋 **Required Secrets**

Для работы гибридной AI системы нужны следующие GitHub Secrets:

### ✅ **Already Configured:**
- `PULSEPLATE_OPENAI` - OpenAI API ключ (уже настроен)

### 🔧 **Need to Configure:**

#### 1. **OLLAMA_API_KEY**
```bash
# Для Ollama Cloud (рекомендуется для продакшн)
gh secret set OLLAMA_API_KEY --body "your_ollama_cloud_api_key_here"

# Или для локального Ollama (оставить пустым)
gh secret set OLLAMA_API_KEY --body ""
```

#### 2. **GHCR_READ_TOKEN** (для Docker images)
```bash
# Personal Access Token с правами read:packages
gh secret set GHCR_READ_TOKEN --body "your_github_pat_token"
```

## 🚀 **Quick Setup Commands**

### **Option 1: Ollama Cloud (Recommended)**
```bash
# 1. Get Ollama Cloud API key from https://ollama.ai/cloud
# 2. Set the secret
gh secret set OLLAMA_API_KEY --body "your_ollama_cloud_key"

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

# Expected output:
# NAME                            UPDATED
# CODECOVE_TOCKEN                 about 28 days ago
# CODECOVE_TOKEN_STATIC_ANALYSIS  about 28 days ago
# CODECOV_TOKEN_CI                about 28 days ago
# GITHUB                          about 1 month ago
# GROK_API                        about 1 month ago
# HF_TOKEN                        about 1 month ago
# HUGGING_FACE                    about 1 month ago
# OLLAMA_API_KEY                  just now
# PULSEPLATE_OPENAI               about 20 days ago
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
- **Simple queries (70%)**: Ollama (free)
- **Medium queries (20%)**: Ollama (free) or OpenAI ($0.15/1K tokens)
- **Complex queries (10%)**: OpenAI ($0.60/1K tokens)

### **Monthly Estimate:**
- **1000 simple queries**: $0 (Ollama)
- **200 medium queries**: $0-3 (Ollama/OpenAI)
- **100 complex queries**: $6 (OpenAI)
- **Total**: ~$6-9/month (vs $60+ with OpenAI-only)

## 🔧 **Environment Variables**

The system uses these environment variables:

```bash
# Ollama Configuration
OLLAMA_ENDPOINT=https://api.ollama.ai/v1  # or http://localhost:11434
OLLAMA_API_KEY=your_ollama_cloud_key
OLLAMA_MODEL=llama3

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini

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
