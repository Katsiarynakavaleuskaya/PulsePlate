# PulsePlate Copilot Instructions

## Project Overview

PulsePlate is a comprehensive FastAPI-based nutrition and meal planning application with BMI calculations, WHO-based nutrition targets, and VIP features for advanced meal planning. The project emphasizes high test coverage (97%+) and supports multiple languages (English, Russian, Spanish).

## Architecture & Key Components

### Core Structure
- **`app.py`** - Main FastAPI application with all endpoints and middleware
- **`app/routers/`** - Modular API routes (foods, recipes, vip, premium_week, bmi_pro)
- **`core/`** - Business logic modules (menu_engine, targets, plate, food_apis)
- **`tests/`** - Comprehensive test suite with 97% coverage requirement

### Feature Flag System
- **VIP Module**: `VIP_MODULE_ENABLED=true` enables advanced nutrition features
- **Feature Gates**: Various `FEATURE_*` env vars control endpoint availability
- Always check feature flags before implementing new premium features

### Database Pipeline
- **Food Sources**: USDA FoodData Central + Open Food Facts
- **Unified Database**: `core/food_apis/unified_db.py` merges data sources
- **Background Updates**: `core/food_apis/scheduler.py` handles automatic updates
- **Caching**: Smart caching with checksum validation in `update_manager.py`

## Development Workflow

### Testing Requirements
```bash
# Run tests with coverage enforcement
pytest --cov=. --cov-fail-under=97 -q

# Use the test task for convenience
python -m pytest tests --cov=. --cov-report=term-missing --cov-fail-under=97 -x
```

### Environment Setup
- **Python 3.13.5** (pinned in `.python-version`, `.tool-versions`)
- Install via: `pyenv install 3.13.5 && pyenv local 3.13.5`
- Dependencies: `pip install -r requirements-dev.txt -r requirements.txt`

### Code Standards
- **Black**: Line length 100 (`black . --line-length=100`)
- **Type Hints**: Required for all functions
- **Pydantic v2**: Use `model_dump()`, `model_validate()` syntax
- **Async/Await**: All endpoints are async for better concurrency

## Critical Patterns

### Error Handling & Fallbacks
```python
# Pattern: Graceful degradation for missing modules
try:
    from core.advanced_feature import some_function
except ImportError:
    some_function = None

# In endpoints, provide sensible fallbacks
if some_function is None:
    return stub_response()
```

### API Key Authentication
```python
# Premium endpoints require API key
@app.post("/api/v1/premium/endpoint", dependencies=[Depends(get_api_key)])
```

### Module Resolution for Tests
```python
# Pattern: Allow test patching via multiple module candidates
import sys as _sys
_candidates = [
    _sys.modules.get("app"),
    _sys.modules.get(__name__),
    _sys.modules.get("_app_top_module"),
]
_function = resolve_attr("function_name", fallback_function, _candidates)
```

## Testing Strategy

### Coverage Targets
- **Minimum**: 97% line coverage enforced in CI
- **Test Types**: Unit, integration, property-based (disabled), API smoke tests
- **Mocking**: Extensive use of pytest mocks for external dependencies

### Test File Patterns
- `test_*_coverage.py` - Coverage-focused tests
- `test_*_api.py` - API endpoint tests
- `test_*_smoke.py` - Basic functionality tests
- `disabled_hypothesis/` - Property-based tests (isolated due to performance)

### Common Test Utilities
```python
# Mock external dependencies
@patch("app.calculate_all_bmr", return_value={"mifflin": 1500})
@patch("core.menu_engine.make_weekly_menu")

# Use pytest fixtures from conftest.py
def test_endpoint(client, mock_auth):
```

## Development Commands

### Essential Make Commands
```bash
make dev          # Start dev server on :8001
make test         # Run tests quickly
make cov          # Coverage analysis
make lint         # Code quality checks
make fmt          # Auto-format code
make smoke-auto   # Test against running server
```

### Git Workflow
```bash
make feature NAME=my-feature  # Create feature branch
make auto-push               # Full checks + push (main branch)
make safe-push              # Conditional push based on branch
```

## Key Integration Points

### Food Database
- **Unified Access**: Always use `get_unified_food_db()` for food data
- **Update Pipeline**: Background scheduler updates data automatically
- **Regional Support**: Food availability varies by region (BY, RU, etc.)

### Nutrition Engine
- **WHO Standards**: `core/targets.py` implements WHO-based nutrition targets
- **Menu Generation**: `core/menu_engine.py` creates personalized meal plans
- **Auto-Repair**: VIP feature automatically fixes nutrient deficiencies

### I18n Support
- **Languages**: English, Russian, Spanish via `core/i18n.py`
- **Pattern**: `t(lang, "translation_key")` for all user-facing text
- **Locale-Aware**: BMI categories, meal names adapt to language/culture

## Common Gotchas

1. **Import Isolation**: Many modules use try/except imports for graceful degradation
2. **Feature Flags**: Always check environment variables before using premium features
3. **Test Mocking**: Complex module resolution allows extensive test patching
4. **Coverage Enforcement**: 97% threshold is strict - new code needs comprehensive tests
5. **Async Context**: All endpoints are async; use `await` for database/external calls

## Quick References

- **API Docs**: Start server and visit `/docs` for OpenAPI interface
- **Environment**: Check `.env.example` for configuration options
- **Database Schema**: See `core/food_db.py` for food data structure
- **Meal Planning**: `core/plate.py` implements visual nutrition planning
- **Spanish Support**: Full i18n implementation with cultural adaptations
