# MSW Mock Server for Premium API Endpoints

## Overview

This directory contains Mock Service Worker (MSW) handlers for PulsePlate's premium API endpoints:

- `/api/v1/premium/bmr` - BMR/TDEE calculations
- `/api/v1/premium/plate` - Plate portions and meal planning
- `/api/v1/premium/targets` - WHO-based nutrition targets

## Error Simulation

### Using the X-Mock-Error Header

To simulate server errors in tests, include the `X-Mock-Error` header in your request:

```typescript
fetch('/api/v1/premium/bmr', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Mock-Error': 'server_error'  // Triggers 500 response
  },
  body: JSON.stringify({
    weight_kg: 70,
    height_cm: 170,
    age: 30,
    sex: 'male',
    activity: 'moderate'
  })
});
```

### Why Header-Based Error Simulation?

**Previous approach (deprecated):** Magic numeric values in request body:

- `weight_kg: 999` → 500 error on BMR endpoint
- `age: 999` → 500 error on Plate endpoint
- `height_cm: 999` → 500 error on Targets endpoint

**Problems with magic numbers:**

- Could collide with valid test data (edge cases, stress tests)
- Not explicit - hard to understand intent
- Required different magic values per endpoint
- Made test data less realistic

**Benefits of header-based approach:**

- Explicit error triggering - clear test intent
- No collision with valid test data
- Consistent across all endpoints
- Request body remains realistic

## Validation Errors (400 responses)

Each endpoint validates request parameters and returns 400 Bad Request for invalid inputs:

### BMR Endpoint

- `weight_kg`: Required, must be > 0
- `height_cm`: Required, must be > 0
- `age`: Required, 0-120
- `sex`: Required, 'male' or 'female'
- `activity`: Required, one of: sedentary, light, moderate, active, very_active
- `bodyfat`: Optional, 0-60

### Plate Endpoint

- `sex`: Required, 'male' or 'female'
- `age`: Required, 10-100
- `height_cm`: Required, must be > 0
- `weight_kg`: Required, must be > 0
- `activity`: Required, one of: sedentary, light, moderate, active, very_active
- `goal`: Required, 'loss', 'maintain', or 'gain'
- `deficit_pct`: Optional, 5-25
- `surplus_pct`: Optional, 5-20
- `bodyfat`: Optional, 3-60

### Targets Endpoint

- `sex`: Required, 'male' or 'female'
- `age`: Required, 1-120
- `height_cm`: Required, must be > 0
- `weight_kg`: Required, must be > 0
- `activity`: Required, one of: sedentary, light, moderate, active, very_active
- `goal`: Optional, 'loss', 'maintain', or 'gain'
- `deficit_pct`: Optional, 5-25
- `surplus_pct`: Optional, 5-20
- `bodyfat`: Optional, 3-60
- `life_stage`: Optional, one of: child, teen, adult, pregnant, lactating, elderly

## Example Usage in Tests

### Setup in Tests

```typescript
import { server } from './test/msw/server';
import { beforeAll, afterAll, afterEach } from 'vitest';

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'bypass' });
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
```

### Example: Testing Successful Requests (200 OK)

```typescript
it('should return BMR data for valid request', async () => {
  const response = await fetch('https://api.test/api/v1/premium/bmr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      weight_kg: 70,
      height_cm: 170,
      age: 30,
      sex: 'male',
      activity: 'moderate',
    }),
  });

  expect(response.status).toBe(200);
  const data = await response.json();
  expect(data).toHaveProperty('bmr');
  expect(data).toHaveProperty('tdee');
});
```

### Example: Testing Validation Errors (400 Bad Request)

```typescript
it('should return 400 for invalid weight', async () => {
  const response = await fetch('https://api.test/api/v1/premium/bmr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      weight_kg: -10,  // Invalid: negative weight
      height_cm: 170,
      age: 30,
      sex: 'male',
      activity: 'moderate',
    }),
  });

  expect(response.status).toBe(400);
  const data = await response.json();
  expect(data).toHaveProperty('error');
  expect(data.error).toContain('weight_kg');
});
```

### Example: Testing Server Errors (500 Internal Server Error)

```typescript
it('should return 500 when X-Mock-Error header is set', async () => {
  const response = await fetch('https://api.test/api/v1/premium/bmr', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Mock-Error': 'server_error',  // Trigger 500 error
    },
    body: JSON.stringify({
      weight_kg: 70,   // Valid data, but server error triggered by header
      height_cm: 170,
      age: 30,
      sex: 'male',
      activity: 'moderate',
    }),
  });

  expect(response.status).toBe(500);
  const data = await response.json();
  expect(data).toHaveProperty('error');
  expect(data.error).toBe('Internal server error');
});
```

## Migration Guide

If you have existing tests using magic numbers for error simulation:

### Before (deprecated)

```typescript
const response = await fetch('/api/v1/premium/bmr', {
  method: 'POST',
  body: JSON.stringify({
    weight_kg: 999,  // Magic number to trigger error
    height_cm: 170,
    age: 30,
    sex: 'male',
    activity: 'moderate'
  })
});
```

### After (recommended)

```typescript
const response = await fetch('/api/v1/premium/bmr', {
  method: 'POST',
  headers: {
    'X-Mock-Error': 'server_error'  // Explicit error trigger
  },
  body: JSON.stringify({
    weight_kg: 70,   // Realistic test data
    height_cm: 170,
    age: 30,
    sex: 'male',
    activity: 'moderate'
  })
});
```

## Architecture Decision

**Date:** October 10, 2025
**Decision:** Use request headers for mock error simulation
**Rationale:**

1. Eliminates collision risk with valid test data
2. Makes test intent explicit and readable
3. Allows realistic request bodies in error scenarios
4. Consistent pattern across all endpoints
5. Follows testing best practices (explicit over implicit)

**Related:** PR #133 final checks
