"""
PII redaction utilities for feedback storage.

Redacts common PII patterns before persisting user feedback to comply with
privacy requirements (RAG_CONTRACT.md §7 Security Notes).

Note: This is basic regex-based redaction. For production, consider
NER-based detection (Presidio, spaCy) - tracked in BACKLOG_LEDGER P2.
"""

from __future__ import annotations

import re
from typing import Optional

# Common PII patterns
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# US phone formats: 555-123-4567, 555.123.4567, 5551234567
PHONE_PATTERN = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
# US SSN format: 123-45-6789
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
# Credit card (basic 16-digit patterns with optional separators)
CREDIT_CARD_PATTERN = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")


def redact_pii_from_text(text: Optional[str]) -> Optional[str]:
    """
    Redact common PII patterns from text.

    Args:
        text: Input text that may contain PII

    Returns:
        Text with PII patterns replaced by [*_REDACTED] tokens,
        or None if input is None

    Redactions:
        - Emails -> [EMAIL_REDACTED]
        - Phone numbers -> [PHONE_REDACTED]
        - SSN -> [SSN_REDACTED]
        - Credit cards -> [CREDIT_CARD_REDACTED]

    Example:
        >>> redact_pii_from_text("Contact me@example.com or 555-123-4567")
        'Contact [EMAIL_REDACTED] or [PHONE_REDACTED]'
    """
    if text is None:
        return None

    result = text
    result = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", result)
    result = PHONE_PATTERN.sub("[PHONE_REDACTED]", result)
    result = SSN_PATTERN.sub("[SSN_REDACTED]", result)
    result = CREDIT_CARD_PATTERN.sub("[CREDIT_CARD_REDACTED]", result)

    return result
