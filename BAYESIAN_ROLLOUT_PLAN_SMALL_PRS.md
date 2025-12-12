# Bayesian Integration Rollout Plan (Small PRs)

**Epic**: Issue #286
**Original PR**: #266 (closed - too large, 368 files)
**Strategy**: Break into **small PRs (~20 files max)** for easier review and CI

---

## ✅ Completed PRs (3/10 from original plan)

### PR #287 - CI/CD Infrastructure (PR 1/10) ✅ MERGED
- Config files update
- `.bandit.yaml` standardization
- Coverage configuration

### PR #293 - Database Models (PR 2/10) ✅ MERGED
- Recipe model with nutrition data
- Foundation for Bayesian tracking

### PR #294 - Core Bayesian Modules (PR 3/10) ✅ MERGED
- 7 analyzer modules (~200KB)
- 16 test files
- Business router API endpoint

---

## 🔄 In Progress / Partially Done

### Business Analyzers & API
- ✅ `app/routers/business.py` - API endpoint exists
- ✅ Business analyzer tests (16 files)
- ✅ `/api/v1/business/analyze` endpoint working
- ❓ **Need to verify**: All business features complete?

---

## 📋 Remaining Work - Broken into Small PRs

### Phase 4: Enhanced Nutrition Features (Split into 3 small PRs)

#### PR 4.1: Nutrition Core Utilities (~15 files, 2 days)
**Files to add/modify:**
- `core/nutrition_utils.py` - Helper functions
- `core/nutrition_validators.py` - Input validation
- `core/meal_types.py` - Meal type definitions
- `core/portion_calculator.py` - Portion size logic
- Tests: `tests/test_nutrition_utils.py` (~8 test files)

**Acceptance Criteria:**
- [ ] Nutrition calculation helpers work
- [ ] Validators handle edge cases
- [ ] 97%+ test coverage
- [ ] CI passes

#### PR 4.2: Meal Planning Engine (~18 files, 3 days)
**Files to add/modify:**
- `core/meal_planner.py` - Core planning logic
- `core/meal_optimizer.py` - Optimize meal combinations
- `core/dietary_constraints.py` - Diet filters (vegan, keto, etc.)
- `core/calorie_distributor.py` - Distribute calories across meals
- Tests: `tests/test_meal_planner.py` (~10 test files)

**Acceptance Criteria:**
- [ ] Generate meal plans based on targets
- [ ] Support dietary restrictions
- [ ] Optimize for macro balance
- [ ] 97%+ test coverage

#### PR 4.3: Nutrition API Endpoints (~12 files, 2 days)
**Files to add/modify:**
- `app/routers/nutrition.py` - REST endpoints
- `app/schemas/nutrition.py` - Request/response models
- Tests: `tests/test_nutrition_api.py` (~6 test files)

**Acceptance Criteria:**
- [ ] POST `/api/v1/nutrition/plan` endpoint
- [ ] GET `/api/v1/nutrition/recipes` endpoint
- [ ] Swagger docs generated
- [ ] Integration tests pass

---

### Phase 5: Business Features Verification (~10 files, 1 day)

#### PR 5.1: Business Analyzer Audit
**Tasks:**
- [ ] Review existing business analyzer code
- [ ] Verify all features from PR #266 are present
- [ ] Add missing business logic (if any)
- [ ] Update documentation

**Files to review/modify:**
- `app/routers/business.py`
- `core/business_bayesian_analyzer.py`
- Tests: Verify 16 test files cover all cases

---

### Phase 6: API Integration Completion (~15 files, 2 days)

#### PR 6.1: Additional Bayesian Endpoints (~15 files)
**Files to add:**
- `app/routers/bayesian.py` - Bayesian analysis endpoints
- `app/routers/recommendations.py` - Recommendation API
- `app/schemas/bayesian.py` - Request/response models
- Tests: `tests/test_bayesian_api.py` (~8 files)

**Endpoints to add:**
- POST `/api/v1/bayesian/analyze` - Generic test analysis
- GET `/api/v1/bayesian/recommendations` - Get recommendations
- POST `/api/v1/bayesian/feedback` - Submit feedback

---

### Phase 7: Database Migrations (Split into 2 small PRs)

#### PR 7.1: Recipe & Nutrition Migrations (~8 files, 1 day)
**Files to add:**
- `alembic/versions/001_add_recipe_model.py`
- `alembic/versions/002_add_nutrition_fields.py`
- Tests: Migration tests

**Tasks:**
- [ ] Create Alembic migrations for Recipe model
- [ ] Add nutrition tracking tables
- [ ] Test upgrade/downgrade
- [ ] Verify data integrity

#### PR 7.2: Bayesian Analysis Migrations (~7 files, 1 day)
**Files to add:**
- `alembic/versions/003_add_bayesian_results.py`
- `alembic/versions/004_add_test_metrics.py`
- Tests: Migration tests

**Tasks:**
- [ ] Create tables for Bayesian analysis results
- [ ] Add test quality metrics tables
- [ ] Test migrations on staging

---

### Phase 8: Documentation (Split into 3 small PRs)

#### PR 8.1: API Documentation (~12 files, 1 day)
**Files to add/modify:**
- `docs/api/NUTRITION_API.md`
- `docs/api/BUSINESS_ANALYZER_API.md`
- `docs/api/BAYESIAN_API.md`
- OpenAPI spec updates

#### PR 8.2: User Guides (~10 files, 1 day)
**Files to add:**
- `docs/guides/MEAL_PLANNING.md`
- `docs/guides/BUSINESS_ANALYSIS.md`
- `docs/guides/TEST_QUALITY.md`
- Example code snippets

#### PR 8.3: Developer Docs (~8 files, 1 day)
**Files to add/modify:**
- `docs/dev/BAYESIAN_ARCHITECTURE.md`
- `docs/dev/CONTRIBUTING_BAYESIAN.md`
- Architecture diagrams

---

### Phase 9: Remaining Tests (~20 files, 2 days)

#### PR 9.1: Integration Tests (~20 files)
**Files to add:**
- `tests/integration/test_nutrition_flow.py`
- `tests/integration/test_business_flow.py`
- `tests/integration/test_bayesian_pipeline.py`
- E2E tests (~15 files)

**Coverage targets:**
- [ ] Nutrition planning end-to-end
- [ ] Business analysis workflow
- [ ] Multi-module integration
- [ ] 97%+ overall coverage maintained

---

### Phase 10: Config & Cleanup (Split into 2 small PRs)

#### PR 10.1: Configuration Updates (~10 files, 1 day)
**Files to modify:**
- `pyproject.toml` - Add Bayesian metadata
- `.env.example` - Document new env vars
- `requirements.txt` - Verify dependencies
- CI config updates (if needed)

#### PR 10.2: Code Cleanup (~10 files, 1 day)
**Tasks:**
- [ ] Remove temporary code/comments
- [ ] Remove deprecated functions
- [ ] Optimize imports
- [ ] Final lint/format pass

---

## Summary

**Total Remaining PRs**: 14 small PRs (vs 7 large PRs in original plan)

### By Phase:
- **Phase 4** (Nutrition): 3 PRs (~45 files)
- **Phase 5** (Business): 1 PR (~10 files)
- **Phase 6** (API): 1 PR (~15 files)
- **Phase 7** (Migrations): 2 PRs (~15 files)
- **Phase 8** (Docs): 3 PRs (~30 files)
- **Phase 9** (Tests): 1 PR (~20 files)
- **Phase 10** (Cleanup): 2 PRs (~20 files)

**Estimated Timeline**:
- Optimistic: 14-18 days
- Realistic: 3-4 weeks (with reviews)

**Advantages of small PRs**:
- ✅ Easier code review
- ✅ Faster CI runs (<180 files each)
- ✅ Lower merge conflict risk
- ✅ Can parallelize some PRs
- ✅ Easier to rollback if issues

---

## Next Steps

1. **Immediate**: Start PR 4.1 (Nutrition Core Utilities)
2. **Parallel**: Audit PR 5.1 (Business features verification)
3. **Week 1**: Complete Phase 4 (Nutrition)
4. **Week 2**: Phases 5-7 (Business, API, Migrations)
5. **Week 3**: Phases 8-9 (Docs, Tests)
6. **Week 4**: Phase 10 (Cleanup) + Buffer

---

## Notes

- Each PR should be **<20 files** or **<180 files total** (CI limit)
- Maintain **97% coverage** in every PR
- Run full test suite locally before creating PR
- Use Dependabot for dependency updates (separate from feature work)
- Update this plan as we discover new requirements
