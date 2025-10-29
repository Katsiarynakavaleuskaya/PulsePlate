"""
Tests for verify_requirements.py to achieve 100% coverage.
"""

import runpy
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from verify_requirements import main, parse_requirements


class TestVerifyRequirements:
    """Test verify_requirements.py functionality."""

    def test_parse_requirements_nonexistent_file(self) -> None:
        """Non-existent file should yield empty mapping."""
        result = parse_requirements(Path("nonexistent.txt"))
        assert result == {}

    def test_parse_requirements_empty_file(self) -> None:
        """Empty requirements file should produce empty mapping."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write("")
            handle.flush()

        try:
            result = parse_requirements(temp_path)
            assert result == {}
        finally:
            temp_path.unlink(missing_ok=True)

    def test_parse_requirements_with_comments_and_empty_lines(self) -> None:
        """Comments, blank lines, and nested references are ignored."""
        content = """
# This is a comment
package1==1.0.0
# Another comment

package2>=2.0.0
-r requirements.txt
package3==3.0.0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
            handle.flush()
        try:
            result = parse_requirements(temp_path)
            expected = {"package1": "==1.0.0", "package2": ">=2.0.0", "package3": "==3.0.0"}
            assert result == expected
        finally:
            temp_path.unlink(missing_ok=True)

    def test_parse_requirements_with_special_characters(self) -> None:
        """Package names with dashes, underscores, and extras are parsed."""
        content = (
            "package-with-dashes==1.0.0\n"
            "package_with_underscores>=2.0.0\n"
            "package[extra]==3.0.0"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
            handle.flush()

        try:
            result = parse_requirements(temp_path)
            expected = {
                "package-with-dashes": "==1.0.0",
                "package_with_underscores": ">=2.0.0",
                "package[extra]": "==3.0.0",
            }
            assert result == expected
        finally:
            temp_path.unlink(missing_ok=True)

    def test_main_success_path(self) -> None:
        """Consistent requirement sets return success."""
        with patch("verify_requirements.parse_requirements") as mock_parse:
            mock_parse.return_value = {"package1": "==1.0.0", "package2": ">=2.0.0"}
            result = main()
            assert result == 0

    def test_main_with_version_mismatches(self) -> None:
        """Mismatched versions between files surface as errors."""
        with patch("verify_requirements.parse_requirements") as mock_parse:

            def side_effect(path: Path) -> dict:
                text_path = str(path)
                if "requirements.txt" in text_path:
                    return {"package1": "==1.0.0"}
                if "requirements-dev.txt" in text_path:
                    return {"package1": "==2.0.0"}
                return {}

            mock_parse.side_effect = side_effect
            result = main()
            assert result == 1

    def test_main_with_requirements_all_mismatch(self) -> None:
        """Differences in requirements-all also fail."""
        with patch("verify_requirements.parse_requirements") as mock_parse:

            def side_effect(path: Path) -> dict:
                text_path = str(path)
                if "requirements.txt" in text_path:
                    return {"package1": "==1.0.0"}
                if "requirements-all.txt" in text_path:
                    return {"package1": "==3.0.0"}
                return {}

            mock_parse.side_effect = side_effect
            result = main()
            assert result == 1

    def test_main_with_empty_requirements(self) -> None:
        """Completely empty files still succeed."""
        with patch("verify_requirements.parse_requirements") as mock_parse:
            mock_parse.return_value = {}
            result = main()
            assert result == 0

    def test_sys_exit_line_81(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Running the module as a script triggers sys.exit(main())."""
        exit_calls = []

        def fake_exit(code: int = 0) -> None:
            exit_calls.append(code)
            raise SystemExit(code)

        monkeypatch.setattr(sys, "exit", fake_exit)

        # Mock parse_requirements to return consistent data
        with patch("verify_requirements.parse_requirements") as mock_parse:
            mock_parse.return_value = {"package1": "==1.0.0"}

            with pytest.raises(SystemExit) as excinfo:
                runpy.run_module("verify_requirements", run_name="__main__")

            assert exit_calls == [0]
            assert excinfo.value.code == 0

    def test_script_execution_line_81(self) -> None:
        """Test script execution as subprocess to cover line 81."""
        import subprocess
        import sys
        from pathlib import Path

        # Run the script as a subprocess to trigger the if __name__ == "__main__" block
        script_path = Path(__file__).parent.parent / "verify_requirements.py"
        result = subprocess.run(
            [sys.executable, str(script_path)], capture_output=True, text=True, timeout=30
        )

        # Should exit with code 0 (success)
        assert result.returncode == 0
        # Should have some output
        assert len(result.stdout) > 0
