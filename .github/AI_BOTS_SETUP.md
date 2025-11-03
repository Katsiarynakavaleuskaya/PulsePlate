# AI Code Review Bots Setup

This document describes the AI code review bots configured for the PulsePlate project and how to ensure they work on every PR.

## Configured Bots

### 1. CodeRabbit 🐰
**Status**: ✅ Configured (`.coderabbit.yaml`)
**Purpose**: Comprehensive code review with detailed analysis, sequence diagrams, and security checks
**GitHub App**: https://github.com/apps/coderabbitai

**Features**:
- Detailed code walkthroughs
- Sequence diagrams for complex changes
- Pre-merge checks (description quality, linked issues, scope analysis)
- Path-specific instructions for Python and TypeScript
- Health/nutrition domain focus

**Installation**:
1. Go to https://github.com/apps/coderabbitai
2. Click "Install" or "Configure"
3. Select the PulsePlate repository
4. Grant necessary permissions

### 2. Codecov 📊
**Status**: ✅ Configured (`codecov.yml`)
**Purpose**: Code coverage analysis and reporting
**GitHub App**: https://github.com/apps/codecov

**Features**:
- 97% coverage requirement enforcement
- Patch coverage analysis
- Line-by-line coverage reports
- Coverage badges and visualizations

**Installation**:
1. Go to https://github.com/apps/codecov
2. Click "Install" or "Configure"
3. Select the PulsePlate repository
4. Link with codecov.io account

### 3. Sourcery AI 🧙
**Status**: ✅ Configured (`.sourcery.yaml`)
**Purpose**: Code quality improvements and refactoring suggestions
**GitHub App**: https://github.com/apps/sourcery-ai

**Features**:
- Reviewer's guide generation
- Code quality metrics
- Refactoring suggestions
- Project-specific instructions

**Installation**:
1. Go to https://github.com/apps/sourcery-ai
2. Click "Install" or "Configure"
3. Select the PulsePlate repository
4. Configure dashboard settings at https://app.sourcery.ai

### 4. Codex by ChatGPT 💡
**Status**: ⚠️ Needs Installation
**Purpose**: AI-powered code review with OpenAI ChatGPT
**GitHub App**: https://github.com/apps/chatgpt-codex-connector

**Features**:
- AI-powered review comments
- Interactive code discussions
- Context-aware suggestions
- Priority-based feedback

**Installation**:
1. Go to https://github.com/apps/chatgpt-codex-connector
2. Click "Install" or "Configure"
3. Select the PulsePlate repository
4. Set up team settings

## Verification

To verify bots are working on your PRs:

1. **Create a test PR** with a small change
2. **Check for bot comments** within 1-5 minutes
3. **Look for these indicators**:
   - 🐰 CodeRabbit: Detailed walkthrough comment
   - 📊 Codecov: Coverage report comment
   - 🧙 Sourcery AI: Reviewer's guide comment
   - 💡 Codex: Review comment with priority badges

## Triggering Bots Manually

If bots don't auto-trigger, you can manually invoke them:

### CodeRabbit
```
@coderabbitai review
```

### Sourcery AI
```
@sourcery-ai review
```

### Codex
```
@codex review
```

## Configuration Files

All bot configurations are version controlled:

- `.coderabbit.yaml` - CodeRabbit settings
- `codecov.yml` - Codecov settings
- `.sourcery.yaml` - Sourcery AI settings
- `.github/workflows/codecov-upload.yml` - Codecov workflow

## Troubleshooting

### Bots Not Commenting

1. **Check App Installation**: Go to repository Settings → Integrations → GitHub Apps
2. **Verify Permissions**: Ensure apps have access to pull requests
3. **Check PR Filters**: Some bots skip draft PRs or specific branches
4. **Manual Trigger**: Use `@bot-name review` commands

### Coverage Bot Not Working

1. **Check Workflow**: Ensure `.github/workflows/codecov-upload.yml` runs
2. **Verify Token**: Codecov needs `CODECOV_TOKEN` secret
3. **Check Upload**: Look for "Upload coverage to Codecov" step in Actions

### Quality Issues

If bots give too many/few suggestions:

1. **Adjust CodeRabbit profile** in `.coderabbit.yaml` (chill/balanced/assertive)
2. **Update Sourcery rules** in `.sourcery.yaml`
3. **Configure per-path instructions** for specific files

## Best Practices

1. **Address Bot Feedback**: Review and respond to bot comments
2. **Use Commands**: Learn bot-specific commands for better interaction
3. **Update Configs**: Keep configuration files in sync with project needs
4. **Monitor Coverage**: Watch for coverage drops in Codecov reports
5. **Learn from Bots**: Use suggestions to improve code quality over time

## Support

- **CodeRabbit**: support@coderabbit.ai
- **Codecov**: support@codecov.io
- **Sourcery AI**: support@sourcery.ai
- **Codex**: Managed through ChatGPT Enterprise

## Notes for Copilot Agent

When you (GitHub Copilot Workspace Agent) create a PR:

1. ✅ All configured bots should auto-trigger
2. ✅ PR description is detailed enough for bot analysis
3. ✅ Coverage data is uploaded via GitHub Actions
4. ✅ Configuration files are up to date

If bots don't trigger automatically:
- The repository owner needs to install/configure the GitHub Apps
- Some bots may require team/organization plans
- Check repository Settings → Integrations → Applications
