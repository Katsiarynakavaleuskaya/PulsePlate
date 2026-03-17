---
description: Index for 734+ cybersecurity skills (approximate; see tools/cybersecurity_skills/index.json) (agentskills.io). Use when security audit, vulnerability scan, threat model, API security, DevSecOps, or web app security tasks.
globs:
alwaysApply: false
---

# Cybersecurity Skills Index

**Source:** `tools/cybersecurity_skills/` (git submodule from [anthropic-cybersecurity-skills](https://github.com/Katsiarynakavaleuskaya/anthropic-cybersecurity-skills))

**When to use:** Security audit, vulnerability scan, threat modeling, API security review, DevSecOps, web application security, container security.

## PulsePlate-relevant subdomains

| Subdomain | Count | Example skills |
|-----------|-------|----------------|
| api-security | 28 | testing-api-for-broken-object-level-authorization, testing-oauth2-implementation-flaws |
| web-application-security | 42 | testing-for-xss-vulnerabilities, testing-for-json-web-token-vulnerabilities |
| devsecops | 17 | semgrep-custom-sast-rules, secret-scanning-with-gitleaks |
| container-security | 30 | trivy-image-scanning, falco-runtime-detection |
| vulnerability-management | 25 | cvss-scoring, patch-management-workflow |

## Full index

- **Location:** `tools/cybersecurity_skills/index.json`
- **Skills path:** `tools/cybersecurity_skills/skills/{skill-name}/SKILL.md`
- **Format:** agentskills.io (YAML frontmatter + workflow)

## Codex install

Skills are installed to `$CODEX_HOME/skills/` via `scripts/install_codex_skills.sh`. Run after clone:

```bash
git submodule update --init --recursive
scripts/install_codex_skills.sh
```
