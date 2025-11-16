# Fingerprint Salt Rotation Plan

## Overview

The client fingerprint salt is a critical security secret used to hash IP addresses into pseudonymous identifiers. This document outlines the procedure for rotating the salt without breaking compliance or losing the ability to audit historical logs.

## Security Considerations

### Why Rotate the Salt?

1. **Security Best Practice**: Regular rotation of cryptographic secrets reduces the impact of potential compromise
2. **Compliance**: Some regulations require periodic rotation of secrets
3. **Incident Response**: If the salt is suspected to be compromised, immediate rotation is required

### Impact of Rotation

⚠️ **IMPORTANT**: Rotating the salt will break correlation of fingerprints across the rotation event. Old fingerprints will no longer match new ones, even for the same IP address.

**Before Rotation:**
- IP `192.168.1.1` → Fingerprint `abc123def456` (with old salt)

**After Rotation:**
- IP `192.168.1.1` → Fingerprint `xyz789ghi012` (with new salt)

This means:
- Historical logs cannot be correlated with new requests using fingerprints alone
- If correlation is needed, you must use the original IP addresses (if available) or other identifiers
- Audit trails may need to be maintained separately for pre-rotation and post-rotation periods

## Rotation Procedure

### Step 1: Preparation

1. **Document Current State**:
   ```bash
   # Record the rotation date and time
   echo "Salt rotation scheduled for: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> salt_rotation_log.txt
   ```

2. **Backup Current Salt** (if stored in environment):
   ```bash
   # Export current salt (for reference only - do not store unencrypted)
   echo "Old salt (encrypted): $CLIENT_FINGERPRINT_SALT" >> salt_rotation_log.txt
   ```

3. **Notify Stakeholders**:
   - Security team
   - Compliance team
   - Operations team
   - Any systems that depend on fingerprint correlation

### Step 2: Generate New Salt

**Option A: Using Python Script**

```python
from core.fingerprint_security import generate_new_salt, rotate_salt

# Generate new salt
old_salt, new_salt = rotate_salt()

print(f"Old salt: {old_salt}")
print(f"New salt: {new_salt}")

# Encrypt the new salt (if using encryption)
from secure_config import encrypt_value
encrypted_salt = encrypt_value(new_salt)
print(f"Encrypted salt: {encrypted_salt}")
```

**Option B: Manual Generation**

```python
import secrets
salt_bytes = secrets.token_bytes(32)
new_salt = salt_bytes.hex()
print(f"New salt: {new_salt}")
```

### Step 3: Store New Salt Securely

#### Development/Staging

Update `.env` file:
```bash
# Encrypted format (recommended)
CLIENT_FINGERPRINT_SALT=encrypted:<encrypted_value>

# Or plain text (development only - NOT for production)
CLIENT_FINGERPRINT_SALT=<new_salt_value>
```

#### Production

Use a secrets manager:

**AWS Secrets Manager:**
```bash
aws secretsmanager update-secret \
  --secret-id pulseplate/fingerprint-salt \
  --secret-string "$new_salt"
```

**HashiCorp Vault:**
```bash
vault kv put secret/pulseplate fingerprint_salt="$new_salt"
```

**Kubernetes Secrets:**
```bash
kubectl create secret generic fingerprint-salt \
  --from-literal=salt="$new_salt" \
  --dry-run=client -o yaml | kubectl apply -f -
```

**GitHub Secrets (for CI/CD):**
```bash
# Via GitHub CLI
gh secret set CLIENT_FINGERPRINT_SALT --body "$new_salt"
```

### Step 4: Deploy New Salt

1. **Update Configuration**:
   - Update environment variables in your deployment platform
   - Update CI/CD pipeline secrets if applicable
   - Update infrastructure-as-code (Terraform, CloudFormation, etc.)

2. **Restart Application**:
   ```bash
   # The application will automatically pick up the new salt on restart
   systemctl restart pulseplate
   # or
   docker-compose restart pulseplate
   # or
   kubectl rollout restart deployment/pulseplate
   ```

3. **Verify**:
   ```bash
   # Check that new fingerprints are being generated
   curl -X GET http://localhost:8000/health
   # Check logs for new fingerprint format
   tail -f logs/app.log | grep "client="
   ```

### Step 5: Document Rotation

1. **Update Rotation Log**:
   ```bash
   echo "Salt rotated on: $(date -u +"%Y-%m-%d %H:%M:%S UTC")" >> salt_rotation_log.txt
   echo "New salt (encrypted): $CLIENT_FINGERPRINT_SALT" >> salt_rotation_log.txt
   ```

2. **Update Compliance Records**:
   - Document rotation in compliance tracking system
   - Update data processing records (GDPR Article 30)
   - Note the cutoff date for fingerprint correlation

3. **Archive Old Salt** (if required by policy):
   - Store encrypted old salt in secure archive
   - Set expiration date for archived salt
   - Document access controls for archived salt

## Emergency Rotation

If the salt is suspected to be compromised:

1. **Immediate Actions**:
   - Generate new salt immediately
   - Deploy new salt to all environments
   - Restart all application instances

2. **Incident Response**:
   - Document suspected compromise
   - Assess impact (what data may have been exposed)
   - Notify security team and compliance officer
   - Consider notifying affected users if required by regulations

3. **Post-Incident**:
   - Review access logs for salt storage
   - Review application logs for suspicious activity
   - Update security controls to prevent future compromise

## Rotation Schedule

### Recommended Schedule

- **Production**: Every 90-180 days (or per compliance requirements)
- **Staging**: Every 30-60 days (for testing rotation procedures)
- **Development**: As needed (can rotate frequently for testing)

### Calendar Reminders

Set calendar reminders:
- **90 days before rotation**: Plan rotation
- **30 days before rotation**: Prepare documentation
- **7 days before rotation**: Finalize rotation plan
- **Rotation day**: Execute rotation
- **Post-rotation**: Verify and document

## Compliance Notes

### GDPR

- Salt rotation does not affect user rights (fingerprints are pseudonymous, not personal data)
- Document rotation in data processing records (Article 30)
- Maintain audit trail of salt rotations

### HIPAA (if applicable)

- Salt rotation is a security control (Administrative Safeguards)
- Document rotation in security management process
- Maintain rotation logs for audit purposes

## Testing Rotation

Before rotating in production:

1. **Test in Development**:
   ```bash
   # Set test salt
   export CLIENT_FINGERPRINT_SALT="test_salt_old"

   # Generate fingerprints
   # ... make requests ...

   # Rotate salt
   export CLIENT_FINGERPRINT_SALT="test_salt_new"

   # Verify new fingerprints are different
   # ... make requests ...
   ```

2. **Test in Staging**:
   - Follow full rotation procedure
   - Verify application continues to function
   - Verify logs are properly classified
   - Verify retention policies still work

## Troubleshooting

### Issue: Application fails to start after rotation

**Solution**: Check that the salt is properly set in environment variables:
```bash
# Verify salt is set
echo $CLIENT_FINGERPRINT_SALT

# Check application logs
tail -f logs/app.log
```

### Issue: Cannot correlate old and new fingerprints

**Expected Behavior**: This is by design. Old and new fingerprints cannot be correlated after rotation.

**If Correlation is Required**:
- Use original IP addresses (if logged separately)
- Use other identifiers (session IDs, user IDs, etc.)
- Maintain separate audit trails for pre-rotation and post-rotation periods

## Related Documentation

- `core/fingerprint_security.py`: Salt management implementation
- `core/log_retention.py`: Log retention and classification
- `SECURITY.md`: General security guidelines
- `docs/PRIVACY_POLICY.md`: Privacy policy details

## Contact

For questions about salt rotation:
- Security Team: [security@example.com]
- Compliance Officer: [compliance@example.com]
- Operations: [ops@example.com]
