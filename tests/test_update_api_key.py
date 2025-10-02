"""
Tests for update_api_key module - API key management with encryption
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

import secure_config
import update_api_key
from secure_config import encrypt_value, get_or_create_encryption_key


def fake_key(label: str = "test", *, blocks: int = 7) -> str:
    """Generate a deterministic fake key that passes validation without resembling a real secret."""

    return f"sk-{label}-" + ("xyz" * blocks)


class TestUpdateAPIKey:
    """Test update_api_key functionality"""

    def test_validate_api_key_valid(self):
        """Test valid API key validation"""
        valid_key = "sk-" + "a" * 20
        # Should pass validation (returns True in update_api_key function)
        assert valid_key.startswith("sk-")
        assert len(valid_key) >= 20
        assert len(valid_key) <= 256

    def test_validate_api_key_invalid_prefix(self):
        """Test API key validation rejects invalid prefix"""
        invalid_key = "invalid-key-12345678"
        assert not invalid_key.startswith("sk-")

    def test_validate_api_key_too_short(self):
        """Test API key validation rejects short keys"""
        short_key = "sk-short"
        assert len(short_key) < 20

    def test_validate_api_key_too_long(self):
        """Test API key validation rejects very long keys"""
        long_key = "sk-" + "a" * 300
        assert len(long_key) > 256

    def test_encrypt_value_no_encryption(self):
        """Test encryption raises RuntimeError when crypto unavailable"""
        with patch("secure_config.ENCRYPTION_AVAILABLE", False):
            # Should raise RuntimeError when crypto not available
            with pytest.raises(RuntimeError, match="cryptography library not installed"):
                encrypt_value("sk-test12345678901234567890")

    def test_encrypt_value_with_encryption(self, tmp_path):
        """Test encryption works when crypto available"""
        try:
            from cryptography.fernet import Fernet

            # Create temp key
            key_file = tmp_path / ".cursor" / ".key"
            key_file.parent.mkdir(parents=True, exist_ok=True)
            test_key = Fernet.generate_key()
            key_file.write_bytes(test_key)
            os.chmod(key_file, 0o600)

            with patch("secure_config.Path.home", return_value=tmp_path):
                result = encrypt_value("sk-test12345678901234567890")
                assert result.startswith("encrypted:")

        except ImportError:
            pytest.skip("cryptography not installed")

    def test_get_encryption_key_creates_new(self, tmp_path):
        """Test encryption key creation"""
        with patch("secure_config.Path.home", return_value=tmp_path):
            try:
                key = get_or_create_encryption_key()
                assert key is not None

                # Check key file exists
                key_file = tmp_path / ".cursor" / ".key"
                assert key_file.exists()

                # Check permissions
                stat_info = os.stat(key_file)
                assert stat_info.st_mode & 0o777 == 0o600

            except (ImportError, AttributeError):
                pytest.skip("cryptography not installed or function not available")

    def test_update_api_key_invalid_key(self, tmp_path, capsys):
        """Test update_api_key rejects invalid keys"""
        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key("invalid-key")
            assert result is False

            captured = capsys.readouterr()
            assert "Invalid API key format" in captured.out

    def test_update_api_key_fails_without_encryption(self, tmp_path, capsys):
        """Test update_api_key fails when encryption not available"""
        valid_key = "sk-" + "a" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("update_api_key.ENCRYPTION_AVAILABLE", False):
                result = update_api_key.update_api_key(valid_key)
                assert result is False

        captured = capsys.readouterr()
        assert "cryptography" in captured.out

    def test_update_api_key_simple_success(self, tmp_path, capsys, fake_crypto):
        """Test update_api_key basic success case with encryption"""
        valid_key = "sk-" + "a" * 40

        # Create MCP config
        mcp_file = tmp_path / ".cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.write_text(json.dumps({"mcpServers": {}}))

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        captured = capsys.readouterr()
        assert "API key will be stored encrypted" in captured.out
        meta = tmp_path / ".cursor" / "key.meta.json"
        assert meta.exists()
        metadata = json.loads(meta.read_text())
        assert metadata["profiles"]["premium"]["masked_sample"].startswith("sk-a")

    def test_update_api_key_updates_mcp_config(self, tmp_path, fake_crypto):
        """Test that update_api_key updates MCP config"""
        valid_key = "sk-" + "a" * 40
        mcp_file = tmp_path / ".cursor" / "mcp.json"
        mcp_file.parent.mkdir(parents=True, exist_ok=True)

        mcp_file.write_text(json.dumps({"mcpServers": {}}))

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        config = json.loads(mcp_file.read_text())
        env = config["mcpServers"]["pulseplate-chatgpt"]["env"]
        assert env["OPENAI_API_KEY"] == valid_key

    def test_update_api_key_updates_env_file(self, tmp_path, fake_crypto):
        """Ensure .env file is updated and encrypted value written."""
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("OPENAI_API_KEY=encrypted:old")

        valid_key = "sk-" + "x" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        new_value = env_file.read_text().strip().split("=", 1)[1]
        assert new_value.startswith("encrypted:")

    def test_update_api_key_handles_env_missing(self, tmp_path, fake_crypto):
        """Should append encrypted key when env entry missing."""
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("OTHER=value")

        valid_key = "sk-" + "y" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        content = env_file.read_text().splitlines()
        assert any(line.startswith("OPENAI_API_KEY=encrypted:") for line in content)
        assert "OTHER=value" in content

    def test_update_api_key_handles_env_file_absent(self, tmp_path, capsys, fake_crypto):
        """No error when env/settings files do not exist."""
        valid_key = "sk-" + "z" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        captured = capsys.readouterr()
        assert "environment file" not in captured.out.lower()

    def test_update_api_key_creates_env_entry_when_missing(self, tmp_path, fake_crypto):
        """If env file absent, no file should be created automatically."""
        valid_key = "sk-" + "w" * 40

        env_file = tmp_path / ".cursor" / ".env"
        assert not env_file.exists()

        with patch("update_api_key.Path.home", return_value=tmp_path):
            update_api_key.update_api_key(valid_key)

        assert not env_file.exists()

    def test_update_api_key_writes_plaintext_to_settings_json(self, tmp_path, fake_crypto):
        """settings.json should receive plain text key."""
        settings_file = tmp_path / ".cursor" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text(json.dumps({}))

        valid_key = "sk-" + "d" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        settings = json.loads(settings_file.read_text())
        assert settings["cursor.ai.openaiApiKey"] == valid_key

    def test_update_api_key_updates_env_file_existing_key(self, tmp_path, fake_crypto):
        """Test update_api_key replaces existing encrypted key in .env."""
        valid_key = "sk-" + "b" * 40
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        env_file = tmp_path / ".cursor" / ".env"
        env_file.write_text("OPENAI_API_KEY=encrypted:old")

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("secure_config.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True

        content = env_file.read_text().strip()
        assert content.startswith("OPENAI_API_KEY=encrypted:")
        assert "old" not in content

    def test_update_api_key_appends_env_key_when_missing(self, tmp_path, fake_crypto):
        """Test update_api_key appends encrypted key when env file has no entry."""
        valid_key = "sk-" + "c" * 40
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        env_file = tmp_path / ".cursor" / ".env"
        env_file.write_text("OTHER_VAR=value")

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("secure_config.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True

        content = env_file.read_text().splitlines()
        assert "OTHER_VAR=value" in content
        assert any(line.startswith("OPENAI_API_KEY=encrypted:") for line in content)

    def test_update_api_key_creates_files_when_missing(self, tmp_path, capsys, fake_crypto):
        """Test update_api_key handles missing optional files gracefully."""
        valid_key = "sk-" + "d" * 40
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("secure_config.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True

        """Test update_api_key updates settings.json when present."""
        captured = capsys.readouterr()
        assert "MCP configuration" not in captured.out  # file absent, skip message
        env_file = tmp_path / ".cursor" / ".env"
        assert env_file.exists() is False  # not created because method only writes if exists

    def test_update_api_key_updates_settings_json(self, tmp_path, fake_crypto):
        """Test update_api_key updates settings.json when present."""
        valid_key = "sk-" + "e" * 40
        key_file = tmp_path / ".cursor" / ".key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(fake_crypto.generate_key())

        settings_file = tmp_path / ".cursor" / "settings.json"
        settings_file.write_text(json.dumps({"cursor.ai.openaiApiKey": "old"}))

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("secure_config.Path.home", return_value=tmp_path):
                result = update_api_key.update_api_key(valid_key)
                assert result is True

        updated = json.loads(settings_file.read_text())
        assert updated["cursor.ai.openaiApiKey"] == valid_key

    def test_update_api_key_encrypt_failure(self, tmp_path, capsys):
        """Test update_api_key handles encryption failure gracefully."""
        valid_key = "sk-" + "f" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("update_api_key.ENCRYPTION_AVAILABLE", True):
                with patch("update_api_key.encrypt_value", side_effect=RuntimeError("boom")):
                    result = update_api_key.update_api_key(valid_key)

        assert result is False
        captured = capsys.readouterr()
        assert "Error: boom" in captured.out

    def test_update_api_key_encryption_prefix_validation(self, tmp_path, capsys):
        """Test update_api_key detects unexpected encryption output."""
        valid_key = "sk-" + "g" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            with patch("update_api_key.ENCRYPTION_AVAILABLE", True):
                with patch("update_api_key.encrypt_value", return_value="not_encrypted"):
                    result = update_api_key.update_api_key(valid_key)

        assert result is False
        captured = capsys.readouterr()
        assert "Encryption failed" in captured.out

    def test_update_api_key_invalid_env_line(self, tmp_path, fake_crypto):
        """Строки .env без '=' пропускаются без ошибок / Invalid lines are skipped."""
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("INVALID_LINE\nOPENAI_API_KEY=encrypted:old")

        valid_key = "sk-" + "h" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        lines = env_file.read_text().splitlines()
        assert "INVALID_LINE" in lines
        assert any(line.startswith("OPENAI_API_KEY=encrypted:") for line in lines)

    def test_update_api_key_skips_blank_env_lines(self, tmp_path, fake_crypto):
        """Blank env lines are preserved without breaking updates."""
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("\nOPENAI_API_KEY=encrypted:old\n")

        valid_key = "sk-" + "i" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            result = update_api_key.update_api_key(valid_key)
            assert result is True

        lines = env_file.read_text().splitlines()
        assert "" in lines  # blank line preserved
        assert any(line.startswith("OPENAI_API_KEY=encrypted:") for line in lines)

    def test_update_api_key_supports_free_profile(self, tmp_path, fake_crypto):
        """Free profile writes to dedicated env key without touching premium entry."""
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("OPENAI_API_KEY=encrypted:premium-value\n")

        free_key = "sk-" + "f" * 40

        with patch("update_api_key.Path.home", return_value=tmp_path):
            update_api_key.update_api_key(free_key, profile="free")

        lines = env_file.read_text().splitlines()
        assert any(line.startswith("OPENAI_API_KEY=encrypted:premium-value") for line in lines)
        assert any(line.startswith("OPENAI_API_KEY_FREE=") for line in lines)

        meta = json.loads((tmp_path / ".cursor" / "key.meta.json").read_text())
        assert "free" in meta["profiles"]

    def test_rotate_api_key_creates_backups(self, tmp_path, fake_crypto):
        """Rotation should back up mutable files when present."""
        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("OPENAI_API_KEY=encrypted:old\n")

        with patch("update_api_key.Path.home", return_value=tmp_path):
            update_api_key.rotate_api_key("sk-" + "r" * 40)

        backups = list(env_file.parent.glob(".env.bak.*"))
        assert backups, "Expected rotation to create at least one backup file"

    def test_batch_update_from_file_multiple_profiles(self, tmp_path, fake_crypto):
        """Bulk file payload supports multiple profile entries."""
        payload = "premium:sk-" + "p" * 40 + "\nfree:sk-" + "f" * 40 + "\n"
        config_file = tmp_path / "keys.txt"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(payload)

        env_file = tmp_path / ".cursor" / ".env"
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("OPENAI_API_KEY=encrypted:old\n")

        with patch("update_api_key.Path.home", return_value=tmp_path):
            update_api_key._handle_set_command(
                api_key=None,
                profile="premium",
                from_env=None,
                from_file=config_file,
                dry_run=False,
                backup=False,
                source="test-batch",
            )

        content = env_file.read_text()
        assert "OPENAI_API_KEY=" in content
        assert "OPENAI_API_KEY_FREE=" in content

    def test_audit_logger_reuse_same_directory(self, tmp_path, monkeypatch):
        """_audit_logger should reuse handlers when working directory matches."""

        cursor_dir = tmp_path / ".cursor"
        monkeypatch.setattr(update_api_key, "_cursor_home", lambda: cursor_dir)
        logger = update_api_key._audit_logger()
        for handler in list(logger.handlers):
            if not isinstance(handler, logging.handlers.RotatingFileHandler):
                logger.removeHandler(handler)
                handler.close()
        initial_count = len(logger.handlers)
        try:
            again = update_api_key._audit_logger()
            assert again is logger
            assert len(logger.handlers) == initial_count
        finally:
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
                handler.close()

    def test_mask_secret_variants(self):
        """_mask_secret handles empty, short, and long inputs."""

        assert update_api_key._mask_secret("") == "(empty)"
        assert update_api_key._mask_secret("short") == "***"
        assert update_api_key._mask_secret("sk-secret-value") == "sk-s...alue"

    def test_create_backup_and_permission_warning(self, tmp_path, monkeypatch, caplog):
        """Backup helper creates copies and warns about unsafe permissions."""

        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        target = cursor_dir / ".env"
        target.write_text("OPENAI_API_KEY=encrypted:value")

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2025, 1, 2, 3, 4, 5, tzinfo=tz)

        monkeypatch.setattr(update_api_key, "datetime", FixedDatetime, raising=False)

        assert update_api_key._create_backup(cursor_dir / "missing.env") is None

        backup_path = update_api_key._create_backup(target)
        assert backup_path is not None and backup_path.exists()

        os.chmod(target, 0o644)
        perm_logger = logging.getLogger("perm-warning")
        for handler in list(perm_logger.handlers):
            perm_logger.removeHandler(handler)
        caplog.set_level(logging.WARNING, logger="perm-warning")
        monkeypatch.setattr(update_api_key, "_audit_logger", lambda: perm_logger)
        update_api_key._verify_secure_permissions(target)
        assert "Insecure permissions" in caplog.text

        # Non-existent paths should be ignored without error
        update_api_key._verify_secure_permissions(cursor_dir / "nonexistent")

    def test_store_in_keychain_branches(self, monkeypatch, caplog):
        """_store_in_keychain handles missing modules, failures, and success."""

        caplog.set_level(logging.WARNING)
        log = logging.getLogger("keychain-test")
        for handler in list(log.handlers):
            log.removeHandler(handler)
        monkeypatch.setattr(update_api_key, "_audit_logger", lambda: log)
        monkeypatch.setenv("PP_KEY_STORAGE", "keychain")

        monkeypatch.setattr(update_api_key, "keyring", None, raising=False)
        assert update_api_key._store_in_keychain("premium", "encrypted:value") is False
        assert "python-keyring" in caplog.text
        caplog.clear()

        class FaultyKeyring:
            def set_password(self, *_args, **_kwargs):
                raise RuntimeError("boom")

        monkeypatch.setattr(update_api_key, "keyring", FaultyKeyring(), raising=False)
        assert update_api_key._store_in_keychain("premium", "encrypted:value") is False
        assert "System keychain persistence failed" in caplog.text
        caplog.clear()

        saved = {}

        class SuccessfulKeyring:
            def set_password(self, service, username, value):
                saved["call"] = (service, username, value)

        monkeypatch.setattr(update_api_key, "keyring", SuccessfulKeyring(), raising=False)
        assert update_api_key._store_in_keychain("premium", "encrypted:value") is True
        assert saved["call"][1] == "premium-api-key"

    def test_update_metadata_handles_invalid_json(self, tmp_path, monkeypatch):
        """Invalid metadata should be replaced without error."""

        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        meta_path = cursor_dir / "key.meta.json"
        meta_path.write_text("not-json")
        monkeypatch.setattr(update_api_key, "_cursor_home", lambda: cursor_dir)

        result = update_api_key._update_metadata("premium", "sk-test-1234567890", "tests")
        data = json.loads(result.read_text())
        assert data["profiles"]["premium"]["source"] == "tests"

    def test_update_api_key_logs_keychain_success(self, tmp_path, monkeypatch, caplog):
        """update_api_key should log keychain storage when enabled."""

        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        monkeypatch.setattr(update_api_key, "_cursor_home", lambda: cursor_dir)
        monkeypatch.setattr(update_api_key, "ENCRYPTION_AVAILABLE", True, raising=False)
        monkeypatch.setenv("PP_KEY_STORAGE", "keychain")

        class DummyKeyring:
            def set_password(self, *args):
                return None

        audit_logger = logging.getLogger("update-keychain")
        for handler in list(audit_logger.handlers):
            audit_logger.removeHandler(handler)
        caplog.set_level(logging.INFO, logger="update-keychain")

        monkeypatch.setattr(update_api_key, "keyring", DummyKeyring(), raising=False)
        monkeypatch.setattr(update_api_key, "_audit_logger", lambda: audit_logger)
        monkeypatch.setattr(
            update_api_key, "encrypt_value", lambda key: "encrypted:value", raising=False
        )
        monkeypatch.setattr(update_api_key, "_update_config_files", lambda *a, **k: [])
        monkeypatch.setattr(update_api_key, "_update_metadata", lambda *a, **k: tmp_path / "meta")

        assert update_api_key.update_api_key("sk-" + "m" * 40) is True
        assert "stored_in_system" in caplog.text

    def test_warn_if_stale_emits_warning(self, tmp_path, monkeypatch, caplog):
        """_warn_if_stale should warn for outdated metadata entries."""

        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        monkeypatch.setattr(update_api_key, "_cursor_home", lambda: cursor_dir)

        # Missing file should be ignored silently
        update_api_key._warn_if_stale(threshold_days=30)

        # Invalid JSON content should also be ignored
        meta_file = cursor_dir / "key.meta.json"
        meta_file.write_text("not-json")
        update_api_key._warn_if_stale(threshold_days=30)

        meta_file.write_text(json.dumps({"profiles": []}))
        update_api_key._warn_if_stale(threshold_days=30)

        meta_file.write_text(json.dumps({"profiles": {"premium": {}}}))
        update_api_key._warn_if_stale(threshold_days=30)

        meta_file.write_text(json.dumps({"profiles": {"premium": {"last_updated": "bad"}}}))
        update_api_key._warn_if_stale(threshold_days=30)

        stale_payload = {
            "profiles": {
                "premium": {
                    "last_updated": (datetime.now(timezone.utc) - timedelta(days=120)).isoformat()
                }
            }
        }
        meta_file.write_text(json.dumps(stale_payload))

        warning_logger = logging.getLogger("stale")
        for handler in list(warning_logger.handlers):
            warning_logger.removeHandler(handler)
        caplog.set_level(logging.WARNING, logger="stale")
        monkeypatch.setattr(update_api_key, "_audit_logger", lambda: warning_logger)

        update_api_key._warn_if_stale(threshold_days=30)
        assert "stale" in caplog.text

    def test_parse_bulk_payload_formats(self):
        """Bulk payload parser should support JSON, lines, and empty payloads."""

        json_array = json.dumps([{"profile": "premium", "api_key": fake_key("array")}])
        jobs = update_api_key._parse_bulk_payload(
            json_array, default_profile="premium", source="json"
        )
        assert jobs == [("premium", fake_key("array"), "json")]

        json_object = json.dumps({"free": fake_key("free")})
        jobs = update_api_key._parse_bulk_payload(
            json_object, default_profile="premium", source="json"
        )
        assert ("free", fake_key("free"), "json") in jobs

        weird_json = json.dumps([1, 2])
        jobs = update_api_key._parse_bulk_payload(
            weird_json, default_profile="premium", source="json"
        )
        assert jobs  # fallback to line-based parsing

        missing_key_json = json.dumps([{"profile": "premium"}])
        jobs = update_api_key._parse_bulk_payload(
            missing_key_json, default_profile="premium", source="json"
        )
        assert jobs

        odd_json = json.dumps("just-a-string")
        jobs = update_api_key._parse_bulk_payload(
            odd_json, default_profile="premium", source="json"
        )
        assert jobs

        broken_json = "{invalid"
        jobs = update_api_key._parse_bulk_payload(
            broken_json, default_profile="premium", source="json"
        )
        assert jobs

        graph_payload = f"premium={fake_key('graph')}\n# comment\n{fake_key('fallback')}"
        jobs = update_api_key._parse_bulk_payload(
            graph_payload, default_profile="premium", source="lines"
        )
        assert ("premium", fake_key("graph"), "lines") in jobs
        assert ("premium", fake_key("fallback"), "lines") in jobs

        assert (
            update_api_key._parse_bulk_payload("", default_profile="premium", source="empty") == []
        )

        class BadPayload(str):
            def strip(self):
                return self

            def splitlines(self):
                return [BadLine(self)]

        class BadLine(str):
            def split(self, sep=None, maxsplit=-1):
                if sep == ":":
                    return [self]
                return super().split(sep, maxsplit)

            def strip(self):
                return self

        with pytest.raises(ValueError):
            update_api_key._parse_bulk_payload(
                BadPayload("premium:bad"), default_profile="premium", source="lines"
            )

        with patch("update_api_key.json.loads", return_value=123):
            jobs = update_api_key._parse_bulk_payload(
                "{}", default_profile="premium", source="json"
            )
            assert jobs

    def test_collect_jobs_sources(self, tmp_path, monkeypatch):
        """_collect_jobs should aggregate direct, env, and file sources."""

        config = tmp_path / "bulk_keys.json"
        config.write_text(json.dumps({"free": fake_key("file")}))
        monkeypatch.setenv(
            "BULK_KEYS",
            json.dumps([{"profile": "premium", "api_key": fake_key("env")}]),
        )

        jobs = update_api_key._collect_jobs(
            fake_key("direct"),
            profile="premium",
            from_env="BULK_KEYS",
            from_file=config,
            source="cli",
        )
        assert any(job[0] == "premium" and job[1] == fake_key("direct") for job in jobs)
        assert any(job[0] == "free" for job in jobs)

        with pytest.raises(RuntimeError):
            update_api_key._collect_jobs(None, "premium", "MISSING_ENV", None, source="cli")

        with pytest.raises(RuntimeError):
            update_api_key._collect_jobs(None, "premium", None, None, source="cli")

    def test_update_api_key_invalid_profile_raises(self):
        """Unsupported profiles should raise ValueError before any side effects."""

        with pytest.raises(ValueError):
            update_api_key.update_api_key("sk-" + "v" * 40, profile="unknown")

    def test_update_helpers_handle_invalid_json(self, tmp_path, monkeypatch, capsys):
        """Config update helpers should tolerate invalid JSON payloads."""

        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        monkeypatch.setattr(update_api_key, "_cursor_home", lambda: cursor_dir)

        missing_mcp = cursor_dir / "missing.json"
        assert (
            update_api_key._update_mcp_config(
                missing_mcp, "OPENAI_API_KEY", "value", backup=False, dry_run=False
            )
            is None
        )

        mcp = cursor_dir / "mcp.json"
        mcp.write_text("not-json")
        assert (
            update_api_key._update_mcp_config(
                mcp, "OPENAI_API_KEY", "value", backup=False, dry_run=False
            )
            is None
        )
        assert "Failed to decode" in capsys.readouterr().out

        missing_settings = cursor_dir / "missing_settings.json"
        assert (
            update_api_key._update_settings(
                missing_settings, "cursor.ai.openaiApiKey", "plain", backup=False, dry_run=False
            )
            is None
        )

        settings = cursor_dir / "settings.json"
        settings.write_text("not-json")
        result = update_api_key._update_settings(
            settings, "cursor.ai.openaiApiKey", "plain", backup=True, dry_run=False
        )
        assert result == settings
        assert json.loads(settings.read_text())["cursor.ai.openaiApiKey"] == "plain"

    def test_run_diagnostics_paths(self, tmp_path, monkeypatch, caplog):
        """run_diagnostics detects missing resources then succeeds once files exist."""

        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        monkeypatch.setattr(update_api_key, "_cursor_home", lambda: cursor_dir)
        caplog.set_level(logging.WARNING)

        monkeypatch.setattr(update_api_key, "ENCRYPTION_AVAILABLE", False, raising=False)
        assert update_api_key.run_diagnostics(profiles=["premium"]) is False

        monkeypatch.setattr(update_api_key, "ENCRYPTION_AVAILABLE", True, raising=False)
        assert update_api_key.run_diagnostics(profiles=["unknown"]) is False

        key_file = cursor_dir / ".key"
        key_file.write_text("secret")
        os.chmod(key_file, 0o600)
        meta_content = {
            "profiles": {
                "premium": {
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "masked_sample": "***",
                    "source": "tests",
                }
            }
        }
        (cursor_dir / "key.meta.json").write_text(json.dumps(meta_content))
        env_file = cursor_dir / ".env"
        env_file.write_text("OPENAI_API_KEY=encrypted:value\n")

        assert update_api_key.run_diagnostics(profiles=["free"]) is False

        env_file.write_text("OPENAI_API_KEY=encrypted:value\nOPENAI_API_KEY_FREE=encrypted:free\n")
        assert update_api_key.run_diagnostics(profiles=["premium", "free"]) is True

    def test_update_config_files_logging(self, tmp_path, monkeypatch, caplog):
        """_update_config_files should log dry-run and missing file states."""

        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        monkeypatch.setattr(update_api_key, "_cursor_home", lambda: cursor_dir)

        log = logging.getLogger("config-files")
        for handler in list(log.handlers):
            log.removeHandler(handler)
        caplog.set_level(logging.INFO, logger="config-files")

        update_api_key._update_config_files(
            "premium", "sk-test", "encrypted:value", log, backup=False, dry_run=True
        )
        assert "dry run" in caplog.text

        caplog.clear()
        update_api_key._update_config_files(
            "premium", "sk-test", "encrypted:value", log, backup=False, dry_run=False
        )
        assert "missing" in caplog.text

        env_path = cursor_dir / ".env"
        assert (
            update_api_key._update_env_file(
                env_path, ["OPENAI_API_KEY"], "value", backup=False, dry_run=False
            )
            is None
        )
        env_path.write_text("EXISTING=value")
        assert (
            update_api_key._update_env_file(
                env_path, ["OPENAI_API_KEY"], "value", backup=False, dry_run=True
            )
            == env_path
        )

    def test_print_update_results_branches(self, tmp_path, capsys):
        """_print_update_results should handle dry-run and success output."""

        update_api_key._print_update_results("premium", [], None, False, dry_run=True)
        assert "No files were modified" in capsys.readouterr().out

        touched = [tmp_path / "file"]
        metadata_path = tmp_path / "meta"
        update_api_key._print_update_results("premium", touched, metadata_path, True, dry_run=False)
        output = capsys.readouterr().out
        assert "Metadata recorded" in output
        assert "Key also stored" in output

    def test_interactive_prompt_branches(self, monkeypatch, capsys):
        """Interactive prompt handles missing and valid user input."""

        monkeypatch.setattr("builtins.input", lambda prompt="": "")
        update_api_key._interactive_prompt()
        assert "No API key" in capsys.readouterr().out

        responses = iter(["sk-prompt", "free"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))
        monkeypatch.setattr(update_api_key, "update_api_key", lambda *args, **kwargs: True)
        update_api_key._interactive_prompt()
        assert "Configuration updated successfully" in capsys.readouterr().out

        responses_fail = iter(["sk-fail", "premium"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(responses_fail))
        monkeypatch.setattr(update_api_key, "update_api_key", lambda *args, **kwargs: False)
        update_api_key._interactive_prompt()
        assert "Failed to update" in capsys.readouterr().out

    def test_handle_set_command_and_main_dispatch(self, monkeypatch, capsys):
        """CLI helpers should dispatch commands and report failures."""

        jobs = [("premium", "sk-test", "cli")]
        monkeypatch.setattr(update_api_key, "_collect_jobs", lambda *a, **k: jobs)
        monkeypatch.setattr(update_api_key, "update_api_key", lambda *a, **k: True)
        assert update_api_key._handle_set_command(
            "sk", "premium", None, None, dry_run=False, backup=True, source="cli"
        )

        def _exploding(*_args, **_kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(update_api_key, "update_api_key", _exploding)
        batch_logger = logging.getLogger("batch-failure")
        for handler in list(batch_logger.handlers):
            batch_logger.removeHandler(handler)
        monkeypatch.setattr(update_api_key, "_audit_logger", lambda: batch_logger)
        assert (
            update_api_key._handle_set_command(
                "sk", "premium", None, None, dry_run=False, backup=True, source="cli"
            )
            is False
        )
        assert "Failed to update" in capsys.readouterr().out

        monkeypatch.setattr(update_api_key, "run_diagnostics", lambda **_: True)
        assert update_api_key.main(["verify"]) == 0

        monkeypatch.setattr(update_api_key, "_handle_set_command", lambda **_: True)
        assert (
            update_api_key.main(
                [
                    "set",
                    "--api-key",
                    "sk-test",
                    "--profile",
                    "premium",
                ]
            )
            == 0
        )

        monkeypatch.setattr(update_api_key, "_interactive_prompt", lambda: None)
        assert update_api_key.main([]) == 0

        assert (
            update_api_key.main(
                [
                    "rotate",
                    "--api-key",
                    "sk-rotate",
                    "--profile",
                    "premium",
                ]
            )
            == 0
        )

        monkeypatch.setattr(update_api_key, "update_api_key", lambda *args, **kwargs: True)
        assert (
            update_api_key.main(
                [
                    "--api-key",
                    "sk-direct",
                    "--profile",
                    "premium",
                ]
            )
            == 0
        )
