"""
Tests for PII redaction utilities.

Verifies that common PII patterns are properly redacted before storage.
"""

from __future__ import annotations

import pytest

from core.pii_redaction import redact_pii_from_text


class TestRedactPiiFromText:
    """Tests for redact_pii_from_text function."""

    def test_redact_email_simple(self) -> None:
        """Simple email is redacted."""
        text = "Contact support@example.com for help"
        result = redact_pii_from_text(text)
        assert "[EMAIL_REDACTED]" in result
        assert "support@example.com" not in result

    def test_redact_email_multiple(self) -> None:
        """Multiple emails are all redacted."""
        text = "Email alice@test.com or bob@company.org"
        result = redact_pii_from_text(text)
        assert result.count("[EMAIL_REDACTED]") == 2
        assert "alice@test.com" not in result
        assert "bob@company.org" not in result

    def test_redact_email_with_subdomain(self) -> None:
        """Email with subdomain is redacted."""
        text = "Contact admin@mail.example.co.uk"
        result = redact_pii_from_text(text)
        assert "[EMAIL_REDACTED]" in result

    def test_redact_phone_dashes(self) -> None:
        """Phone with dashes is redacted."""
        text = "Call 555-123-4567 for support"
        result = redact_pii_from_text(text)
        assert "[PHONE_REDACTED]" in result
        assert "555-123-4567" not in result

    def test_redact_phone_dots(self) -> None:
        """Phone with dots is redacted."""
        text = "Call 555.123.4567 for support"
        result = redact_pii_from_text(text)
        assert "[PHONE_REDACTED]" in result
        assert "555.123.4567" not in result

    def test_redact_phone_no_separators(self) -> None:
        """Phone without separators is redacted."""
        text = "Call 5551234567 now"
        result = redact_pii_from_text(text)
        assert "[PHONE_REDACTED]" in result
        assert "5551234567" not in result

    def test_redact_phone_multiple(self) -> None:
        """Multiple phones are all redacted."""
        text = "Call 555-123-4567 or 555.987.6543"
        result = redact_pii_from_text(text)
        assert result.count("[PHONE_REDACTED]") == 2

    def test_redact_ssn(self) -> None:
        """SSN is redacted."""
        text = "SSN: 123-45-6789"
        result = redact_pii_from_text(text)
        assert "[SSN_REDACTED]" in result
        assert "123-45-6789" not in result

    def test_redact_credit_card_spaces(self) -> None:
        """Credit card with spaces is redacted."""
        text = "Card: 4111 1111 1111 1111"
        result = redact_pii_from_text(text)
        assert "[CREDIT_CARD_REDACTED]" in result
        assert "4111 1111 1111 1111" not in result

    def test_redact_credit_card_dashes(self) -> None:
        """Credit card with dashes is redacted."""
        text = "Card: 4111-1111-1111-1111"
        result = redact_pii_from_text(text)
        assert "[CREDIT_CARD_REDACTED]" in result

    def test_redact_credit_card_no_separators(self) -> None:
        """Credit card without separators is redacted."""
        text = "Card: 4111111111111111"
        result = redact_pii_from_text(text)
        assert "[CREDIT_CARD_REDACTED]" in result

    def test_redact_multiple_pii_types(self) -> None:
        """Multiple PII types in same text are all redacted."""
        text = "Email me@example.com, call 555-123-4567, SSN 123-45-6789"
        result = redact_pii_from_text(text)
        assert "[EMAIL_REDACTED]" in result
        assert "[PHONE_REDACTED]" in result
        assert "[SSN_REDACTED]" in result
        assert "me@example.com" not in result
        assert "555-123-4567" not in result
        assert "123-45-6789" not in result

    def test_no_pii_unchanged(self) -> None:
        """Text without PII is unchanged."""
        text = "No PII here, just normal text about BMI calculations."
        result = redact_pii_from_text(text)
        assert result == text

    def test_none_input_returns_none(self) -> None:
        """None input returns None."""
        assert redact_pii_from_text(None) is None

    def test_empty_string_unchanged(self) -> None:
        """Empty string returns empty string."""
        assert redact_pii_from_text("") == ""

    def test_preserves_surrounding_text(self) -> None:
        """Redaction preserves surrounding text."""
        text = "Hello, contact me@test.com please. Thanks!"
        result = redact_pii_from_text(text)
        assert result == "Hello, contact [EMAIL_REDACTED] please. Thanks!"

    def test_redaction_tokens_are_uppercase(self) -> None:
        """Redaction tokens use consistent uppercase format."""
        text = "Email: a@b.com, Phone: 111-222-3333, SSN: 111-22-3333"
        result = redact_pii_from_text(text)
        # All tokens should be uppercase with _REDACTED suffix
        assert "[EMAIL_REDACTED]" in result
        assert "[PHONE_REDACTED]" in result
        assert "[SSN_REDACTED]" in result
