# 🐳 Docker Best Practices for PulsePlate

## 📋 **Quality Checklist**

### Before Every Push:
- [ ] Test Docker build locally: `make docker-build`
- [ ] Verify health check: `curl http://localhost:8000/health`
- [ ] Check image size: `docker images pulseplate`
- [ ] Clean old images: `make docker-clean-images`

### Weekly Maintenance:
- [ ] Review Docker images: `docker images pulseplate`
- [ ] Clean dangling images: `docker image prune -f`
- [ ] Update base images if needed
- [ ] Check for security vulnerabilities: `docker scan pulseplate:latest`

## 🚀 **Commands Reference**

### Build & Test:
```bash
# Build with versioning
make docker-build  # Creates :latest and :<commit-hash>

# Test locally
docker run -d --name pulseplate-test -p 8000:8000 pulseplate:latest
curl http://localhost:8000/health
docker stop pulseplate-test && docker rm pulseplate-test

# Build development version
make docker-build-dev
```

### Image Management:
```bash
# List all PulsePlate images
docker images pulseplate

# Clean old images (keeps latest 3)
make docker-clean-images

# Tag for production
docker tag pulseplate:latest pulseplate:v1.0.0

# Remove specific image
docker rmi pulseplate:old-tag
```

### Troubleshooting:
```bash
# Check container logs
docker logs <container-name>

# Inspect image layers
docker history pulseplate:latest

# Check image size breakdown
docker system df
```

## 🔧 **CI/CD Integration**

### GitHub Actions:
- ✅ All GitHub Actions pinned to specific commit SHAs
- ✅ Tag validation prevents workflow failures
- ✅ SBOM and Trivy security scanning enabled
- ✅ Multi-platform builds (linux/amd64, linux/arm64)

### Local Testing:
```bash
# Test the same way CI does
make docker-build
docker run -d --name test -p 8000:8000 pulseplate:latest
sleep 5 && curl -f http://localhost:8000/health
docker stop test && docker rm test
```

## 📊 **Performance Tips**

### Build Optimization:
- Use `.dockerignore` to exclude unnecessary files
- Leverage Docker layer caching
- Use multi-stage builds (already implemented)
- Pin base image versions

### Runtime Optimization:
- Use non-root user (already implemented)
- Set proper environment variables
- Configure health checks
- Use appropriate base images (python:3.12-slim)

## 🛡️ **Security Best Practices**

### Image Security:
- ✅ Non-root user (pulseplate)
- ✅ Minimal base image (python:3.12-slim)
- ✅ No secrets in image layers
- ✅ Regular security scanning with Trivy

### Runtime Security:
- ✅ Read-only filesystem where possible
- ✅ Proper file permissions
- ✅ Health checks for monitoring
- ✅ Resource limits in docker-compose

## 📈 **Monitoring & Maintenance**

### Regular Tasks:
1. **Daily**: Test builds before pushing
2. **Weekly**: Clean old images
3. **Monthly**: Review and update base images
4. **Quarterly**: Security audit and dependency updates

### Metrics to Track:
- Image size trends
- Build time performance
- Security vulnerability count
- Layer cache hit rate

---

**Remember**: Docker is a powerful tool, but with great power comes great responsibility! 🕷️
