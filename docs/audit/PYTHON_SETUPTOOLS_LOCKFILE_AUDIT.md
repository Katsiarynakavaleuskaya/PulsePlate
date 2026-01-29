# Audit: Setuptools Usage and Lock File Strategy (Python Ecosystem 2026)

**Date:** 2026-01-28
**Status:** Audit complete
**Trigger:** Article "Что творится с Python? Новый синтаксис отменили, скорость подросла слабо, а старый setuptools начал ломаться" (OnlyPython)
**Scope:** setuptools usage, setup.cfg deprecations, lock file strategy, Dependabot/uv alignment.

---

## Executive Summary

| Topic | Current state | Risk | Recommendation |
|-------|----------------|------|----------------|
| **Setuptools** | Used as pinned dependency in `requirements.in` (security); not used as build backend; no `setup.cfg` | Low | Keep current approach; no change required for setuptools 78.x deprecations |
| **Lock file** | pip-tools (`pip-compile`) → `requirements.txt` / `requirements-dev.txt`; `requirements-lock.txt` present | Low | Retain pip-tools; optionally evaluate PEP 751 (`pylock.toml`) when tooling stabilizes |
| **Dependabot** | `package-ecosystem: pip` only; no uv | Low | Optional: add uv later to benefit from Dependabot uv support |

**Conclusion:** No mandatory changes. Setuptools deprecations (e.g. hyphenated keys in `setup.cfg`) do not apply; lock strategy is valid. Optional follow-ups: evaluate standard lock file (PEP 751) and uv when ready.

---

## 1. Setuptools Usage

### 1.1 Where setuptools appears

- **`requirements.in`** (line 32–33):
  `setuptools>=78.1.1,<79.0.0`
  Comment: security pin for GHSA-58pv-8j8x-9vj2 (jaraco.context).
- **`requirements.txt`** (pip-compile output):
  `setuptools==78.1.1`
- **`requirements-dev.txt`**:
  `setuptools==78.1.1`
- **`.github/workflows/security.yml`** (line 95):
  `python -m pip install --upgrade pip setuptools wheel` (CI env setup).
- **`Dockerfile`**:
  - Production stage: `pip install -r requirements.txt` then **`pip uninstall -y setuptools wheel`** so they are not in the runtime image.
  - Dev stage: installs from `requirements-dev.txt` and does **not** uninstall setuptools (needed for some dev tooling).

### 1.2 What we do not use

- **No `setup.cfg`** in the repository → the setuptools 78.0.1 deprecation (hyphenated keys, e.g. `long-description` → `long_description`) does not affect this project.
- **No `setup.py`**.
- **No `[build-system]` in `pyproject.toml`** → we do not use setuptools (or any other backend) to build an installable package; the app is run as a directory (e.g. `uvicorn app.main:app`).

### 1.3 Article vs our setup

- **Article:** setuptools 78.0.1 removed support for hyphenated keys in `setup.cfg` (e.g. `long-description`).
- **Us:** We have no `setup.cfg`. Setuptools is only a pinned install-time dependency for security; we do not rely on setuptools for build or config.
- **Verdict:** No change required for setuptools deprecations. Keeping `setuptools>=78.1.1,<79.0.0` in `requirements.in` remains correct for the security fix.

### 1.4 Optional: build backend

If we later add a proper installable package (e.g. `pip install .`), the article suggests preferring **hatchling** or **pdm** over setuptools. Today we do not need a build backend; this is a note for future packaging only.

---

## 2. Lock File Strategy

### 2.1 Current approach

- **Canonical lock files:**
  - **Production:** `requirements.txt` (generated from `requirements.in` via `pip-compile`).
  - **Dev:** `requirements-dev.txt` (from `requirements-dev.in`, with constraint from `requirements.txt`).
- **Additional artifact:** `requirements-lock.txt` (pip-compile of both `.in` files).
- **Process:** `REQUIREMENTS.md` describes using `pip-compile --allow-unsafe` to regenerate lock files; Dependabot opens PRs against `requirements.txt` (and related files as configured).

So we **do** use a lock-file strategy: pinned, reproducible installs via pip-tools.

### 2.2 PEP 751 (standard lock file)

- **Article:** PEP 751 defines a standard lock file format (`pylock.toml`) for reproducible builds.
- **Us:** We use pip-tools’ `requirements.txt` as our lock format, not `pylock.toml`.
- **Verdict:** No immediate change. When tools (pip, uv, etc.) widely support PEP 751 and migration path is clear, we can consider evaluating a move to `pylock.toml` in a dedicated change (see backlog).

### 2.3 Summary

| Question | Answer |
|----------|--------|
| Do we use a lock file? | Yes: `requirements.txt` (and dev lock) from pip-compile. |
| Do we use PEP 751 `pylock.toml`? | No. |
| Is that a problem? | No; current approach is valid and reproducible. |

---

## 3. Dependabot and uv

### 3.1 Current Dependabot config

- **`.github/dependabot.yml`:**
  - `package-ecosystem: "pip"`
  - Directory: `/`
  - Grouped updates (security, production, testing, quality, dev-tools).
  - No uv ecosystem configured.

### 3.2 Article

- Dependabot now supports **uv** (lock files and dependency management).
- **Us:** We use pip + pip-tools, not uv.
- **Verdict:** Optional improvement. If we later adopt uv for installs/lock, we can add a Dependabot config for uv in the same repo (see backlog).

---

## 4. Recommendations

### 4.1 No immediate changes

1. **Setuptools:** Keep `setuptools>=78.1.1,<79.0.0` in `requirements.in`. Do not add `setup.cfg` with hyphenated keys.
2. **Lock file:** Keep pip-tools and `requirements.txt` / `requirements-dev.txt` as the canonical lock.
3. **Dependabot:** Keep current `pip` configuration.

### 4.2 Optional follow-ups (backlog)

1. **PEP 751 / standard lock file**
   When tooling (pip/uv) and CI support PEP 751 (`pylock.toml`) and migration is documented, evaluate switching to a standard lock file (separate PR, optional).

2. **uv + Dependabot**
   If we introduce uv for dependency management, add Dependabot updates for uv (e.g. lock file and dependency groups) and document in `REQUIREMENTS.md`.

3. **Build backend (only if we ship a package)**
   If we later add `[build-system]` for an installable package, prefer hatchling (or similar) over setuptools as recommended by the article.

---

## 5. Evidence (commands / locations)

- Setuptools in repo:
  `grep -rn setuptools requirements.in requirements.txt requirements-dev.txt .github/workflows/ Dockerfile`
  Output (sample):
  ```text
  requirements.in:32:setuptools>=78.1.1,<79.0.0
  requirements.txt:50:setuptools==78.1.1
  requirements-dev.txt:45:setuptools==78.1.1
  ```
- No setup.cfg:
  `ls -la setup.cfg 2>/dev/null` → not present.
- No build-system in pyproject:
  `grep -n build-system pyproject.toml` → no match.
- Lock process:
  `REQUIREMENTS.md` (pip-compile, verify_requirements.py).
- Dependabot:
  `.github/dependabot.yml` (package-ecosystem: pip).

---

## 6. References

- OnlyPython article (2026): PEP 736 rejected, Python 3.14 performance, setuptools 78 deprecations, PEP 751 lock file, Dependabot + uv.
- `REQUIREMENTS.md` — requirements and lock file workflow.
- `AGENTS.md` — Dockerfile policy (no pip version pin; security via requirements).

---

**Last updated:** 2026-01-28
**Maintainer:** @katsiaryna_kavaleuskaya
