"""
RU: Anti-duplication guard — no BMI math outside core/bmi (with whitelist).
EN: Anti-duplication guard — no BMI math outside core/bmi (with whitelist).

Commit 4: prevents BMI formulas/thresholds from creeping into app/web/iOS adapters.

This guard enforces the canonical BMI rule: all BMI math MUST live only in core/bmi/*.
"""

from __future__ import annotations

import re
import os
import sys
from pathlib import Path
from typing import Final

import pytest

_DEBUG_GUARD: Final[bool] = bool(os.environ.get("REPO_POLICY_GUARD_DEBUG"))

REPO_ROOT = Path(__file__).resolve().parents[1]

# Whitelist: paths where BMI math is allowed (temporary or canonical)
#
# POLICY: Each whitelist entry MUST have:
#   - Comment explaining WHY it's allowed
#   - Reference to PR/issue tracking cleanup (if temporary)
#   - No silent additions (always document rationale)
#
WHITELIST_PARTS = [
    "core/bmi/",  # Canonical location ✅ (permanent)
    "tests/",  # Test code allowed ✅ (permanent)
    # NOTE: legacy_app.py removed from whitelist (PR-502) — now uses core proxies only
    "docs/",  # Documentation formulas OK ✅ (permanent)
    "bmi_core.py",  # TEMP: legacy oracle for golden parity tests (PR-455 Commit 4)
    ".venv/",  # Virtual environment (exclude from scanning)
    ".venv-ci/",  # CI virtual environment (exclude from scanning)
    # TEMP: Visualization thresholds for charts (not core BMI logic)
    # Tracked in PR-456: migrate to use core/bmi/engine.py thresholds
    "bmi_visualization.py",
    # TEMP: PRO endpoint (separate from Free BMI, uses local calc_bmi helper)
    # Tracked in PR-456: migrate to use core/bmi/engine.py
    "app/routers/bmi_pro.py",
    "core/nutrition_",  # Nutrition constants (not BMI math, different domain)
    # NOTE: core/bmi_extras is whitelisted for BMI calculations, but thresholds must come from core/bmi/risk
    # Guard test will still catch hardcoded thresholds (18.5/25/30/0.95/0.80) even in whitelisted files
    "core/bmi_extras",  # PRO features (separate from Free BMI canonical engine)
    "app/schemas/bmi.py",  # Schema Field descriptions (documentation, not code)
    "tests_strict/",  # Strict test suite (test code)
    # Uses BMI for nutrition analysis context (not core BMI calculation logic)
    "core/nutrition_bayesian_analyzer.py",
    # NOTE: bodyfat.py NOT whitelisted — guard regex excludes 94.42 via negative lookahead
]

# Forbidden patterns (domain signatures for BMI math)
# Pattern 1: BMI formula (weight / height^2) - must be in context of BMI calculation
# More specific: look for BMI-related context (bmi =, calc_bmi, etc.)
BMI_FORMULA_RE = re.compile(
    r"(bmi\s*=|calc_bmi|calculate.*bmi|bmi_value).*weight(_kg)?\s*/\s*\(\s*height(_m|_cm)?\s*\*\*\s*2|"
    r"weight(_kg)?\s*/\s*\(\s*height(_m|_cm)?\s*\*\*\s*2.*bmi",
    re.IGNORECASE,
)

# Pattern 2: BMI thresholds (canonical values) - must be in BMI context
# Look for BMI-related keywords nearby (bmi, category, threshold, etc.)
# Includes 24.9 (healthy range max) per PR-502 enforcement
# NOTE: Also detects WHR thresholds (0.95/0.80/0.90/0.85) outside core/bmi/risk.py
# Numeric thresholds pattern (factored out to avoid duplication)
_NUMERIC_THRESHOLDS = (
    r"(?:"
    r"18\.5|24\.9|25\.0|30\.0|35\.0|40\.0|"
    r"17\.5|26\.0|27\.0|24\.5|"
    r"0\.95|0\.80|0\.90|0\.85"
    r")"
)

BMI_THRESHOLDS_RE = re.compile(
    rf"(bmi|category|threshold|underweight|normal|overweight|obesity|healthy|whr|waist.*hip).*"
    rf"\b{_NUMERIC_THRESHOLDS}\b|"
    rf"\b{_NUMERIC_THRESHOLDS}\b.*"
    rf"(bmi|category|threshold|underweight|normal|overweight|obesity|healthy|whr|waist.*hip)",
    re.IGNORECASE,
)

# Pattern 3: WHtR formula (waist / 100 / height)
WHTR_FORMULA_RE = re.compile(
    r"waist(_cm)?\s*/\s*100(\.0)?\s*/\s*height(_m)?|wht(r|_ratio)\s*=\s*.*waist.*height",
    re.IGNORECASE,
)

# Pattern 4: Waist circumference thresholds (WHO/clinical values) - PR-502 enforcement
# Detects hardcoded waist risk thresholds (80/88 female, 94/102 male)
# Uses negative lookahead (?!\.) to avoid matching 94.42 (US Navy bodyfat constant)
WAIST_THRESHOLDS_RE = re.compile(
    r"(waist|risk|warn|high|threshold|central|abdominal).*"
    r"\b(80|88|94|102)(?!\.)\b|"
    r"\b(80|88|94|102)(?!\.)\b.*"
    r"(waist|risk|warn|high|threshold|central|abdominal)",
    re.IGNORECASE,
)

# Skip comment-only lines and docstrings (to avoid false positives from documentation)
SKIP_LINE_RE = re.compile(r"^\s*#|^\s*\"\"\"|^\s*'''|description=|Field\(.*description")

# Skip lines that are clearly not BMI math (docstrings, type hints, etc.)
SKIP_CONTEXT_RE = re.compile(
    r"description=|Field\(|#|docstring|type:|->|def.*\(.*\)\s*->|:.*float.*="
)


def _update_docstring_state(
    line: str, in_docstring: bool, doc_quote: str | None
) -> tuple[bool, str | None]:
    """
    Track triple-quoted docstrings robustly.

    Handles:
    - Single-line docstrings: '''x''' or \"\"\"x\"\"\"
    - Multiple occurrences per line by parity (odd/even count)
    - Avoids closing \"\"\" with ''' (and vice versa)

    Args:
        line: Current line to analyze
        in_docstring: Current docstring state
        doc_quote: Type of quote that opened docstring ('\"\"\"' or \"'''\") or None

    Returns:
        Tuple of (updated in_docstring state, updated doc_quote type)
    """
    dq = '"""'
    sq = "'''"

    # When not inside docstring, ignore triple-quotes in comments
    scan = line
    if not in_docstring:
        scan = scan.split("#", 1)[0]

    dq_count = scan.count(dq)
    sq_count = scan.count(sq)

    if not in_docstring:
        # Entering docstring: if any triple quotes appear, choose which one opens first
        if dq_count or sq_count:
            first_dq = scan.find(dq) if dq_count else 10**9
            first_sq = scan.find(sq) if sq_count else 10**9
            opener = dq if first_dq < first_sq else sq
            # Parity: if opener occurs odd times -> enter, else stay out (opened+closed same line)
            opener_count = dq_count if opener == dq else sq_count
            if opener_count % 2 == 1:
                return True, opener
            return False, None
        return False, None

    # Already inside docstring: only the same quote type can close it
    assert doc_quote in (dq, sq), f"Unexpected doc_quote: {doc_quote!r} (expected {dq!r} or {sq!r})"
    close_count = scan.count(doc_quote)
    if close_count % 2 == 1:
        return False, None
    return True, doc_quote


def _is_whitelisted(rel_path: str) -> bool:
    """Check if path is in whitelist."""
    return any(part in rel_path for part in WHITELIST_PARTS)


def _should_skip_threshold_check(rel_path: str) -> bool:
    """
    Check if threshold regex checks should be skipped for this path.

    Special case: core/bmi_extras is whitelisted for BMI math calculations,
    but threshold checks must still run to prevent hardcoded thresholds outside core/bmi/risk.
    """
    # core/bmi_extras is whitelisted for math, but thresholds must be checked
    if "core/bmi_extras" in rel_path:
        return False
    return _is_whitelisted(rel_path)


def _scan(
    pattern: re.Pattern[str], description: str, skip_threshold_check: bool = False
) -> list[str]:
    """
    Scan repository for forbidden patterns.

    Args:
        pattern: Regex pattern to search for
        description: Description for error messages
        skip_threshold_check: If True, use special logic for threshold checks
            (core/bmi_extras must still be checked even if whitelisted)

    Returns:
        List of hits in format "file:line: content"
    """
    hits: list[str] = []
    for path in REPO_ROOT.rglob("*.py"):
        try:
            rel = str(path.relative_to(REPO_ROOT))
        except ValueError:
            # Path not relative to REPO_ROOT (shouldn't happen, but defensive)
            continue
        # For threshold checks, use special logic (core/bmi_extras must be checked)
        if skip_threshold_check:
            if _should_skip_threshold_check(rel):
                continue
        else:
            if _is_whitelisted(rel):
                continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            in_docstring = False
            doc_quote: str | None = None
            for idx, line in enumerate(text, start=1):
                # Track docstring state FIRST (before SKIP_LINE_RE check)
                # This ensures docstring state is updated even for lines that start with """
                in_docstring, doc_quote = _update_docstring_state(line, in_docstring, doc_quote)
                # Skip lines inside docstrings
                if in_docstring:
                    continue
                # Skip comment-only lines and docstring markers (after docstring state check)
                if SKIP_LINE_RE.match(line):
                    continue
                # Skip docstrings and type hints (but keep BMI/WHR-related lines)
                lower = line.lower()
                if SKIP_CONTEXT_RE.search(line) and not any(
                    k in lower for k in ("bmi", "whr", "waist", "hip")
                ):
                    continue
                if pattern.search(line):
                    hits.append(f"{rel}:{idx}: {line.strip()}")
        except (OSError, UnicodeDecodeError) as e:
            # Skip files that can't be read (permissions, etc.).
            if _DEBUG_GUARD:
                print(
                    f"REPO_POLICY_GUARD_DEBUG: skip unreadable file {rel}: {e!r}", file=sys.stderr
                )
            continue

    return hits


def test_no_bmi_formula_outside_core() -> None:
    """
    RU: Проверяет, что формула BMI (weight / height^2) не встречается вне whitelist.
    EN: Ensures BMI formula (weight / height^2) is not found outside whitelist.
    """
    hits = _scan(BMI_FORMULA_RE, "BMI formula")
    assert not hits, (
        f"BMI formula found outside core/bmi (violates canonical rule):\n"
        f"{chr(10).join(f'  {hit}' for hit in hits)}\n\n"
        "Move BMI calculations to core/bmi/engine.py"
    )


# Temp file created by test_skip_context_does_not_filter_whr_thresholds; exclude from
# main guard to avoid xdist race (other worker may still have the file on disk).
_GUARD_WHR_SKIP_TEMP_BASENAME = "test_guard_whr_skip_temp.py"


def test_no_bmi_thresholds_outside_core() -> None:
    """
    RU: Проверяет, что пороги BMI (18.5, 25.0, 30.0, etc.) не встречаются вне whitelist.
    EN: Ensures BMI thresholds (18.5, 25.0, 30.0, etc.) are not found outside whitelist.

    NOTE: core/bmi_extras is whitelisted for math, but threshold checks still run
    to prevent hardcoded thresholds outside core/bmi/risk.py.
    """
    hits = _scan(BMI_THRESHOLDS_RE, "BMI thresholds", skip_threshold_check=True)
    filtered_hits: list[str] = []
    for hit in hits:
        path_part = hit.split(":", 1)[0]
        if os.path.basename(path_part) == _GUARD_WHR_SKIP_TEMP_BASENAME:
            continue
        filtered_hits.append(hit)
    hits = filtered_hits
    assert not hits, (
        "BMI thresholds found outside core/bmi (violates canonical rule):\n"
        + "\n".join(f"  {hit}" for hit in hits)
        + "\n\nMove threshold logic to core/bmi/engine.py"
    )


def test_no_whtr_formula_outside_core() -> None:
    """
    RU: Проверяет, что формула WHtR (waist / 100 / height) не встречается вне whitelist.
    EN: Ensures WHtR formula (waist / 100 / height) is not found outside whitelist.
    """
    hits = _scan(WHTR_FORMULA_RE, "WHtR formula")
    assert not hits, (
        "WHtR formula found outside core/bmi (violates canonical rule):\n"
        + "\n".join(f"  {hit}" for hit in hits)
        + "\n\nMove WHtR calculations to core/bmi/engine.py or core/bmi/risk.py"
    )


def test_no_waist_thresholds_outside_core() -> None:
    """
    RU: Проверяет, что пороги талии (80/88/94/102) не встречаются вне whitelist.
    EN: Ensures waist thresholds (80/88/94/102) are not found outside whitelist.

    PR-502: Prevents hardcoded waist risk constants from creeping back into legacy_app.py.

    NOTE: core/bmi_extras is whitelisted for math, but threshold checks still run
    to prevent hardcoded thresholds outside core/bmi/risk.py.
    """
    hits = _scan(WAIST_THRESHOLDS_RE, "waist thresholds", skip_threshold_check=True)
    assert not hits, (
        "Waist thresholds found outside core/bmi (violates canonical rule):\n"
        + "\n".join(f"  {hit}" for hit in hits)
        + "\n\nMove waist threshold logic to core/bmi/risk.py"
    )


def test_docstring_tracker_single_line_docstring_does_not_leak() -> None:
    """Test that single-line docstrings don't leak state to next line."""
    in_doc = False
    q: str | None = None
    # Single-line docstring (opening and closing on same line) should NOT toggle state
    in_doc, q = _update_docstring_state('"""doc"""', in_doc, q)
    assert in_doc is False, "Single-line docstring should not toggle state"
    assert q is None, "No quote type should be set for single-line docstring"

    in_doc, q = _update_docstring_state("'''doc'''", in_doc, q)
    assert in_doc is False, "Single-line docstring with single quotes should not toggle state"
    assert q is None, "No quote type should be set for single-line docstring"

    # Next line should be checked (not skipped)
    in_doc, q = _update_docstring_state("THRESHOLD = 25.0", in_doc, q)
    assert in_doc is False, "Line after single-line docstring should not be in docstring state"


def test_docstring_tracker_multiline_toggles_on_odd_count() -> None:
    """Test that multiline docstrings correctly toggle state."""
    in_doc = False
    q: str | None = None
    # Opening delimiter (odd count = 1)
    in_doc, q = _update_docstring_state('"""doc', in_doc, q)
    assert in_doc is True, "Opening delimiter should set in_docstring=True"
    assert q == '"""', "Quote type should be set to triple double quotes"

    # Line inside docstring (no delimiters)
    in_doc, q = _update_docstring_state("still doc", in_doc, q)
    assert in_doc is True, "Line inside docstring should keep in_docstring=True"
    assert q == '"""', "Quote type should remain unchanged"

    # Closing delimiter (odd count = 1)
    in_doc, q = _update_docstring_state('end"""', in_doc, q)
    assert in_doc is False, "Closing delimiter should set in_docstring=False"
    assert q is None, "Quote type should be cleared after closing"

    # Next line should be checked (not skipped)
    in_doc, q = _update_docstring_state("THRESHOLD = 30.0", in_doc, q)
    assert in_doc is False, "Line after closed docstring should not be in docstring state"


def test_docstring_tracker_ignores_comments_when_not_in_docstring() -> None:
    """Test that triple-quotes in comments don't affect state when not in docstring."""
    in_doc = False
    q: str | None = None
    # Triple-quotes in comment should be ignored
    in_doc, q = _update_docstring_state("# Comment with '''quotes'''", in_doc, q)
    assert in_doc is False, "Triple-quotes in comment should not toggle state when not in docstring"
    assert q is None, "No quote type should be set from comment"

    # But if we're already in docstring, comment prefix doesn't matter
    in_doc = True
    q = '"""'
    in_doc, q = _update_docstring_state("# Still in docstring", in_doc, q)
    assert in_doc is True, "Comment prefix should not affect state when already in docstring"
    assert q == '"""', "Quote type should remain unchanged"


def test_docstring_tracker_single_line_does_not_disable_scan() -> None:
    """Test that single-line docstrings don't disable guard scanning."""
    in_doc = False
    q: str | None = None
    in_doc, q = _update_docstring_state('"""summary"""', in_doc, q)
    assert in_doc is False, "Single-line docstring should not enter docstring state"
    assert q is None, "No quote type should be set for single-line docstring"


def test_docstring_tracker_multiline_enters_and_exits() -> None:
    """Test that multiline docstrings correctly enter and exit."""
    in_doc = False
    q: str | None = None
    in_doc, q = _update_docstring_state('"""start', in_doc, q)
    assert in_doc is True and q == '"""', "Opening delimiter should enter docstring state"
    in_doc, q = _update_docstring_state("still doc", in_doc, q)
    assert in_doc is True, "Line inside docstring should keep state"
    in_doc, q = _update_docstring_state('end"""', in_doc, q)
    assert in_doc is False and q is None, "Closing delimiter should exit docstring state"


def test_docstring_tracker_known_limitation_triple_quotes_in_string_literals() -> None:
    """
    Document known limitation: triple-quotes inside string literals are detected.

    Current regex-based approach detects triple-quotes even inside regular string literals.
    This is a known limitation.

    Why this is acceptable for guard tests:
    1. Such patterns are extremely rare in Python code
    2. Guard focuses on docstrings and active code patterns, not string literal content
    3. Full tokenize-based parsing would be overkill for this use case
    4. False positives from this edge case are unlikely to mask real violations

    If this becomes a problem in practice, we'd need to use Python's tokenize module
    to properly distinguish string literals from docstrings.
    """
    in_doc = False
    q: str | None = None
    # Current implementation WILL detect triple-quotes inside string literal (1 delimiter = odd = toggle)
    in_doc, q = _update_docstring_state('x = \'not a docstring """ just text\'', in_doc, q)
    # This is expected behavior with regex approach - documented limitation, not a bug
    assert (
        in_doc is True
    ), "Regex-based tracker detects triple-quotes in string literals (known limitation)"

    # Verify that next line would be incorrectly skipped (but this is rare in practice)
    # Next line has no triple-quotes, so state doesn't toggle and remains True
    in_doc, q = _update_docstring_state("THRESHOLD = 25.0  # This would be skipped", in_doc, q)
    assert (
        in_doc is True
    ), "Next line after false-positive toggle would be incorrectly skipped (known limitation)"


@pytest.mark.serial
def test_skip_context_does_not_filter_whr_thresholds() -> None:
    """Test that SKIP_CONTEXT filter does not skip WHR thresholds in type-hinted constants."""
    # Create test file outside tests/ to avoid whitelist (use app/ as it's scanned)
    test_file = REPO_ROOT / "app" / _GUARD_WHR_SKIP_TEMP_BASENAME
    try:
        test_file.write_text(
            '"""Module docstring"""\n'
            "WHR_THRESHOLD: float = 0.90  # whr threshold\n"
            "# This should be detected as a violation\n"
        )

        # Use BMI_THRESHOLDS_RE to scan the repository
        hits = _scan(BMI_THRESHOLDS_RE, "BMI threshold violation", skip_threshold_check=False)

        # Filter hits to only our test file
        test_hits = [h for h in hits if _GUARD_WHR_SKIP_TEMP_BASENAME in h]

        assert len(test_hits) > 0, "Should detect WHR threshold even with type hint"
        # Verify the violation is on line 2 (after docstring)
        assert any(
            f"{_GUARD_WHR_SKIP_TEMP_BASENAME}:2:" in h for h in test_hits
        ), "WHR threshold with type hint should not be skipped by SKIP_CONTEXT filter"
    finally:
        # Clean up: remove test file
        test_file.unlink(missing_ok=True)


def test_bmi_thresholds_re_matches_new_whr_thresholds() -> None:
    """Test that BMI_THRESHOLDS_RE matches new WHR thresholds (0.90/0.85)."""
    assert (
        BMI_THRESHOLDS_RE.search("whr threshold for males is 0.90") is not None
    ), "Should match 0.90 WHR threshold for males"
    assert (
        BMI_THRESHOLDS_RE.search("Recommended WHR (waist to hip ratio) cutoff: 0.85 for females")
        is not None
    ), "Should match 0.85 WHR threshold for females"
    assert (
        BMI_THRESHOLDS_RE.search("0.90 is the whr threshold for high risk") is not None
    ), "Should match 0.90 in WHR context"
    assert (
        BMI_THRESHOLDS_RE.search("For women, 0.85 waist hip ratio indicates elevated risk (whr)")
        is not None
    ), "Should match 0.85 in waist hip ratio context"


def test_bmi_thresholds_re_does_not_match_nearby_non_whr_thresholds() -> None:
    """Test that BMI_THRESHOLDS_RE does not match near-miss values (0.89/0.86)."""
    assert (
        BMI_THRESHOLDS_RE.search("whr of 0.89 is below the risk threshold") is None
    ), "Should not match 0.89 (near-miss, not a threshold)"
    assert (
        BMI_THRESHOLDS_RE.search("For women, a whr of 0.86 is considered borderline") is None
    ), "Should not match 0.86 (near-miss, not a threshold)"
    assert (
        BMI_THRESHOLDS_RE.search("0.89 whr value is observed in the sample") is None
    ), "Should not match 0.89 in WHR context"
    assert (
        BMI_THRESHOLDS_RE.search("0.86 waist to hip ratio (whr) recorded") is None
    ), "Should not match 0.86 in waist hip ratio context"


def test_bmi_thresholds_re_does_not_match_non_bmi_whr_context() -> None:
    """Test that 0.90/0.85 do not match outside BMI/WHR context (anti-false-positive)."""
    # These should NOT match because they lack BMI/WHR keywords (discount, accuracy, etc.)
    assert (
        BMI_THRESHOLDS_RE.search("discount rate 0.90 percent") is None
    ), "Should not match 0.90 in discount context"
    assert (
        BMI_THRESHOLDS_RE.search("accuracy 0.85 correlation") is None
    ), "Should not match 0.85 in accuracy context"
    assert (
        BMI_THRESHOLDS_RE.search("value 0.90 exceeds limit") is None
    ), "Should not match 0.90 without BMI/WHR keyword"
    assert (
        BMI_THRESHOLDS_RE.search("value 0.85 is recorded") is None
    ), "Should not match 0.85 without BMI/WHR keyword"


def test_docstring_tracker_mismatched_quotes_does_not_close() -> None:
    """Test that mismatched triple quotes do not close docstring."""
    in_doc = False
    q: str | None = None
    # Start with double quotes
    in_doc, q = _update_docstring_state('"""start', in_doc, q)
    assert in_doc is True and q == '"""', "Should enter docstring with double quotes"
    # Encounter single quotes - should NOT close (mismatched)
    in_doc, q = _update_docstring_state("still doc '''", in_doc, q)
    assert (
        in_doc is True and q == '"""'
    ), "Should remain in docstring (single quotes don't close double-quote docstring)"
    # Only matching double quotes close it
    in_doc, q = _update_docstring_state('end"""', in_doc, q)
    assert in_doc is False and q is None, "Matching double quotes should close docstring"


def test_docstring_tracker_mismatched_quotes_single_to_double() -> None:
    """Test that mismatched triple quotes (single to double) do not close docstring."""
    in_doc = False
    q: str | None = None
    # Start with single quotes
    in_doc, q = _update_docstring_state("'''start", in_doc, q)
    assert in_doc is True and q == "'''", "Should enter docstring with single quotes"
    # Encounter double quotes - should NOT close (mismatched)
    in_doc, q = _update_docstring_state('still doc """', in_doc, q)
    assert (
        in_doc is True and q == "'''"
    ), "Should remain in docstring (double quotes don't close single-quote docstring)"
    # Only matching single quotes close it
    in_doc, q = _update_docstring_state("end'''", in_doc, q)
    assert in_doc is False and q is None, "Matching single quotes should close docstring"
