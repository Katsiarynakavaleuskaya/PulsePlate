# Requirements Management Guide

## 📦 File Structure

### Production Dependencies

**`requirements.txt`** - Canonical source for production packages
- All production dependencies with exact versions
- Used in production deployments
- Updated by Dependabot

**`requirements-rag-vector.txt`** - Optional vector/ML runtime profile
- Exact versions for the opt-in RAG vector stack
- Installed only when a job or runtime explicitly selects the `rag-vector` profile

**`requirements-test.txt`** - Test-only dependency profile
- Keeps pytest/coverage tooling plus `pgvector` for postgres-vector contract tests
- Does not pull the heavy vector/ML runtime stack (`sentence-transformers`, `transformers`, `torch`)

### Development Dependencies

**`requirements-dev.txt`** - Development and testing tools
```bash
-r requirements.txt  # Includes all production deps
pytest==9.0.3
pytest-cov==7.0.0
...
```

**`requirements-all.txt`** - All dependencies (prod + dev)
```bash
-r requirements.txt  # Includes production deps
pytest>=8.3         # Dev tools with minimum versions
...
```

**`constraints.txt`** - Minimum and bounded versions for reproducible dev resolution
```bash
pytest>=9.0.3
black>=26.5.0
...
```

## 🚀 Installation

### Production Environment
```bash
pip install -r requirements.txt
```

### Development Environment (with locked dev requirements and constraints)
```bash
pip install -r requirements-dev.txt -c constraints.txt
```

### All Dependencies (flexible versions)
```bash
pip install -r requirements-all.txt
```

## ✅ Verification

Check consistency between requirements files:
```bash
python verify_requirements.py
```

This script ensures:
- `requirements-dev.txt` doesn't override `requirements.txt` versions
- `requirements-all.txt` uses `-r requirements.txt` (not duplicate pins)
- No version conflicts between files

## 🔄 Updating Dependencies

### Update Production Dependency
1. Dependabot creates PR with updated `requirements.txt`
2. Review and merge PR
3. Verify with `python verify_requirements.py`

### Regenerate lockfiles (pip-tools)

This repo uses `pip-compile` (pip-tools) to generate pinned `requirements*.txt`.
To avoid environment drift, run this with the pinned Python from `.python-version` / `.tool-versions`.

```bash
# Include setuptools/pip/wheel in lockfile for security fixes (--allow-unsafe)
pip-compile --allow-unsafe --output-file=requirements.txt requirements.in
pip-compile --allow-unsafe --output-file=requirements-rag-vector.txt requirements-rag-vector.in
pip-compile --allow-unsafe --constraint=requirements.txt --output-file=requirements-dev.txt requirements-dev.in
pip-compile --allow-unsafe --output-file=requirements-lock.txt requirements-dev.in requirements.in
```

### Update Dev Dependency
1. Update version in `requirements-dev.txt`
2. Update constraint in `constraints.txt` (if needed)
3. Run `python verify_requirements.py`
4. Test: `pip install -r requirements-dev.txt -c constraints.txt`

## 🛡️ Best Practices

1. **Single Source of Truth**: `requirements.txt` is canonical for production
2. **Use `-r` Reference**: Avoid duplicating pins in `requirements-all.txt`
3. **Constraints for Reproducibility**: Use `constraints.txt` for minimum/bounded dev versions
4. **Verify Before Commit**: Always run `verify_requirements.py`
5. **CI/CD**: GitHub Actions uses `requirements-dev.txt` for testing

## 📋 Common Commands

```bash
# Create/update virtualenv
python -m venv .venv
source .venv/bin/activate

# Install for development
pip install -r requirements-dev.txt -c constraints.txt

# Install for production
pip install -r requirements.txt

# Verify consistency
python verify_requirements.py

# Update all to latest (within constraints)
pip install -U -r requirements-all.txt -c constraints.txt
```

## 🔗 References

- [pip Requirements Files](https://pip.pypa.io/en/stable/reference/requirements-file-format/)
- [pip Constraints Files](https://pip.pypa.io/en/stable/user_guide/#constraints-files)
- [Python Packaging User Guide](https://packaging.python.org/)
