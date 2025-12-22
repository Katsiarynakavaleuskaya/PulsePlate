# Security Guidelines

## API Key Management

### Encryption

PulsePlate uses **Fernet symmetric encryption** (from `cryptography` library) to secure API keys at rest.

### How it works

1. **Encryption Key**: A 256-bit (32-byte) Fernet key stored in `~/.cursor/.key` (Fernet uses AES-128 internally) with `600` permissions (owner read/write only)
2. **API Keys**: Stored encrypted in the `.env` file with `encrypted:` prefix
3. **Runtime**: Keys are decrypted on-the-fly when needed
4. **Git**: Both `.key` and `.env` files are in `.gitignore` - never committed

### Usage

#### Update API Key (Encrypted)

```bash
python update_api_key.py
```

The script will:

- Prompt for your OpenAI API key
- Ask if you want encryption (default: Yes)
- Encrypt and store the key
- Update configuration files

#### Read Encrypted Keys (in code)

```python
from secure_config import get_api_key_from_env

# Automatically decrypts if needed
api_key = get_api_key_from_env("OPENAI_API_KEY")
```

### Installation

```bash
pip install cryptography
```

### Fallback

If `cryptography` is not installed, the system gracefully falls back to plain text storage with warnings.

## Security Best Practices

### Development

- ✅ Use encryption for local API keys
- ✅ Never commit `.env` or `.key` files
- ✅ Use `600` permissions for sensitive files
- ✅ Rotate keys regularly

### Production

For production deployments, use dedicated secret management:

- **AWS**: AWS Secrets Manager or Systems Manager Parameter Store
- **Azure**: Azure Key Vault
- **GCP**: Google Cloud Secret Manager
- **HashiCorp**: Vault
- **Kubernetes**: Sealed Secrets or External Secrets Operator

## Files

- `update_api_key.py` - CLI tool for secure key management
- `secure_config.py` - Helper functions for encryption/decryption
- `~/.cursor/.key` - Encryption key (generated automatically, gitignored)
- `~/.cursor/.env` - Encrypted API keys (gitignored)

## CodeQL Compliance

This implementation addresses CodeQL alert **py/clear-text-storage-sensitive-data**:

- ✅ Sensitive data encrypted at rest
- ✅ Encryption keys stored separately
- ✅ Proper file permissions
- ✅ Graceful fallback with warnings
- ✅ Documentation and security guidelines

## Threat Model

### Protected Against

- ✅ Accidental git commits (gitignore)
- ✅ File system access by other users (file permissions)
- ✅ Plain text storage of secrets (encryption)
- ✅ Key exposure in logs (keys never logged)

### Not Protected Against

- ❌ Root/admin access to file system
- ❌ Memory dumps during runtime
- ❌ Compromised Python environment
- ❌ Physical access to machine

### Adherence Endpoint Posture (SEC-001)

- Current posture: adherence endpoints derive user identity from authenticated API keys and reject
  payload-supplied `user_id` fields to prevent horizontal privilege escalation.
- Planned remediation: add per-API-key rate limiting, suspicious-request logging/alerting, and full
  user authentication mapping by 2025-10-15.

For these threats, use hardware security modules (HSM) or cloud-based secret management.

## License

This security implementation is part of PulsePlate and follows the same license.
