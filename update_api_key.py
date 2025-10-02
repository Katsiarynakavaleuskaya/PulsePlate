#!/usr/bin/env python3
"""PulsePlate API key management utilities.

This module provides a CLI and callable helpers for managing OpenAI API keys
with encryption, metadata tracking, and audit logging. It supports multiple
profiles (e.g. free vs premium), safe rotation with backups, batch updates,
optional keychain storage, and diagnostic health checks.

Business logic guarantees:
- Premium profile remains the default and continues to populate the historic
  `OPENAI_API_KEY` locations for MCP/runtime compatibility.
- Free profile values are stored alongside premium keys without changing the
  runtime behaviour for existing installations.
"""

from __future__ import annotations

import argparse
import json
import logging
import logging.handlers
import os
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from secure_config import ENCRYPTION_AVAILABLE, encrypt_value

try:  # Optional secret storage backends
    import keyring
except ImportError:  # pragma: no cover - optional dependency
    keyring = None

DEFAULT_PROFILE = "premium"
CURSOR_SUBDIR = ".cursor"
AUDIT_LOG_FILENAME = "api_key_audit.log"
METADATA_FILENAME = "key.meta.json"
DEFAULT_STALE_THRESHOLD_DAYS = 60
MAX_AUDIT_LOG_BYTES = 512 * 1024  # 512 KiB
AUDIT_LOG_BACKUPS = 3

PROFILE_CONFIG: Dict[str, Dict[str, object]] = {
    "premium": {
        "env_keys": ["OPENAI_API_KEY"],
        "settings_key": "cursor.ai.openaiApiKey",
        "mcp_env_key": "OPENAI_API_KEY",
        "description": "Paid/Premium key",
    },
    "free": {
        "env_keys": ["OPENAI_API_KEY_FREE"],
        "settings_key": "cursor.ai.openaiApiKeyFree",
        "mcp_env_key": "OPENAI_API_KEY_FREE",
        "description": "Public/free-tier key",
    },
}


def _is_valid_api_key(api_key: str) -> bool:
    """Return True when the provided API key satisfies length/prefix requirements."""

    return bool(api_key and api_key.startswith("sk-") and 20 <= len(api_key) <= 256)


@dataclass
class UpdateResult:
    """Result information for key updates."""

    profile: str
    encrypted_value: str
    plain_masked: str
    env_updates: List[Path]
    metadata_path: Optional[Path]
    stored_in_keychain: bool


def _cursor_home() -> Path:
    return Path.home() / CURSOR_SUBDIR


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _audit_logger() -> logging.Logger:
    logger = logging.getLogger("pulseplate.update_api_key")
    cursor_home = _cursor_home()

    if logger.handlers:
        needs_reset = False
        for handler in logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                current_target = Path(handler.baseFilename).parent
                if current_target != cursor_home:
                    needs_reset = True
                    break
            else:
                needs_reset = True
                break
        if not needs_reset:
            return logger
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:  # pragma: no cover - defensive
                pass

    logger.setLevel(logging.INFO)
    _ensure_directory(cursor_home)
    log_path = cursor_home / AUDIT_LOG_FILENAME

    handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=MAX_AUDIT_LOG_BYTES,
        backupCount=AUDIT_LOG_BACKUPS,
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    return logger


def _mask_secret(value: str) -> str:
    if not value:
        return "(empty)"
    return "***" if len(value) <= 8 else f"{value[:4]}...{value[-4:]}"


def _create_backup(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    backup_path = path.with_name(f"{path.name}.bak.{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def _verify_secure_permissions(path: Path) -> None:
    if not path.exists() or os.name == "nt":
        return
    current_mode = stat.S_IMODE(path.stat().st_mode)
    if current_mode != 0o600:
        _audit_logger().warning(
            "Insecure permissions detected on %s (mode %o). Expected 600.",
            path,
            current_mode,
        )


def _store_in_keychain(profile: str, api_key: str, encrypted: str) -> bool:
    storage_pref = os.getenv("PP_KEY_STORAGE", "file").lower()
    if storage_pref != "keychain":
        return False
    if keyring is None:
        _audit_logger().warning(
            "Keychain storage requested for profile %s but python-keyring is not installed. Fallback to file.",
            profile,
        )
        return False
    service = "PulsePlate/OpenAI"
    username = f"{profile}-api-key"
    try:
        keyring.set_password(service, username, encrypted)
        return True
    except Exception as exc:  # pragma: no cover - defensive
        _audit_logger().warning(
            "Failed to persist profile %s key in system keychain: %s", profile, str(exc)
        )
        return False


def _update_metadata(profile: str, api_key: str, source: str) -> Path:
    cursor_home = _cursor_home()
    _ensure_directory(cursor_home)
    meta_path = cursor_home / METADATA_FILENAME
    masked = _mask_secret(api_key)  # Always mask before any operation
    now = datetime.now(timezone.utc)

    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            meta = {}
    else:
        meta = {}

    profiles = meta.setdefault("profiles", {})
    profiles[profile] = {
        "last_updated": now.isoformat(),
        "masked_sample": masked,  # Only store masked value, never plain text
        "source": source,
    }
    meta["updated_at"] = now.isoformat()

    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True))
    return meta_path


def _warn_if_stale(threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS) -> None:
    meta_path = _cursor_home() / METADATA_FILENAME
    if not meta_path.exists():
        return
    try:
        data = json.loads(meta_path.read_text())
    except json.JSONDecodeError:
        return

    profiles = data.get("profiles", {})
    if not isinstance(profiles, dict):
        return

    now = datetime.now(timezone.utc)
    for profile, payload in profiles.items():
        last_updated = payload.get("last_updated")
        if not last_updated:
            continue
        try:
            timestamp = datetime.fromisoformat(last_updated)
        except ValueError:
            continue
        age = now - timestamp
        if age > timedelta(days=threshold_days):
            _audit_logger().warning(
                "API key profile '%s' is stale (%d days since last rotation).",
                profile,
                age.days,
            )


def _update_env_file(
    env_path: Path, key_names: Sequence[str], value: str, *, backup: bool, dry_run: bool
) -> Optional[Path]:
    if dry_run or not env_path.exists():
        return env_path if env_path.exists() else None

    if backup:
        _create_backup(env_path)

    with open(env_path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()

    # Remove all existing entries for each key in key_names to prevent duplicates
    key_set = set(key_names)
    filtered_lines = [
        line for line in lines if not any(line.strip().startswith(f"{key}=") for key in key_set)
    ]

    updated = False

    # Add new entries for each key
    for key in key_names:
        filtered_lines.append(f"{key}={value}")
        updated = True

    if updated:
        env_path.write_text("\n".join(filtered_lines) + "\n")
    _verify_secure_permissions(env_path)
    return env_path


def _update_mcp_config(
    mcp_path: Path, env_key: str, api_key: str, *, backup: bool, dry_run: bool
) -> Optional[Path]:
    if dry_run or not mcp_path.exists():
        return mcp_path if mcp_path.exists() else None

    if backup:
        _create_backup(mcp_path)

    try:
        with open(mcp_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode MCP config file '{mcp_path}': {e}")
        return None

    config.setdefault("mcpServers", {})
    config["mcpServers"].setdefault("pulseplate-chatgpt", {})
    config["mcpServers"]["pulseplate-chatgpt"].setdefault("env", {})
    config["mcpServers"]["pulseplate-chatgpt"]["env"][env_key] = api_key

    with open(mcp_path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)

    return mcp_path


def _update_settings(
    settings_path: Path, settings_key: str, api_key: str, *, backup: bool, dry_run: bool
) -> Optional[Path]:
    if dry_run or not settings_path.exists():
        return settings_path if settings_path.exists() else None

    if backup:
        _create_backup(settings_path)

    try:
        with open(settings_path, "r", encoding="utf-8") as handle:
            settings = json.load(handle)
    except json.JSONDecodeError:
        print(
            f"Warning: {settings_path} contains invalid JSON. Creating backup before overwriting."
        )
        backup_path = settings_path.with_suffix(f"{settings_path.suffix}.bak")
        import shutil

        shutil.copy2(settings_path, backup_path)
        settings = {}

    settings[settings_key] = api_key

    with open(settings_path, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)

    return settings_path


def _collect_jobs(
    api_key: Optional[str],
    profile: str,
    from_env: Optional[str],
    from_file: Optional[Path],
    *,
    source: str,
) -> List[Tuple[str, str, str]]:
    jobs: List[Tuple[str, str, str]] = []
    if api_key:
        jobs.append((profile, api_key, source))

    if from_env:
        if not (payload := os.getenv(from_env)):
            raise RuntimeError(f"Environment variable {from_env} is not set or empty")
        jobs.extend(_parse_bulk_payload(payload, default_profile=profile, source=f"env:{from_env}"))

    if from_file:
        jobs.extend(
            _parse_bulk_payload(
                Path(from_file).read_text(encoding="utf-8"),
                default_profile=profile,
                source=str(from_file),
            )
        )

    if not jobs:
        raise RuntimeError("No API keys supplied. Provide --api-key, --from-env, or --from-file.")

    return jobs


def _parse_bulk_payload(
    payload: str, *, default_profile: str, source: str
) -> List[Tuple[str, str, str]]:
    """Parse bulk payload for API keys. Supports both JSON array format and line-based profile:key format."""
    jobs: List[Tuple[str, str, str]] = []
    payload = payload.strip()

    if not payload:
        return jobs

    # Try JSON format first
    if payload.startswith("{") or payload.startswith("["):
        try:
            data = json.loads(payload)
            if isinstance(data, list):
                # JSON array format: [{"profile": "premium", "api_key": "sk-..."}, ...]
                for entry in data:
                    if not isinstance(entry, dict):
                        raise ValueError("Each entry in bulk payload must be a JSON object")
                    profile = entry.get("profile", default_profile)
                    api_key = entry.get("api_key")
                    if not api_key:
                        raise ValueError("Missing 'api_key' in bulk payload entry")
                    jobs.append((profile, api_key, source))
            elif isinstance(data, dict):
                # JSON object format: {"premium": "sk-...", "free": "sk-..."}
                for profile, api_key in data.items():
                    jobs.append((str(profile), str(api_key).strip(), source))
            else:
                raise ValueError("Bulk payload JSON must be an object or array")
            return jobs
        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, fall back to line-based parsing
            pass

    # Line-based format: "profile:key" or just "key" (uses default_profile)
    for raw_line in payload.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        delimiter = None
        for candidate in ("=", ":", ","):
            if candidate in line:
                delimiter = candidate
                break

        if delimiter:
            parts = line.split(delimiter, 1)
            if len(parts) == 2:
                prof, key = parts
                jobs.append((prof.strip(), key.strip(), source))
            else:
                raise ValueError(f"Invalid line format: {line}")
        else:
            # No delimiter found, treat as API key with default profile
            jobs.append((default_profile, line, source))

    return jobs


def _update_config_files(
    profile: str, api_key: str, encrypted_value: str, logger, *, backup: bool, dry_run: bool
) -> List[Path]:
    """Update all configuration files for the given profile.

    Note: api_key parameter is never logged directly to prevent clear-text logging
    of sensitive information. All logging uses only profile names and file paths.
    """
    cursor_home = _cursor_home()
    env_file = cursor_home / ".env"
    mcp_file = cursor_home / "mcp.json"
    settings_file = cursor_home / "settings.json"

    config = PROFILE_CONFIG[profile]
    touched: List[Path] = []

    if env_file.exists() and not dry_run:
        env_keys: Sequence[str] = config["env_keys"]  # type: ignore[assignment]
        updated_env = _update_env_file(
            env_file, env_keys, encrypted_value, backup=backup, dry_run=dry_run
        )
        if updated_env:
            touched.append(updated_env)
            logger.info("update.env profile=%s file=%s", profile, updated_env)
    elif dry_run:
        logger.info("update.env profile=%s dry_run_skipped file=%s", profile, env_file)
    else:
        logger.info("update.env profile=%s skipped_missing_file file=%s", profile, env_file)

    if mcp_file.exists():
        mcp_env_key: str = config["mcp_env_key"]  # type: ignore[assignment]
        updated_mcp = _update_mcp_config(
            mcp_file, mcp_env_key, api_key, backup=backup, dry_run=dry_run
        )
        if updated_mcp and not dry_run:
            touched.append(updated_mcp)
            logger.info("update.mcp profile=%s file=%s", profile, updated_mcp)

    if settings_file.exists():
        settings_key: str = config["settings_key"]  # type: ignore[assignment]
        updated_settings = _update_settings(
            settings_file, settings_key, api_key, backup=backup, dry_run=dry_run
        )
        if updated_settings and not dry_run:
            touched.append(updated_settings)
            logger.info("update.settings profile=%s file=%s", profile, updated_settings)

    return touched


def _log_and_fail(logger, log_message: str, *log_args, error_message: str = "") -> bool:
    """Log an error and print a user-friendly message, then return False."""
    logger.error(log_message, *log_args)
    print(error_message)
    return False


def _print_update_results(
    profile: str,
    touched: List[Path],
    metadata_path: Optional[Path],
    stored_keychain: bool,
    dry_run: bool,
) -> None:
    """Print the results of an API key update operation."""
    if dry_run:
        print(f"🔍 Dry run complete for profile '{profile}'. No files were modified.")
    else:
        print("🔐 API key will be stored encrypted in .env")
        if touched:
            print("✅ Updated:")
            for path in touched:
                print(f"  - {path}")
        if metadata_path:
            print(f"🗂️ Metadata recorded at {metadata_path}")
        if stored_keychain:
            print("🔑 Key also stored in system keychain (PP_KEY_STORAGE=keychain)")
        print("\n🎉 API key updated successfully!")
        print("\nNext steps:")
        print("1. Restart Cursor")
        print("2. Test MCP integration with Cmd+Shift+P → 'MCP: List Tools'")
        print("3. Verify ChatGPT tools are available")


def update_api_key(
    api_key: str,
    *,
    profile: str = DEFAULT_PROFILE,
    use_encryption: bool = True,
    dry_run: bool = False,
    backup: bool = True,
    source: str = "manual",
) -> bool:
    """Persist an API key for the given profile.

    Args:
        api_key: Plain text OpenAI API key (never logged in clear text).
        profile: Logical profile name ("premium" or "free").
        use_encryption: Whether to encrypt before writing to disk (recommended).
        dry_run: When True, validate flows but avoid writing to disk.
        backup: Create timestamped .bak copies of touched files.
        source: Descriptive label recorded in metadata/audit trail.

    Security:
        API keys are NEVER logged in clear text. All logging uses masked values only.
    """
    profile = profile.lower()
    if profile not in PROFILE_CONFIG:
        raise ValueError(
            f"Unsupported profile '{profile}'. Valid profiles: {', '.join(PROFILE_CONFIG)}"
        )

    logger = _audit_logger()
    # SECURITY: Mask the key immediately and use only masked value in logs
    masked = _mask_secret(api_key)
    logger.info("update.start profile=%s masked=%s dry_run=%s", profile, masked, dry_run)

    # Validate API key
    if not _is_valid_api_key(api_key):
        return _log_and_fail(
            logger,
            "update.validation_failed profile=%s reason=invalid_format",
            profile,
            error_message="❌ Invalid API key format. Should start with 'sk-', be at least 20 characters, and no longer than 256 characters",
        )

    # Check encryption availability
    if not ENCRYPTION_AVAILABLE:
        return _log_and_fail(
            logger,
            "update.encryption_unavailable profile=%s",
            profile,
            error_message="❌ Encryption is required. Install cryptography: pip install cryptography",
        )

    # Encrypt the API key
    try:
        encrypted_value = encrypt_value(api_key)
    except RuntimeError as exc:
        return _log_and_fail(
            logger,
            "update.encryption_failed profile=%s error=%s",
            profile,
            str(exc),  # SECURITY: Convert exception to string to avoid leaking sensitive data
            error_message=f"❌ Error: {exc}",
        )

    # Validate encryption result
    if not encrypted_value.startswith("encrypted:"):
        return _log_and_fail(
            logger,
            "update.encryption_failed profile=%s error=unexpected_format",
            profile,
            error_message="❌ Error: Encryption failed - key not properly encrypted",
        )

    touched = _update_config_files(
        profile, api_key, encrypted_value, logger, backup=backup, dry_run=dry_run
    )

    stored_keychain = False
    if not dry_run and encrypted_value.startswith("encrypted:"):
        stored_keychain = _store_in_keychain(profile, api_key, encrypted_value)
        if stored_keychain:
            logger.info("update.keychain profile=%s status=stored", profile)

    metadata_path = None
    if not dry_run:
        metadata_path = _update_metadata(profile, api_key, source)
        logger.info("update.metadata profile=%s file=%s", profile, metadata_path)

    # SECURITY: Only log masked value, never the actual key
    logger.info(
        "update.complete profile=%s masked=%s touched=%d dry_run=%s",
        profile,
        masked,
        len(touched),
        dry_run,
    )

    _print_update_results(profile, touched, metadata_path, stored_keychain, dry_run)

    return True


def rotate_api_key(
    api_key: str,
    *,
    profile: str = DEFAULT_PROFILE,
    dry_run: bool = False,
    source: str = "rotation",
) -> bool:
    """Rotate an API key with guaranteed backups."""
    return update_api_key(
        api_key,
        profile=profile,
        dry_run=dry_run,
        backup=not dry_run,
        source=source,
    )


def run_diagnostics(
    *, profiles: Optional[Iterable[str]] = None, threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS
) -> bool:
    """Run integrity checks for configured profiles."""
    logger = _audit_logger()
    ok = True

    if not ENCRYPTION_AVAILABLE:
        logger.error("diagnostics.encryption_unavailable")
        print("❌ Encryption not available. Install 'cryptography'.")
        ok = False
    else:
        print("✅ cryptography module detected")

    cursor_home = _cursor_home()
    key_file = cursor_home / ".key"
    if key_file.exists():
        print(f"✅ Encryption key detected at {key_file}")
        _verify_secure_permissions(key_file)
    else:
        print(f"⚠️ Encryption key missing at {key_file}")
        ok = False

    meta_path = cursor_home / METADATA_FILENAME
    if meta_path.exists():
        print(f"📄 Metadata file located at {meta_path}")
        _verify_secure_permissions(meta_path)
    else:
        print("Info: No metadata file found yet (keys may not have been stored).")

    _warn_if_stale(threshold_days)

    selected_profiles = list(profiles) if profiles else list(PROFILE_CONFIG.keys())
    for profile in selected_profiles:
        if profile not in PROFILE_CONFIG:
            logger.warning("diagnostics.unknown_profile profile=%s", profile)
            continue
        env_keys: Sequence[str] = PROFILE_CONFIG[profile]["env_keys"]  # type: ignore[assignment]
        env_file = cursor_home / ".env"
        if not env_file.exists():
            print(f"Info: .env missing for profile '{profile}' — nothing to verify.")
            continue
        content = env_file.read_text()
        if any(f"{key}=" in content for key in env_keys):
            print(f"✅ .env contains entry for profile '{profile}' ({', '.join(env_keys)})")
        else:
            print(f"⚠️ .env missing entry for profile '{profile}' ({', '.join(env_keys)})")
            ok = False

    return ok


def _interactive_prompt() -> None:
    print("🔑 OpenAI API Key Configuration")
    print("=" * 40)

    api_key = input("Enter your OpenAI API key (sk-...): ").strip()
    if not api_key:
        print("❌ No API key provided")
        return

    profile = input("Profile (premium/free) [premium]: ").strip() or DEFAULT_PROFILE

    success = update_api_key(api_key, profile=profile)
    if success:
        print("\n✅ Configuration updated successfully!")
    else:
        print("\n❌ Failed to update configuration")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage PulsePlate OpenAI API keys")
    sub = parser.add_subparsers(dest="command")

    set_parser = sub.add_parser("set", help="Store or update API keys")
    set_parser.add_argument("--api-key", dest="api_key", help="API key value")
    set_parser.add_argument(
        "--profile", choices=list(PROFILE_CONFIG.keys()), default=DEFAULT_PROFILE
    )
    set_parser.add_argument(
        "--from-env", dest="from_env", help="Environment variable with key or profile map"
    )
    set_parser.add_argument(
        "--from-file",
        dest="from_file",
        type=Path,
        help="File containing API keys (one per line or JSON mapping)",
    )
    set_parser.add_argument("--dry-run", action="store_true", help="Validate without writing")
    set_parser.add_argument("--skip-backup", action="store_true", help="Skip creating backup files")
    set_parser.add_argument("--source", default="cli", help="Metadata/audit source label")

    rotate_parser = sub.add_parser("rotate", help="Rotate keys with backups")
    rotate_parser.add_argument("--api-key", dest="api_key", help="New API key value")
    rotate_parser.add_argument(
        "--profile", choices=list(PROFILE_CONFIG.keys()), default=DEFAULT_PROFILE
    )
    rotate_parser.add_argument("--from-env", dest="from_env", help="Environment variable payload")
    rotate_parser.add_argument(
        "--from-file",
        dest="from_file",
        type=Path,
        help="File containing API keys",
    )
    rotate_parser.add_argument("--dry-run", action="store_true", help="Dry run rotation")
    rotate_parser.add_argument("--source", default="rotation", help="Metadata/audit source label")

    verify_parser = sub.add_parser("verify", help="Run diagnostics")
    verify_parser.add_argument("--profile", action="append", help="Profile(s) to verify")
    verify_parser.add_argument(
        "--stale-days",
        type=int,
        default=DEFAULT_STALE_THRESHOLD_DAYS,
        help="Warn when keys older than this",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Shortcut: same as `set --dry-run` when no subcommand provided",
    )
    parser.add_argument("--profile", choices=list(PROFILE_CONFIG.keys()), default=DEFAULT_PROFILE)
    parser.add_argument("--api-key", dest="api_key", help="API key (shorthand)")

    return parser


def _handle_set_command(
    api_key: Optional[str],
    profile: str,
    from_env: Optional[str],
    from_file: Optional[Path],
    *,
    dry_run: bool,
    backup: bool,
    source: str,
) -> bool:
    """Handle set command for API key updates.

    Security: API keys are never logged in clear text during batch operations.
    """
    jobs = _collect_jobs(api_key, profile, from_env, from_file, source=source)
    success = True
    for job_profile, job_key, job_source in jobs:
        try:
            result = update_api_key(
                job_key,
                profile=job_profile,
                dry_run=dry_run,
                backup=backup,
                source=job_source,
            )
            success = success and result
        except Exception as exc:  # pragma: no cover - defensive
            # SECURITY: Log only profile and source, not the key or exception details that might contain keys
            _audit_logger().error(
                "batch.update_failed profile=%s source=%s error=%s",
                job_profile,
                job_source,
                type(exc).__name__,
            )
            print(f"❌ Failed to update profile '{job_profile}': {type(exc).__name__}")
            success = False
    return success


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "verify":
        ok = run_diagnostics(profiles=args.profile, threshold_days=args.stale_days)
        return 0 if ok else 1

    if args.command in {"set", "rotate"}:
        dry_run = getattr(args, "dry_run", False)
        backup = not getattr(args, "skip_backup", False)
        if args.command == "rotate":
            backup = not dry_run
        success = _handle_set_command(
            api_key=args.api_key,
            profile=args.profile,
            from_env=args.from_env,
            from_file=args.from_file,
            dry_run=dry_run,
            backup=backup,
            source=args.source,
        )
        return 0 if success else 1

    # Shorthand / interactive fallback
    if args.api_key:
        success = update_api_key(
            args.api_key,
            profile=args.profile,
            dry_run=args.dry_run,
            backup=not args.dry_run,
            source="cli",
        )
        return 0 if success else 1

    _interactive_prompt()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
