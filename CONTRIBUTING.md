# Contributing Guidelines

This repo uses a simple branch model designed to keep `main` always green.

## Branching

- Long‑lived branch: `main` only.
- Create short‑lived branches for work:
  - `feature/<topic>` for new features
  - `fix/<issue>` for bug fixes
  - `chore/<task>` for maintenance
- Avoid direct pushes to `main`. Open a PR.

## Pull Requests

- Keep PRs small and focused. Prefer squash merge.
- Ensure CI is green:
  - Tests pass on Python 3.13.5
  - Coverage ≥ 96% (repo currently ~99%)
- Run locally before pushing:

```bash
# Standard tests
pytest -q --maxfail=1 --disable-warnings \
  --cov=. --cov-report=term-missing --cov-fail-under=97

# Docker tests (if Docker files changed)
make docker-build
docker run -d --rm --name test -p 8000:8000 pulseplate:latest
sleep 2  # Allow container to start
curl -f http://localhost:8000/health || (docker stop test; exit 1)  # Verify health check
```

## Auto‑delete merged branches

- Merged PR branches are deleted automatically.
- A workflow (`.github/workflows/auto-delete-branches.yml`) removes the
  head branch when a PR is merged in this repository.

## Coding

- Follow existing style. Keep changes minimal and scoped.
- Prefer tests that isolate external services by mocking.
- Don't lower coverage thresholds; add tests instead.
- **Code Quality Tools**: Sourcery code quality checks are handled by a GitHub App integration, so Sourcery is not installed locally via `requirements-all.txt`. Code quality suggestions from Sourcery appear as GitHub PR comments.
- **Premium endpoints policy / Политика премиальных эндпойнтов**:
  - Every new premium/admin FastAPI route **must** include the shared API key guard (e.g. `Depends(_get_api_key_dynamic)` or `require_premium_key`).
  - Перед добавлением нового платного эндпойнта убедитесь, что он подключает dependency для проверки ключа и что есть тест, подтверждающий 403/401 без ключа.

### Docstring Convention / Конвенция документации

The project uses bilingual docstrings (Russian and English) for better accessibility:

- **Format**: Start with a brief English summary, then add `RU:` and `EN:` sections
- **Pattern**:
  ```python
  """Brief English summary.

  RU: Краткое описание на русском языке.
  EN: More detailed English explanation (not just repeating the summary).
  """
  ```
- **Guidelines**:
  - First line: Concise English summary
  - `RU:` section: Russian explanation (can be more detailed)
  - `EN:` section: Detailed English explanation (should add value beyond the summary, not duplicate it)
  - Avoid duplication between the summary line and the `EN:` section
- **Example**:
  ```python
  def _atomic_write_json(target_path: Path, data: Mapping[str, Any]) -> None:
      """Atomically write JSON to target_path.

      RU: Атомарная запись JSON в файл: во временный файл в той же директории,
      затем os.replace(). Гарантирует целостность при сбоях.
      EN: Writes JSON data atomically by first writing to a temporary file in the same
      directory, then using os.replace() to ensure atomicity and data integrity on failures.
      """
  ```

## Commit Messages

- Use conventional style where possible:
  - `feat: ...`, `fix: ...`, `chore: ...`, `docs: ...`, `tests: ...`
- One logical change per commit.

## Security & Quality

- Non‑blocking scanners run in CI (Bandit, CodeQL).
- Address warnings when practical; don’t block urgent fixes.

### Dependency Security Policy (Safety)

- Policy file: `safety-policy.toml` at the repository root. It defines allow‑lists/ignores (currently none) and ensures a single source of truth for Safety configuration.
- Severity threshold: builds and PRs are blocked on findings of severity **high** or **critical**.
- CI enforcement: the Security workflow runs Safety against `requirements.txt` using the shared policy file and fails the job with a non‑zero exit code when high/critical vulnerabilities are present. This blocks merges.
- Local usage:
  - English / EN:
    ```bash
    pip install safety==2.3.5
    safety check --policy-file safety-policy.toml \
      --severity high,critical \
      --full-report -r requirements.txt
    ```
  - Русский / RU:
    ```bash
    pip install safety==2.3.5
    safety check --policy-file safety-policy.toml \
      --severity high,critical \
      --full-report -r requirements.txt
    ```
  - Notes / Примечания:
    - The repo policy currently has `ignore = []` (no ignored findings). Update via PR if a temporary waiver is justified.
    - Keep CI and local checks aligned by always using the same `safety-policy.toml` and severity filter.

## Medical Safety Approval Workflow

Medical safety thresholds and alerting features require explicit approval before production enablement.

### Overview

Medical safety constants (e.g., `MIN_SAFE_FLOOR_KCAL`, `MAX_SAFE_CEILING_KCAL`, `MIN_SAFE_DAILY_CALORIES`, `MAX_SAFE_DAILY_CALORIES`) must not be hardcoded in production code. They must be:

1. **Moved to configuration**: Stored in `config/medical_safety.yaml` (or environment-backed config module)
2. **Feature-flagged**: Gated by `featureFlags.medicalSafetyApproved` (or `MEDICAL_ALERTS_ENABLED`) that defaults to `false`
3. **Approved via workflow**: Require sign-offs from clinical/nutrition committee, legal, and product teams

### Required Sign-offs

Before enabling medical safety alerts/enforcements in production, the following approvals are required:

- **Clinical/Nutrition Committee**: Review and approve threshold values based on medical evidence
- **Legal**: Review compliance with Apple/Google guidelines and local regulations (e.g., HIPAA, GDPR)
- **Product**: Confirm product strategy and user experience implications

### Configuration Structure

Medical safety configuration should be stored in `config/medical_safety.yaml`:

```yaml
# Medical Safety Configuration
# DO NOT modify these values without approval from clinical/nutrition committee

featureFlags:
  medicalSafetyApproved: false  # Set to true only after approval workflow

thresholds:
  MIN_SAFE_FLOOR_KCAL: 1000.0
  MAX_SAFE_CEILING_KCAL: 4500.0
  MIN_SAFE_DAILY_CALORIES: 500
  MAX_SAFE_DAILY_CALORIES: 5000
```

### Implementation Requirements

1. **Runtime Configuration Loading**: Values must be loaded from `config/medical_safety.yaml` at runtime, not hardcoded
2. **Feature Flag Gating**: All medical alerting/enforcement logic must check `featureFlags.medicalSafetyApproved` before executing
3. **Fallback Behavior**: When feature flag is `false`, no alerts/enforcements should be triggered
4. **Unit Tests**: Add tests that verify:
   - Alerts only trigger when feature flag is enabled
   - Config values are read from configuration source (not hardcoded)
   - Behavior when flag is false (no alerts/enforcements)

### Approval Checklist

- [ ] Clinical/nutrition committee review completed
- [ ] Legal review completed
- [ ] Product review completed
- [ ] Configuration file (`config/medical_safety.yaml`) created with approved values
- [ ] Feature flag implementation completed
- [ ] Unit tests added and passing
- [ ] Integration tests verify flag gating behavior
- [ ] Documentation updated (this section, code comments)

### Testing Requirements

Unit tests must assert:

1. **Flag disabled**: No alerts/enforcements when `featureFlags.medicalSafetyApproved = false`
2. **Flag enabled**: Alerts/enforcements trigger when `featureFlags.medicalSafetyApproved = true`
3. **Config loading**: Values are read from `config/medical_safety.yaml`, not hardcoded constants
4. **Threshold application**: Approved config values are correctly applied when flag is enabled

See `docs/BAYESIAN_EXPANSION_STRATEGY.md` lines 1228-1234 and `docs/BAYESIAN_IMPLEMENTATION_PLAN.md` for recommended test scenarios.

## Getting Help

- Open a Draft PR early for feedback.
- Use the issue tracker for bugs and small enhancements.
