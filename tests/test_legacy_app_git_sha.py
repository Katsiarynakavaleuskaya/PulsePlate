# -*- coding: utf-8 -*-
"""
Tests for _short_git_sha function in legacy_app.py.

RU: Тесты для функции _short_git_sha в legacy_app.py.
EN: Tests for _short_git_sha function in legacy_app.py.
"""

from __future__ import annotations

from legacy_app import _short_git_sha


class TestShortGitSha:
    """Test _short_git_sha function for all code paths."""

    def test_short_git_sha_none(self) -> None:
        """Test that None returns 'unknown'."""
        assert _short_git_sha(None) == "unknown"

    def test_short_git_sha_empty_string(self) -> None:
        """Test that empty string returns 'unknown'."""
        assert _short_git_sha("") == "unknown"

    def test_short_git_sha_whitespace_only(self) -> None:
        """Test that whitespace-only string returns 'unknown'."""
        assert _short_git_sha("   ") == "unknown"
        assert _short_git_sha("\t\n") == "unknown"

    def test_short_git_sha_invalid_non_hex(self) -> None:
        """Test that non-hex strings return 'unknown'."""
        assert _short_git_sha("foo") == "unknown"
        assert _short_git_sha("not-a-hex-string") == "unknown"
        assert _short_git_sha("123xyz") == "unknown"

    def test_short_git_sha_too_short(self) -> None:
        """Test that hex strings shorter than 12 chars return 'unknown'."""
        assert _short_git_sha("123") == "unknown"
        assert _short_git_sha("abcd1234") == "unknown"
        assert _short_git_sha("sha256:123") == "unknown"
        assert _short_git_sha("sha256:abcd1234") == "unknown"

    def test_short_git_sha_valid_plain_hex(self) -> None:
        """Test that valid plain hex strings return first 12 chars."""
        assert (
            _short_git_sha("f4c8b72e593f1234567890abcdef")  # pragma: allowlist secret
            == "f4c8b72e593f"  # pragma: allowlist secret
        )
        assert (
            _short_git_sha("abcd1234567890abcdef1234567890")  # pragma: allowlist secret
            == "abcd12345678"  # pragma: allowlist secret
        )
        # Exactly 12 chars
        assert _short_git_sha("abcd12345678") == "abcd12345678"  # pragma: allowlist secret

    def test_short_git_sha_realistic_lengths(self) -> None:
        """Test that realistic SHA lengths (40 for SHA-1, 64 for SHA-256) are handled correctly."""
        # SHA-1 length (40 hex chars)
        assert _short_git_sha("a" * 40) == "aaaaaaaaaaaa"  # pragma: allowlist secret
        # SHA-256 length (64 hex chars)
        assert _short_git_sha("b" * 64) == "bbbbbbbbbbbb"  # pragma: allowlist secret

    def test_short_git_sha_sha256_prefix(self) -> None:
        """Test that sha256: prefix is stripped correctly."""
        # Valid long hex
        assert (
            _short_git_sha(
                "sha256:abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
            )  # pragma: allowlist secret
            == "abcd12345678"
        )
        # Too short after stripping
        assert _short_git_sha("sha256:123") == "unknown"
        # Empty after stripping
        assert _short_git_sha("sha256:") == "unknown"

    def test_short_git_sha_repo_digest_format(self) -> None:
        """Test that repo@sha256: format is handled correctly."""
        # Valid repo digest
        assert (
            _short_git_sha(
                "ghcr.io/user/repo@sha256:abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890"  # pragma: allowlist secret
            )
            == "abcd12345678"
        )
        # Too short after stripping
        assert _short_git_sha("ghcr.io/user/repo@sha256:123") == "unknown"
        # Empty after stripping
        assert _short_git_sha("ghcr.io/user/repo@sha256:") == "unknown"

    def test_short_git_sha_with_whitespace(self) -> None:
        """Test that whitespace around values is handled correctly."""
        assert (
            _short_git_sha("  f4c8b72e593f1234567890abcdef  ")
            == "f4c8b72e593f"  # pragma: allowlist secret
        )
        assert _short_git_sha("  sha256:abcd1234567890abcdef1234567890  ") == "abcd12345678"
        assert (
            _short_git_sha("  ghcr.io/repo@sha256:abcd1234567890abcdef1234567890  ")
            == "abcd12345678"
        )

    def test_short_git_sha_uppercase_hex(self) -> None:
        """Test that uppercase hex is accepted."""
        assert (
            _short_git_sha("ABCD1234567890ABCDEF1234567890")  # pragma: allowlist secret
            == "ABCD12345678"  # pragma: allowlist secret
        )
        assert (
            _short_git_sha("F4C8B72E593F1234567890ABCDEF")  # pragma: allowlist secret
            == "F4C8B72E593F"  # pragma: allowlist secret
        )

    def test_short_git_sha_mixed_case_hex(self) -> None:
        """Test that mixed case hex is accepted."""
        assert (
            _short_git_sha("AbCd1234567890aBcDeF1234567890")  # pragma: allowlist secret
            == "AbCd12345678"  # pragma: allowlist secret
        )
        assert (
            _short_git_sha("f4C8b72E593F1234567890aBcDeF")  # pragma: allowlist secret
            == "f4C8b72E593F"  # pragma: allowlist secret
        )
