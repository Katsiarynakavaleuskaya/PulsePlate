"""
Centralized error classification utilities used across scripts/tools.
"""

from __future__ import annotations

from typing import Final


def classify_error(error_text: str) -> str:
    """Classify an error message into a stable category string.

    Categories (ordered by specificity):
    - assertion_error
    - import_error
    - type_error
    - validation_error
    - memory_error
    - performance_error (incl. timeouts)
    - attribute_error
    - coverage_error
    - async_error
    - unknown
    """
    text: Final[str] = (error_text or "").lower()

    if "assert" in text or "assertionerror" in text:
        return "assertion_error"
    if "importerror" in text or "no module named" in text or "modulenotfounderror" in text:
        return "import_error"
    if "typeerror" in text:
        return "type_error"
    if "valueerror" in text or "unprocessable" in text or "422" in text:
        return "validation_error"
    if "memory" in text:
        return "memory_error"
    if "timeout" in text or "took too long" in text or "performance" in text:
        return "performance_error"
    if "attributeerror" in text or "has no attribute" in text:
        return "attribute_error"
    if "coverage" in text and ("below" in text or "%" in text):
        return "coverage_error"
    if "asyncio" in text or "await" in text or "async" in text:
        return "async_error"
    return "unknown"
