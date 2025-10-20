# Open Food Facts API Migration Plan (v0 → v2)

Context: We currently use OFF v0 endpoints on the `.org` domain as a workaround for 504s observed on `.org` v2. See `core/food_apis/openfoodfacts_client.py` lines 105–110.

Goals:
- Migrate to `https://world.openfoodfacts.net/api/v2/` when `.org` v2 is healthy.
- Keep response parsing stable and bandwidth-efficient.

Action Items:
1. Add runtime health probes for `.org` v2 (implemented: `OFFClient.check_v2_org_health`).
2. Wire probe into periodic telemetry (scheduler or startup log) to track readiness.
3. Prepare parser adjustments for v2 response differences (field names, pagination, filters).

Relevant differences to validate:
- Pagination and `page_size` types/limits.
- Support for `fields` filtering (ensure minimal payloads).
- Consistent product JSON shapes (nutriments, categories, labels fields).

Rollout Plan:
- Behind a feature flag, switch search/details endpoints to v2 on `.net` or `.org` once healthy.
- Monitor error rates and latency; rollback flag on regressions.


