"""Tests for StubProvider."""

from providers.stub import StubProvider


def test_stub_provider_initialization():
    """Test StubProvider initialization."""
    provider = StubProvider()

    assert provider.name == "stub"


def test_stub_provider_generate():
    """Test StubProvider generate method."""
    provider = StubProvider()
    text = "Test input text for stub provider"

    result = provider.generate(text)

    # Check that the result contains expected elements
    assert "stub" in result
    assert "Insight:" in result
    assert text[:120] in result  # Should include the first 120 characters of input


def test_stub_provider_generate_long_text():
    """Test StubProvider with long text input."""
    provider = StubProvider()
    long_text = "A" * 200  # 200 character string

    result = provider.generate(long_text)

    # Should only include first 120 characters
    assert long_text[:120] in result
    assert long_text[120:] not in result  # Should not include characters beyond 120


def test_stub_provider_generate_empty_text():
    """Test StubProvider with empty text input."""
    provider = StubProvider()
    text = ""

    result = provider.generate(text)

    assert "stub" in result
    assert "Insight:" in result
    assert text in result
