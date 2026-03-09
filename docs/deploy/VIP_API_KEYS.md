# VIP API Key Configuration

## Overview

The VIP router now implements production-safe API key authentication with configurable anonymous access controls. This document describes the configuration options and their behavior.

## Configuration Variables

### Environment Detection

- **`ENVIRONMENT`**: Primary runtime environment identifier
  - Values: `production`, `staging`, `development`, `local`, `test`
  - Default: `local`
  - Used to determine if the application is running in production mode

- **`APP_ENV`**: Legacy fallback environment identifier
  - Values: `production`, `staging`, `development`, `local`, `test`
  - Used only when `ENVIRONMENT` is unset
  - **Rule:** `ENVIRONMENT` overrides `APP_ENV`

- **`DEBUG`**: Debug mode flag
  - Values: `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off`
  - Default: `true`
  - Helps opt unknown environments into production-like mode when the runtime env is not explicitly `development`, `local`, or `test`

### Anonymous Access Control

- **`ALLOW_ANONYMOUS_API_KEYS`**: Controls whether anonymous API key access is permitted
  - Values: `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off`
  - Default: `false`
  - When `false`, requests without API keys are rejected with 401 Unauthorized
  - **Hard rule:** must stay `false` in `production` / `staging`; startup now fails closed otherwise

- **`ALLOW_DEV_API_KEY`**: Legacy development mode flag
  - Values: `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off`
  - Default: `true`
  - Used only for explicit local/dev/test workflows
  - **Hard rule:** must stay `false` in `production` / `staging`; startup now fails closed otherwise

### API Key Configuration

- **`API_KEY`**: The expected API key value for authentication
  - When set, all requests must provide this exact key
  - When not set, the application falls back to anonymous access rules

## Behavior Matrix

| Environment | DEBUG | ALLOW_ANONYMOUS_API_KEYS | Behavior |
|-------------|-------|---------------------------|----------|
| `production` | `false` | `false` (default) | **Reject anonymous access** - 401 Unauthorized |
| `production` | `false` | `true` | **Startup error** - unsafe anonymous toggle rejected |
| `staging` | `false` | `false` (default) | **Reject anonymous access** - 401 Unauthorized |
| `staging` | `false` | `true` | **Startup error** - unsafe anonymous toggle rejected |
| `development` | `true` | `false` (default) | **Reject anonymous access** - 401 Unauthorized |
| `development` | `true` | `true` | **Allow anonymous access** - Log info |
| `local` | `true` | `false` (default) | **Reject anonymous access** - 401 Unauthorized |
| `local` | `true` | `true` | **Allow anonymous access** - Log info |
| `test` | `true` | `false` (default) | **Reject anonymous access** - 401 Unauthorized |
| `test` | `true` | `true` | **Allow anonymous access** - Log info |

## Production Safety

### Default Behavior

- **Production-like environments** reject anonymous access by default when `ENVIRONMENT` / `APP_ENV` are not explicitly `development`, `local`, or `test`
- **`DEBUG=false` alone is not enough** to override an explicit developer-like runtime label
- **Development environments** reject anonymous access by default and only allow it when `ALLOW_ANONYMOUS_API_KEYS=true`

### Security Features

1. **Fail-fast configuration**: Production/staging startup raises an explicit error if `ALLOW_ANONYMOUS_API_KEYS=true` or `ALLOW_DEV_API_KEY=true`
2. **Clear error messages**: Different error messages for production vs development contexts
3. **Comprehensive logging**: All authentication events are logged with appropriate severity levels
4. **Environment-aware defaults**: Safe defaults that prevent accidental exposure in production

## Logging

The VIP router logs all authentication events:

- **Error level**: Anonymous access attempts in production (when not explicitly allowed)
- **Warning level**: Anonymous access when explicitly allowed in production
- **Info level**: Anonymous access in development mode

Log messages include:

- Environment information
- Configuration flags
- Request context

## Examples

### Production Configuration (Recommended)

```bash
export ENVIRONMENT=production
export DEBUG=false
export API_KEY=your-secret-api-key
# ALLOW_ANONYMOUS_API_KEYS defaults to false
export ALLOW_DEV_API_KEY=false
```

### Development Configuration

```bash
export ENVIRONMENT=development
export DEBUG=true
export ALLOW_ANONYMOUS_API_KEYS=true
export ALLOW_DEV_API_KEY=true
```

### Staging Configuration (Strict)

```bash
export ENVIRONMENT=staging
export DEBUG=false
export API_KEY=your-staging-api-key
export ALLOW_ANONYMOUS_API_KEYS=false
export ALLOW_DEV_API_KEY=false
```

### Development Configuration (Restricted)

```bash
export ENVIRONMENT=development
export DEBUG=true
export ALLOW_ANONYMOUS_API_KEYS=false
export API_KEY=your-dev-api-key
export ALLOW_DEV_API_KEY=true
```

## Migration Guide

### From Previous Version

If you were previously relying on anonymous access in production:

1. **Set explicit API keys**:

   ```bash
   export API_KEY=your-production-api-key
   ```

2. **Keep fail-closed toggles disabled**:

   ```bash
   export ALLOW_ANONYMOUS_API_KEYS=false
   export ALLOW_DEV_API_KEY=false
   ```

3. **Restart and verify startup remains clean**:

   ```bash
   python -c "from settings import validate_api_key_toggle_guard; validate_api_key_toggle_guard()"
   ```

4. **Do not use `ALLOW_ANONYMOUS_API_KEYS=true` or `ALLOW_DEV_API_KEY=true` as a production workaround.**
   Configure a real `API_KEY` instead.

### Testing

To test the new authentication behavior:

```bash
# Test production mode rejection
export APP_ENV=production
export DEBUG=false
# No API_KEY set
curl -X POST http://localhost:8000/api/v1/vip/weekly-plan \
  -H "Content-Type: application/json" \
  -d '{"sex":"female","age":30,"height_cm":165,"weight_kg":60,"activity":"moderate","goal":"maintain"}'
# Expected: 401 Unauthorized

# Test with valid API key
export API_KEY=test-key
curl -X POST http://localhost:8000/api/v1/vip/weekly-plan \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key" \
  -d '{"sex":"female","age":30,"height_cm":165,"weight_kg":60,"activity":"moderate","goal":"maintain"}'
# Expected: 200 OK
```

## Security Considerations

1. **Never enable `ALLOW_ANONYMOUS_API_KEYS=true` or `ALLOW_DEV_API_KEY=true` in production/staging**
2. **Use strong API keys** in production environments
3. **Monitor authentication logs** for suspicious activity
4. **Rotate API keys regularly** in production
5. **Use environment-specific API keys** (different keys for dev/staging/production)

## Troubleshooting

### Common Issues

1. **401 Unauthorized in development**
   - Check if `ALLOW_ANONYMOUS_API_KEYS=true` is set for the anonymous flow you expect
   - Verify `ALLOW_DEV_API_KEY=true` for deterministic dev/test keys
   - Verify `APP_ENV` / `ENVIRONMENT` and `DEBUG` settings

2. **Anonymous access allowed in production**
   - Treat this as a misconfiguration, not a supported workaround
   - Remove `ALLOW_ANONYMOUS_API_KEYS=true` and `ALLOW_DEV_API_KEY=true`
   - Configure a real `API_KEY` and keep production/staging fail-closed

3. **Inconsistent behavior**
   - Ensure environment variables are set correctly
   - Check for conflicting configuration in multiple locations

### Debug Commands

```bash
# Check current configuration
echo "ENVIRONMENT: $ENVIRONMENT"
echo "APP_ENV: $APP_ENV"
echo "DEBUG: $DEBUG"
echo "ALLOW_ANONYMOUS_API_KEYS: $ALLOW_ANONYMOUS_API_KEYS"
echo "ALLOW_DEV_API_KEY: $ALLOW_DEV_API_KEY"
echo "API_KEY: ${API_KEY:+SET}"

# Test authentication endpoint
curl -v -X POST http://localhost:8000/api/v1/vip/weekly-plan \
  -H "Content-Type: application/json" \
  -d '{"sex":"female","age":30,"height_cm":165,"weight_kg":60,"activity":"moderate","goal":"maintain"}'
```
