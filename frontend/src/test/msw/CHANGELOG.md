# MSW Server Changelog

## [2025-10-10] - Header-Based Error Simulation

### Changed

**Replaced magic number error simulation with header-based approach**

All three premium API endpoint handlers now use the `X-Mock-Error` request header to trigger server errors instead of checking for magic numeric values in the request body.

#### Updated Endpoints

1. `/api/v1/premium/bmr` (BMR/TDEE calculations)
2. `/api/v1/premium/plate` (Plate portions and meal planning)
3. `/api/v1/premium/targets` (WHO-based nutrition targets)

#### Before

```typescript
// Magic numbers in request body
if (req.weight_kg === 999) { return 500 }  // BMR endpoint
if (req.age === 999) { return 500 }        // Plate endpoint
if (req.height_cm === 999) { return 500 }  // Targets endpoint
```

#### After

```typescript
// Header-based error simulation (consistent across all endpoints)
const mockErrorHeader = request.headers.get('X-Mock-Error');
if (mockErrorHeader === 'server_error') {
  return HttpResponse.json(
    { error: 'Internal server error' },
    { status: 500 }
  );
}
```

### Rationale

**Problems with magic numbers:**

- Could collide with valid test data (edge cases, stress tests)
- Not explicit - hard to understand test intent
- Required different magic values per endpoint (inconsistent)
- Made test data less realistic
- Violated separation of concerns (data mixing with control flow)

**Benefits of header-based approach:**

- **Explicit**: Clear test intent - `X-Mock-Error: server_error` is self-documenting
- **No collisions**: Request body can contain any valid data including edge cases
- **Consistent**: Same pattern across all endpoints
- **Realistic**: Test data remains realistic and representative
- **Best practice**: Headers are the standard way to pass metadata in HTTP

### Migration Guide

If you have existing tests using magic numbers:

#### Before (deprecated)

```typescript
// Different magic number per endpoint
fetch('/api/v1/premium/bmr', {
  body: JSON.stringify({ weight_kg: 999, ... })  // Magic number
});

fetch('/api/v1/premium/plate', {
  body: JSON.stringify({ age: 999, ... })  // Different magic number
});

fetch('/api/v1/premium/targets', {
  body: JSON.stringify({ height_cm: 999, ... })  // Yet another magic number
});
```

#### After (recommended)

```typescript
// Consistent header across all endpoints
fetch('/api/v1/premium/bmr', {
  headers: { 'X-Mock-Error': 'server_error' },  // Explicit
  body: JSON.stringify({ weight_kg: 70, ... })  // Realistic data
});

fetch('/api/v1/premium/plate', {
  headers: { 'X-Mock-Error': 'server_error' },  // Same header
  body: JSON.stringify({ age: 30, ... })        // Realistic data
});

fetch('/api/v1/premium/targets', {
  headers: { 'X-Mock-Error': 'server_error' },  // Same header
  body: JSON.stringify({ height_cm: 170, ... }) // Realistic data
});
```

### Implementation Details

**Lines changed:**

- `server.ts:171-176` - BMR endpoint error check
- `server.ts:218-223` - Plate endpoint error check (line numbers before change)
- `server.ts:319-324` - Targets endpoint error check (line numbers before change)

**Header check location:**

- Moved error check to top of handler (before JSON parsing)
- Fails fast if error simulation header is present
- Consistent placement across all three handlers

**Error response:**

```json
{
  "error": "Internal server error"
}
```

Status: 500

### Documentation

Added comprehensive documentation:

- `README.md` - Updated with header-based approach documentation
- Code examples for all three error scenarios (200, 400, 500)
- Migration guide for existing tests
- Architecture decision record

### Testing

No existing tests were affected by this change:

- MSW server is currently not imported by any test files
- No tests were using the old magic number approach
- Change is fully backward compatible for new implementations

### Related

- Pull Request: #133 (final checks)
- Date: October 10, 2025
- Author: Cursor AI (VibeCoding Specialist)
- Reviewer: TBD
