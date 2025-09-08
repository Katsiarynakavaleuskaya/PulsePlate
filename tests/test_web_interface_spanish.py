"""
Tests for Web Interface Spanish Language Support

This test ensures that the web interface correctly supports Spanish language selection.
"""

import os

from fastapi.testclient import TestClient

from app import app


class TestWebInterfaceSpanish:
    """Test web interface Spanish language support."""

    def setup_method(self):
        """Set up test client."""
        os.environ["API_KEY"] = "test_key"
        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up test environment."""
        if "API_KEY" in os.environ:
            del os.environ["API_KEY"]

    def test_web_interface_contains_spanish_option(self):
        """Test that the web interface contains Spanish language option."""
        # Test that the root endpoint returns HTML with Spanish option
        response = self.client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # Check that the response contains Spanish language option
        html_content = response.text
        assert "Español" in html_content
        assert 'value="es"' in html_content
        assert "language-selector" in html_content

    def test_web_interface_form_labels_spanish(self):
        """Test that form labels are correctly translated to Spanish."""
        # Get the web interface with Spanish language
        response = self.client.get("/?lang=es")
        assert response.status_code == 200

        html_content = response.text

        # Check for Spanish form labels
        assert "Peso (kg)" in html_content
        assert "Altura (m)" in html_content
        assert "Edad" in html_content
        assert "Género" in html_content
        assert "Embarazada" in html_content
        assert "Atleta" in html_content
        assert "Cintura (cm, opcional)" in html_content
        assert "Calcular IMC" in html_content

    def test_web_interface_translations_loaded(self):
        """Test that translation script is loaded in the web interface."""
        # Get the web interface
        response = self.client.get("/")
        assert response.status_code == 200

        html_content = response.text

        # Check that translation script is present
        assert "const translations" in html_content
        assert "es:" in html_content
        assert "ru:" in html_content
        assert "en:" in html_content
