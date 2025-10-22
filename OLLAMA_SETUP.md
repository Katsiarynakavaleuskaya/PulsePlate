# 🦙 Ollama Setup Guide

## Overview

This guide shows how to set up Ollama for local development and testing of the PulsePlate application. Ollama provides a local AI server that can be used for development, staging, and production environments.

## Prerequisites

- Docker installed and running
- Ollama installed locally
- GitHub repository with CI/CD workflows

## Installation

### 1. Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

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
OLLAMA_HOST=http://host.docker.internal:11434
ENVIRONMENT=staging

# For production
OLLAMA_HOST=http://host.docker.internal:11434
ENVIRONMENT=production
```

### Docker Configuration

When running PulsePlate in Docker, use `host.docker.internal:11434` to connect to the host's Ollama service:

```bash
docker run -d \
  --name pulseplate-staging \
  -p 8000:8000 \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
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
