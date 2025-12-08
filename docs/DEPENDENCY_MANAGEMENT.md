# Dependency Management with pip-tools

This project uses `pip-tools` to manage dependencies with deterministic builds.

## Files

- `requirements.in` - Production dependencies (high-level)
- `requirements-dev.in` - Development dependencies (high-level)
- `requirements.txt` - Compiled production dependencies with exact versions (auto-generated)
- `requirements-dev.txt` - Compiled development dependencies with exact versions (auto-generated)

## Installation

```bash
# Install pip-tools
pip install pip-tools

# Install production dependencies
pip-sync requirements.txt

# Install development dependencies
pip-sync requirements-dev.txt
```

## Updating Dependencies

### Update all dependencies to latest compatible versions:
```bash
# Update production dependencies
pip-compile requirements.in --upgrade -o requirements.txt

# Update development dependencies
pip-compile requirements-dev.in --upgrade -o requirements-dev.txt

# Install updated dependencies
pip-sync requirements-dev.txt
```

### Update a specific dependency:
```bash
# Update only fastapi
pip-compile requirements.in --upgrade-package fastapi -o requirements.txt
pip-sync requirements.txt
```

### Add a new dependency:
```bash
# Add to requirements.in or requirements-dev.in
echo "new-package>=1.0.0" >> requirements.in

# Recompile
pip-compile requirements.in -o requirements.txt
pip-sync requirements.txt
```

## CI/CD Integration

The GitHub Actions workflows should use:
```yaml
- name: Install dependencies
  run: |
    pip install pip-tools
    pip-sync requirements-dev.txt
```

## Dependabot Configuration

Dependabot is configured to:
- Run monthly (instead of weekly)
- Create max 5 PRs at a time
- Group related dependencies together (production, testing, quality, security)

See `.github/dependabot.yml` for details.
