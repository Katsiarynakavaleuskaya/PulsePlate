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
pytest==9.1.1
pytest-cov==7.1.0
...
```

**`requirements-all.txt`** - All dependencies (prod + dev)
```bash
-r requirements.txt  # Includes production deps
pytest>=9.1.1      # Dev tools with minimum versions
...
```

**`constraints.txt`** - Minimum and bounded versions for reproducible dev resolution
```bash
pytest>=9.1.1
black>=26.5.0
...
```

## 🚀 Installation

### Production Environment
```bash
python scripts/ci/install_locked_python_requirements.py \
  --requirements-profile runtime \
  --requirements-file requirements.txt \
  --constraints-file constraints.txt
```

### Development Environment (with locked dev requirements and constraints)
```bash
python scripts/ci/install_locked_python_requirements.py \
  --requirements-profile runtime-dev \
  --requirements-file requirements.txt \
  --dev-requirements-file requirements-dev.txt \
  --constraints-file constraints.txt
```

### All Dependencies (flexible versions)
```bash
PIP_INDEX_URL="${PULSEPLATE_PYTHON_INDEX_URL:?approved private package proxy required}" \
  python -m pip install -r requirements-all.txt -c constraints.txt
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
export PIP_INDEX_URL="${PULSEPLATE_PYTHON_INDEX_URL:?approved private package proxy required}"
export PIP_TRUSTED_HOST="${PULSEPLATE_PYTHON_TRUSTED_HOST:-}"
pip-compile --allow-unsafe --no-emit-index-url --output-file=requirements.txt requirements.in
pip-compile --allow-unsafe --no-emit-index-url --output-file=requirements-rag-vector.txt requirements-rag-vector.in
pip-compile --allow-unsafe --no-emit-index-url --constraint=requirements.txt --output-file=requirements-dev.txt requirements-dev.in
pip-compile --allow-unsafe --no-emit-index-url --output-file=requirements-lock.txt requirements-dev.in requirements.in
```

### Update Dev Dependency
1. Update version in `requirements-dev.txt`
2. Update constraint in `constraints.txt` (if needed)
3. Run `python verify_requirements.py`
4. Test through the approved proxy:
   `python scripts/ci/install_locked_python_requirements.py --requirements-profile runtime-dev --constraints-file constraints.txt --preflight-only`

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
python scripts/ci/install_locked_python_requirements.py \
  --requirements-profile runtime-dev \
  --constraints-file constraints.txt

# Install for production
python scripts/ci/install_locked_python_requirements.py \
  --requirements-profile runtime \
  --constraints-file constraints.txt

# Verify consistency
python verify_requirements.py

# Update all to latest (within constraints)
PIP_INDEX_URL="${PULSEPLATE_PYTHON_INDEX_URL:?approved private package proxy required}" \
  python -m pip install -U -r requirements-all.txt -c constraints.txt
```

## 🔗 References

- [pip Requirements Files](https://pip.pypa.io/en/stable/reference/requirements-file-format/)
- [pip Constraints Files](https://pip.pypa.io/en/stable/user_guide/#constraints-files)
- [Python Packaging User Guide](https://packaging.python.org/)
