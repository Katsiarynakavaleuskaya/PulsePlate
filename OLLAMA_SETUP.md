# 🦙 Ollama Setup Guide

## Overview

This guide shows how to set up AI for the PulsePlate application using our **Smart AI Router**. You can choose between:

- **Hybrid Approach** (Recommended): Ollama + OpenAI with smart routing
- **Local Ollama**: For development and testing (free, requires local setup)
- **Ollama Cloud**: For production (budget-friendly, managed service)
- **Hugging Face**: For embeddings and specialized models (free tier available)
- **OpenAI Only**: High quality but expensive

Our Smart AI Router automatically chooses the best provider based on query complexity, saving **~90% on AI costs** while maintaining quality.

## Prerequisites

- Docker installed and running
- GitHub repository with CI/CD workflows
- Choose your setup:
  - **Local**: Ollama installed locally
  - **Cloud**: Ollama Cloud account (recommended for production)

## Setup Options

### Option 1: Hybrid Approach (Recommended)

**Best of both worlds:**

- ✅ **85% cost savings** vs OpenAI-only
- ✅ **High quality** for complex queries
- ✅ **Free** for simple queries
- ✅ **Automatic routing** based on complexity
- ✅ **Fallback protection** if one provider fails

**Setup:**

1. Get OpenAI API key (for complex queries)
2. Get Ollama Cloud API key (for simple queries)
3. Use our Smart AI Router

```bash
# Hybrid configuration
OLLAMA_ENDPOINT=https://ollama.com
OLLAMA_API_KEY=your_ollama_cloud_key
OPENAI_API_KEY=your_openai_key
AI_ROUTER_ENABLED=true
```

**Cost Example:**

- 1000 simple queries → Ollama (free)
- 100 complex queries → OpenAI ($6)
- **Total: $6/month** vs $60/month with OpenAI-only

### Option 2: Ollama Cloud (Production Only)

**Advantages:**

- ✅ No server management
- ✅ Budget-friendly pricing
- ✅ Automatic scaling
- ✅ Always up-to-date models
- ✅ Global CDN

**Setup:**

1. Sign up at [Ollama Cloud](https://ollama.ai/cloud)
2. Get your API key
3. Use the cloud endpoint in your deployment

```bash
# Production configuration
OLLAMA_ENDPOINT=https://ollama.com
OLLAMA_API_KEY=your_api_key_here
```

**Pricing (as of 2025):**

- **Free tier**: Rate limits apply (see Ollama docs for hourly/daily limits)
- **Pro**: $20/month (pricing varies by usage)
- **Enterprise**: Custom pricing for high volume

### Cost Consideration

Cost-effective alternative to running your own GPU servers.

### Option 3: Local Ollama (For Development)

## Installation

### 1. Install Ollama

```bash
# macOS
brew install ollama

# Linux
# Download the install script
curl -fsSL -o ollama-install.sh https://ollama.ai/install.sh
# (Optional) Verify the script's checksum - see https://ollama.ai/install.sh for checksum info
# sha256sum ollama-install.sh
# Review the script before running:
less ollama-install.sh
# Run the script
sh ollama-install.sh

# Windows
# Download from https://ollama.ai/download
```

### 2. Start Ollama Service

```bash
# Start Ollama service
ollama serve

# In another terminal, pull a model
ollama pull llama2
```

### 3. Verify Installation

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Test with a simple request
curl http://localhost:11434/api/generate -d '{
  "model": "llama2",
  "prompt": "Hello, world!",
  "stream": false
}'
```

## Configuration

### Environment Variables

The PulsePlate application uses these environment variables to connect to Ollama:

```bash
# For staging
OLLAMA_ENDPOINT=http://host.docker.internal:11434
ENVIRONMENT=staging

# For production
OLLAMA_ENDPOINT=http://host.docker.internal:11434
ENVIRONMENT=production
```

### Docker Configuration

When running PulsePlate in Docker, use `host.docker.internal:11434` to connect to the host's Ollama service:

```bash
docker run -d \
  --name pulseplate-staging \
  -p 8000:8000 \
  -e OLLAMA_ENDPOINT=http://host.docker.internal:11434 \
  -e ENVIRONMENT=staging \
  ghcr.io/katsiarynakavaleuskaya/pulseplate:latest
```

## CI/CD Integration

### GitHub Actions

The CD workflow automatically:

1. **Staging**: Deploys to `localhost:8000` on every push to main
2. **Production**: Deploys to `localhost:8001` on version tags (v*)

### Workflow Triggers

```yaml
# Staging deployment (main branch)
on:
  workflow_run:
    workflows: ["Docker Build and Push"]
    types: [completed]
    branches: [main]

# Production deployment (version tags)
on:
  push:
    tags: ['v*']
```

### Health Checks

Both staging and production include comprehensive health checks:

- Container status verification
- Application health endpoint testing
- Automatic retry with exponential backoff
- Detailed logging for troubleshooting

## Usage

### Staging Environment

```bash
# Access staging
curl http://localhost:8000/health

# View logs
docker logs pulseplate-staging
```

### Production Environment

```bash
# Access production
curl http://localhost:8001/health

# View logs
docker logs pulseplate-production
```

### Model Management

```bash
# List available models
ollama list

# Pull a new model
ollama pull codellama

# Remove a model
ollama rm llama2
```

## Troubleshooting

### Common Issues

1. **Ollama not accessible from Docker**

   ```bash
   # Ensure Ollama is running on host
   ollama serve

   # Check if port 11434 is accessible
   curl http://localhost:11434/api/tags
   ```

2. **Container fails to start**

   ```bash
   # Check container logs
   docker logs pulseplate-staging

   # Verify image exists
   docker images | grep pulseplate
   ```

3. **Health check failures**

   ```bash
   # Check if application is responding
   curl -v http://localhost:8000/health

   # Verify environment variables
   docker exec pulseplate-staging env | grep OLLAMA
   ```

### Performance Tuning

```bash
# Increase Ollama memory limit
export OLLAMA_MAX_LOADED_MODELS=2
export OLLAMA_NUM_PARALLEL=2

# Restart Ollama with new settings
ollama serve
```

## Security Considerations

### 🔒 **Production Hardening Guide**

#### **Network Security**
- **Bind to localhost/private interfaces**: Ollama runs on localhost by default, but verify no external exposure
- **Firewall configuration**: Block unnecessary ports, allow only required traffic
- **Security groups/VPC**: Use private subnets, restrict access to authorized networks only
- **Reverse proxy**: Use Nginx/Traefik with authentication for any remote access
- **TLS encryption**: Enable HTTPS for all external connections, use valid certificates

#### **Authentication & Authorization**
- **API authentication**: Implement API keys, JWT tokens, or OAuth for Ollama API access
- **User isolation**: Run Ollama under dedicated, least-privilege user accounts
- **Access control**: Implement role-based access control (RBAC) for different user tiers
- **Session management**: Enforce session timeouts and secure session handling

#### **Runtime Isolation**
- **Containerization**: Use Docker with security profiles (AppArmor/SELinux)
- **Resource limits**: Set CPU, memory, and disk quotas to prevent resource exhaustion
- **Process isolation**: Use cgroups, namespaces, and seccomp profiles
- **File system**: Use read-only containers where possible, mount volumes with minimal permissions

#### **Data Protection**
- **Encryption at rest**: Encrypt model files and configuration data
- **Encryption in transit**: Use TLS 1.3 for all network communications
- **Secret management**: Store API keys and credentials in HashiCorp Vault, AWS Secrets Manager, or similar
- **Data classification**: Identify and protect sensitive data according to compliance requirements

#### **Integrity & Updates**
- **Signed artifacts**: Verify model checksums and use signed binaries
- **Regular updates**: Keep Ollama and models updated with security patches
- **Vulnerability scanning**: Regular security scans of containers and dependencies
- **Supply chain security**: Verify model sources and maintain software bill of materials (SBOM)

#### **Monitoring & Alerting**
- **Comprehensive logging**: Log all API calls, errors, and security events
- **Anomaly detection**: Monitor for unusual usage patterns or access attempts
- **Performance monitoring**: Track resource usage and response times
- **Security alerts**: Set up alerts for failed authentications, rate limit violations, and errors

#### **Rate Limiting & Abuse Prevention**
- **API rate limits**: Implement per-user and per-endpoint rate limiting
- **Resource quotas**: Limit concurrent requests and model loading
- **Input validation**: Sanitize and validate all inputs to prevent injection attacks
- **DDoS protection**: Use CDN and load balancer protections

#### **Backup & Recovery**
- **Model backups**: Regular backups of trained models and configurations
- **Disaster recovery**: Document and test recovery procedures
- **Data retention**: Implement proper data lifecycle management
- **Business continuity**: Plan for service availability during maintenance

#### **Compliance & Threat Modeling**
- **Threat modeling**: Identify potential attack vectors and mitigation strategies
- **Compliance requirements**: Ensure adherence to GDPR, HIPAA, SOC2, or other relevant standards
- **Security audits**: Regular third-party security assessments
- **Incident response**: Document and test incident response procedures

### ⚠️ **Default Security Posture**
- Ollama runs on localhost only by default (secure)
- No external network access required (good)
- All communication is local (secure)
- Models are stored locally (data sovereignty)

### Option 4: Hugging Face (For Embeddings & Specialized Models)

**Perfect for embeddings and specialized AI tasks:**

- ✅ **Free tier available** - 1000 requests/month
- ✅ **Best embedding models** - Llama Embed Nemotron 8B
- ✅ **No local setup** - Cloud-based API
- ✅ **Multilingual support** - Great for iOS apps
- ✅ **Specialized models** - Nutrition, health, fitness

**Setup:**

1. Create Hugging Face account at <https://huggingface.co>
2. Get API token from <https://huggingface.co/settings/tokens>
3. Install required libraries:

```bash
pip install transformers torch huggingface-hub
```

1. Configure environment:

```bash
# Hugging Face configuration
HUGGINGFACE_API_TOKEN=your_hf_token
HUGGINGFACE_MODEL=nvidia/llama-embed-nemotron-8b
```

**Cost Example:**

- Free tier: 1000 requests/month
- Pro plan: $9/month for 10,000 requests
- Enterprise: Custom pricing

**Best for:**

- Semantic search in recipes
- Product recommendations
- Multilingual content analysis
- Embedding generation for iOS app

## 🆕 Latest Updates

### Llama Embed Nemotron 8B (October 2025)

- **Top-ranked on MMTEB for multilingual embeddings** 🏆
- **Multilingual support** - Perfect for iOS apps with RU/EN/ES
- **Optimized for mobile** - 8B parameters, efficient for iOS
- **Semantic search** - Great for recipe/product recommendations
- **Free and open-source** - No licensing costs

**Consider upgrading to `llama-embed-nemotron:8b` for better multilingual embeddings in PulsePlate!**

## Next Steps

1. **Custom Models**: Train or fine-tune models for your specific use case
2. **Scaling**: Use Ollama with multiple GPUs for better performance
3. **Integration**: Connect with other AI services as needed
4. **Monitoring**: Set up logging and monitoring for production use
5. **🆕 Embedding Models**: Consider Llama Embed Nemotron 8B for semantic search
6. **🆕 Hugging Face**: Explore specialized models for nutrition and health

## Support

- [Ollama Documentation](https://ollama.ai/docs)
- [Ollama GitHub](https://github.com/ollama/ollama)
- [PulsePlate Issues](https://github.com/Katsiarynakavaleuskaya/PulsePlate/issues)
