# Pseudonymous Data Compliance Implementation

## Overview

This document describes the implementation of privacy and security controls for pseudonymous request identifiers (client fingerprints) in the PulsePlate application.

## Implementation Summary

### 1. Privacy Policy Updates

**Location**: `app.py` - `/privacy` endpoint

The privacy policy now explicitly discloses:

- Collection of pseudonymous request identifiers (hashed and truncated IP addresses)
- Purpose of collection (security monitoring, request correlation, abuse prevention)
- Retention period (configurable, default 30 days)
- Data classification (Pseudonymous data per GDPR Article 4(5))
- Automatic deletion policy
- GDPR compliance statement

### 2. Data Classification and Labeling

**Location**: `core/log_retention.py`, `app.py` - logging middleware

Logs containing client fingerprints are now:

- Classified as `PSEUDONYMOUS` data
- Labeled with `[data_class=PSEUDONYMOUS]` in log entries
- Subject to shorter retention periods than public logs

**Classification Labels**:

- `PSEUDONYMOUS`: Contains pseudonymous identifiers (client fingerprints)
- `PUBLIC`: No sensitive data
- `SENSITIVE`: Contains sensitive data

### 3. Data Retention Policy

**Location**: `core/log_retention.py`

**Features**:

- Configurable retention periods via environment variables:
  - `LOG_PSEUDONYMOUS_RETENTION_DAYS` (default: 30 days)
  - `LOG_PUBLIC_RETENTION_DAYS` (default: 90 days)
  - `LOG_SENSITIVE_RETENTION_DAYS` (default: 90 days)
- Automatic deletion of expired logs based on file modification time
- Classification-aware retention (pseudonymous logs have shorter TTL)

**Cleanup Endpoint**: `POST /admin/logs/cleanup`

- Requires API key authentication
- Can filter by data classification
- Returns count of deleted files

### 4. Access Restrictions and Audit Logging

**Location**: `core/log_retention.py` - `LogRetentionManager` class

**Access Controls**:

- Log cleanup endpoint requires API key authentication
- Access to logs containing pseudonymous data is restricted to authorized personnel

**Audit Logging**:

- All access to logs containing pseudonymous/sensitive data is logged
- Audit log includes:
  - Action (READ, DELETE, etc.)
  - Log file path
  - Data classification
  - Reason for access
  - Timestamp (UTC)
  - Requester identifier (if available)

**Audit Log Format**:

```text
LOG_ACCESS_AUDIT: action=READ path=/logs/app.log classification=PSEUDONYMOUS reason=Read access timestamp=2025-01-15T10:30:00
```

### 5. Secure Salt Storage and Rotation

**Location**: `core/fingerprint_security.py`

**Secure Storage**:

- Salt is retrieved from environment variable `CLIENT_FINGERPRINT_SALT`
- Supports encrypted storage (using `secure_config` module)
- Validates salt is set in production (raises error if missing)
- Generates warning in development if salt is not set

**Salt Rotation**:

- Function `rotate_salt()` generates new salt
- Function `generate_new_salt()` creates cryptographically secure salt (32 bytes)
- Documentation: `docs/FINGERPRINT_SALT_ROTATION.md`

**Rotation Plan**:

- Detailed procedure for rotating salt
- Impact analysis (fingerprints cannot be correlated across rotation)
- Emergency rotation procedures
- Recommended rotation schedule (90-180 days for production)
- Compliance notes (GDPR, HIPAA)

## Configuration

### Environment Variables

```bash
# Fingerprint salt (required in production)
CLIENT_FINGERPRINT_SALT=<salt_value>  # or encrypted:...

# Log retention periods (days)
LOG_PSEUDONYMOUS_RETENTION_DAYS=30
LOG_PUBLIC_RETENTION_DAYS=90
LOG_SENSITIVE_RETENTION_DAYS=90

# Log directory
LOG_DIR=logs
```

### Programmatic Usage

```python
from core.log_retention import get_retention_manager, DATA_CLASS_PSEUDONYMOUS
from core.fingerprint_security import compute_fingerprint, get_fingerprint_salt

# Get retention manager
retention_manager = get_retention_manager()

# Cleanup expired logs
deleted_count = retention_manager.cleanup_expired_logs(data_class=DATA_CLASS_PSEUDONYMOUS)

# Compute fingerprint
fingerprint = compute_fingerprint("192.168.1.1")

# Get salt (for rotation)
salt = get_fingerprint_salt()
```

## Compliance Considerations

### GDPR (General Data Protection Regulation)

**Article 4(5) - Pseudonymisation**:

- Client fingerprints are pseudonymous data (cannot directly identify individuals)
- Still subject to GDPR requirements for data processing

**Article 5 - Principles**:

- ✅ **Minimization**: Only collects hashed IPs, not full IPs
- ✅ **Storage Limitation**: Short retention period (30 days default)
- ✅ **Accountability**: Audit logging of access

**Article 13/14 - Information to be provided**:

- ✅ Privacy policy explicitly discloses pseudonymous data collection
- ✅ Purpose and legal basis stated
- ✅ Retention period disclosed

**Article 30 - Records of processing activities**:

- Salt rotation must be documented
- Access to logs must be logged

### HIPAA (if applicable)

**Administrative Safeguards**:

- Salt rotation is a security control
- Access controls and audit logs meet requirements
- Documentation of security procedures

## Testing

### Manual Testing

1. **Check Privacy Policy**:

   ```bash
   curl http://localhost:8000/privacy | jq
   ```

2. **Verify Log Classification**:

   ```bash
   # Make a request
   curl http://localhost:8000/health

   # Check logs for classification label
   tail -f logs/app.log | grep "data_class"
   ```

3. **Test Log Cleanup**:

   ```bash
   # Cleanup expired pseudonymous logs
   curl -X POST http://localhost:8000/admin/logs/cleanup \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"data_class": "PSEUDONYMOUS"}'
   ```

### Automated Testing

Add tests to verify:

- Privacy policy includes pseudonymous data disclosure
- Logs are properly classified
- Retention policy is enforced
- Audit logging works correctly
- Salt rotation functions properly

## Monitoring and Maintenance

### Regular Tasks

1. **Review Audit Logs** (weekly):
   - Check for unauthorized access to pseudonymous logs
   - Verify cleanup operations are running

2. **Verify Retention Policy** (monthly):
   - Confirm expired logs are being deleted
   - Check retention periods are appropriate

3. **Salt Rotation** (every 90-180 days):
   - Follow procedure in `docs/FINGERPRINT_SALT_ROTATION.md`
   - Document rotation date
   - Verify new fingerprints are being generated

### Alerts

Set up alerts for:

- Salt not configured in production
- Unusual access patterns to log files
- Retention cleanup failures
- Salt rotation events

## Related Documentation

- `docs/FINGERPRINT_SALT_ROTATION.md`: Salt rotation procedures
- `SECURITY.md`: General security guidelines
- `core/log_retention.py`: Log retention implementation
- `core/fingerprint_security.py`: Fingerprint security implementation
- `secure_config.py`: Secure configuration management

## Contact

For questions about pseudonymous data compliance:

- Security Team: [security@example.com]
- Compliance Officer: [compliance@example.com]
- Privacy Officer: [privacy@example.com]
