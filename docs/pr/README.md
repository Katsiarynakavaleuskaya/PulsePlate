# PR Documentation

This directory contains all PR-related documentation, including:

- **PR review checklist** (`PR_REVIEW_CHECKLIST.md`) — quick scope analysis to detect PR bloat
- **Audit reports** (`*_AUDIT*.md`)
- **Questionnaires** (`*_QUESTIONNAIRE*.md`)
- **Implementation plans** (`*_PLAN*.md`, `*_IMPLEMENTATION*.md`)
- **Commit decisions** (`*_COMMIT_*.md`)
- **PR descriptions** (`*_DESCRIPTION*.md`)
- **Review responses** (`*_REVIEW*.md`)

## Organization

Files are named with the PR number prefix (e.g., `PR_456_*`, `PR_457_*`) for easy identification.

## Recent PRs

- **PR-456:** BMI Route Ownership & Legacy Migration
  - `PR_456_ROUTE_OWNERSHIP_AUDIT.md` - Route ownership audit
  - `PR_456_AUDIT_REPORT.md` - Pre-PR-457 audit report
  - `PR_456_QUESTIONS_ANSWERS.md` - Q&A document

- **PR-457:** Legacy BMI Helpers Cleanup
  - `PR_457_AUDIT_QUESTIONNAIRE.md` - Pre-implementation audit questionnaire

## Finding Documents

To find a specific PR document:
```bash
# List all PR documents
ls docs/pr/PR_<number>_*

# Search for specific content
grep -r "keyword" docs/pr/
```
