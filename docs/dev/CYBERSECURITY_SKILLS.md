# Cybersecurity Skills for PulsePlate

<!-- markdownlint-disable MD013 -->

734+ cybersecurity skills (approximate; see `tools/cybersecurity_skills/index.json`) from [anthropic-cybersecurity-skills](https://github.com/Katsiarynakavaleuskaya/anthropic-cybersecurity-skills) (agentskills.io format). Installed by default with PulsePlate Codex skills.

## Install

First-time setup (after clone):

```bash
git submodule update --init --recursive
scripts/install_codex_skills.sh
```

Skills are symlinked to `$CODEX_HOME/skills/` (or `~/.codex/skills/`).

## Update

To pull latest cybersecurity skills:

```bash
git submodule update --remote tools/cybersecurity_skills
scripts/install_codex_skills.sh
```

## PulsePlate-relevant subdomains

| Subdomain | Skills | Use case |
|-----------|--------|----------|
| api-security | 28 | API auth, BOLA, OWASP, JWT |
| web-application-security | 42 | XSS, XXE, injection, OWASP |
| devsecops | 17 | semgrep, gitleaks, CI pipeline |
| container-security | 30 | Trivy, Falco, Kubernetes |
| vulnerability-management | 25 | CVSS, patch workflow |

## Routing

- **security-auditor** gets access to all ~734 skills (approximate; see index.json) when routed (see `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`)
- **Cursor:** `.cursor/rules/cybersecurity-skills-index.md` provides index and triggers
- **Codex:** Skills installed to `$CODEX_HOME/skills/`; available to all agents

## Index

Full skill list: `tools/cybersecurity_skills/index.json`

Skill structure: `tools/cybersecurity_skills/skills/{skill-name}/SKILL.md`

## References

- [tools/codex_skills/README.md](../../tools/codex_skills/README.md) — install overview
- [AGENT_SKILL_ROUTING_POLICY.md](../orchestration/AGENT_SKILL_ROUTING_POLICY.md) — skill routing
- [agentskills.io](https://agentskills.io) — skill format standard
