# 🦙 Ollama Setup Guide

## Overview

This guide shows how to set up AI for the PulsePlate application using our **Smart AI Router**. You can choose between:

- **Hybrid Approach** (Recommended): Ollama + OpenAI with smart routing
- **Local Ollama**: For development and testing (free, requires local setup)
- **Ollama Cloud**: For production (budget-friendly, managed service)
- **OpenAI Only**: High quality but expensive

Our Smart AI Router automatically chooses the best provider based on query complexity, saving **~85% on AI costs** while maintaining quality.

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

- **Free tier**: 1,000 requests/month
- **Pro**: $20/month (pricing varies by usage)
- **Enterprise**: Custom pricing for high volume

*Much cheaper than running your own GPU servers!*

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

- Ollama runs on localhost only by default
- No external network access required
- All communication is local
- Models are stored locally

## Next Steps

1. **Custom Models**: Train or fine-tune models for your specific use case
2. **Scaling**: Use Ollama with multiple GPUs for better performance
3. **Integration**: Connect with other AI services as needed
4. **Monitoring**: Set up logging and monitoring for production use

## Support

- [Ollama Documentation](https://ollama.ai/docs)
- [Ollama GitHub](https://github.com/ollama/ollama)
- [PulsePlate Issues](https://github.com/Katsiarynakavaleuskaya/PulsePlate/issues)
