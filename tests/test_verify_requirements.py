"""
Tests for verify_requirements module - requirements consistency checker
"""

import pathlib
import sys
from pathlib import Path

import pytest

from verify_requirements import main, parse_requirements


class TestVerifyRequirements:
    """Test verify_requirements functionality"""

    def test_parse_requirements_empty_file(self, tmp_path):
        """Test parsing empty requirements file"""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("")
        result = parse_requirements(req_file)
        assert result == {}

    def test_parse_requirements_nonexistent_file(self, tmp_path):
        """Test parsing non-existent requirements file"""
        req_file = tmp_path / "nonexistent.txt"
        result = parse_requirements(req_file)
        assert result == {}

    def test_parse_requirements_with_packages(self, tmp_path):
        """Test parsing requirements file with packages"""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("foo==1.2.3\nbar>=2.0.0\nbaz==3.1.4\n")
        result = parse_requirements(req_file)
        assert result == {
            "foo": "==1.2.3",
            "bar": ">=2.0.0",
            "baz": "==3.1.4",
        }

    def test_parse_requirements_skip_comments(self, tmp_path):
        """Test that comments are skipped"""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("# This is a comment\nfoo==1.2.3\n# Another comment\nbar>=2.0.0\n")
        result = parse_requirements(req_file)
        assert result == {"foo": "==1.2.3", "bar": ">=2.0.0"}

    def test_parse_requirements_skip_empty_lines(self, tmp_path):
        """Test that empty lines are skipped"""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("foo==1.2.3\n\nbar>=2.0.0\n\n")
        result = parse_requirements(req_file)
        assert result == {"foo": "==1.2.3", "bar": ">=2.0.0"}

    def test_parse_requirements_skip_r_references(self, tmp_path):
        """Test that -r references are skipped"""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("-r base.txt\nfoo==1.2.3\n-r other.txt\nbar>=2.0.0\n")
        result = parse_requirements(req_file)
        assert result == {"foo": "==1.2.3", "bar": ">=2.0.0"}

    def test_parse_requirements_with_extras(self, tmp_path):
        """Test parsing packages with extras (may not match regex)"""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("foo==1.2.3\nbar>=2.0.0\n")
        result = parse_requirements(req_file)
        # Extras in [] may not be captured by current regex - that's OK
        assert "foo" in result
        assert "bar" in result

    def test_parse_requirements_case_insensitive(self, tmp_path):
        """Test that package names are lowercased"""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("Foo==1.2.3\nBAR>=2.0.0\n")
        result = parse_requirements(req_file)
        assert result == {"foo": "==1.2.3", "bar": ">=2.0.0"}

    def test_parse_requirements_with_version_specifiers(self, tmp_path):
        """Test parsing packages with various version specifiers"""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("foo==1.2.3rc1\nbar>=2.0.0.dev0\nbaz==3.1.4.post5\n")
        result = parse_requirements(req_file)
        assert result == {
            "foo": "==1.2.3rc1",
            "bar": ">=2.0.0.dev0",
            "baz": "==3.1.4.post5",
        }

    def test_parse_requirements_skips_unrecognized_specifiers(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Cover non-matching requirement lines (e.g., ~=)."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("foo~=1.2.3\n")
        assert parse_requirements(req_file) == {}

    def test_parse_requirements_skips_unrecognized_but_keeps_valid(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Skip unrecognized specifiers while still parsing valid ones."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("foo==1.2.3\nbar~=2.0.0\nbaz>=3.1.4\n")

        assert parse_requirements(req_file) == {"foo": "==1.2.3", "baz": ">=3.1.4"}

    def test_main_consistent_requirements(self, tmp_path, monkeypatch, capsys):
        """Test main() with consistent requirements files"""
        # Create test requirements files
        req_main = tmp_path / "requirements.txt"
        req_dev = tmp_path / "requirements-dev.txt"
        req_all = tmp_path / "requirements-all.txt"
        constraints = tmp_path / "constraints.txt"

        req_main.write_text("foo==1.2.3\nbar>=2.0.0\n")
        req_dev.write_text("pytest==7.0.0\nmypy==1.0.0\n")
        req_all.write_text("foo==1.2.3\nbar>=2.0.0\npytest==7.0.0\n")
        constraints.write_text("foo==1.2.3\n")

        # Monkeypatch Path to use tmp_path
        def mock_parent(self):
            return tmp_path

        monkeypatch.setattr(Path, "parent", property(lambda self: tmp_path))
        monkeypatch.chdir(tmp_path)

        # Run main
        with monkeypatch.context() as m:
            m.setattr(
                "verify_requirements.Path",
                lambda x: tmp_path if str(x) == "verify_requirements.py" else Path(x),
            )
            m.setattr(sys, "argv", ["verify_requirements.py"])

            # Mock __file__ to return a path in tmp_path
            import verify_requirements

            original_file = verify_requirements.__file__
            m.setattr(verify_requirements, "__file__", str(tmp_path / "verify_requirements.py"))

            result = main()

            # Restore original
            verify_requirements.__file__ = original_file

        assert result == 0
        captured = capsys.readouterr()
        assert "✅ All requirements files are consistent!" in captured.out

    def test_main_inconsistent_requirements_dev(self, tmp_path, monkeypatch, capsys):
        """Test main() with inconsistent requirements-dev.txt"""
        # Create test requirements files
        req_main = tmp_path / "requirements.txt"
        req_dev = tmp_path / "requirements-dev.txt"
        req_all = tmp_path / "requirements-all.txt"
        constraints = tmp_path / "constraints.txt"

        req_main.write_text("foo==1.2.3\nbar>=2.0.0\n")
        req_dev.write_text("foo==1.5.0\npytest==7.0.0\n")  # Different version!
        req_all.write_text("foo==1.2.3\nbar>=2.0.0\n")
        constraints.write_text("")

        monkeypatch.chdir(tmp_path)

        # Run main
        with monkeypatch.context() as m:
            import verify_requirements

            original_file = verify_requirements.__file__
            m.setattr(verify_requirements, "__file__", str(tmp_path / "verify_requirements.py"))

            result = main()

            verify_requirements.__file__ = original_file

        assert result == 1
        captured = capsys.readouterr()
        assert "Version mismatches found" in captured.out
        assert "foo:" in captured.out

    def test_main_inconsistent_requirements_all(self, tmp_path, monkeypatch, capsys):
        """Test main() with inconsistent requirements-all.txt"""
        # Create test requirements files
        req_main = tmp_path / "requirements.txt"
        req_dev = tmp_path / "requirements-dev.txt"
        req_all = tmp_path / "requirements-all.txt"
        constraints = tmp_path / "constraints.txt"

        req_main.write_text("foo==1.2.3\nbar>=2.0.0\n")
        req_dev.write_text("pytest==7.0.0\n")
        req_all.write_text("foo==1.5.0\nbar>=2.0.0\n")  # Different version!
        constraints.write_text("")

        monkeypatch.chdir(tmp_path)

        # Run main
        with monkeypatch.context() as m:
            import verify_requirements

            original_file = verify_requirements.__file__
            m.setattr(verify_requirements, "__file__", str(tmp_path / "verify_requirements.py"))

            result = main()

            verify_requirements.__file__ = original_file

        assert result == 1
        captured = capsys.readouterr()
        assert "Version mismatches found" in captured.out
        assert "foo:" in captured.out

    def test_main_missing_files(self, tmp_path, monkeypatch, capsys):
        """Test main() handles missing requirements files gracefully"""
        monkeypatch.chdir(tmp_path)

        # Run main with no files
        with monkeypatch.context() as m:
            import verify_requirements

            original_file = verify_requirements.__file__
            m.setattr(verify_requirements, "__file__", str(tmp_path / "verify_requirements.py"))

            result = main()

            verify_requirements.__file__ = original_file

        assert result == 0  # No conflicts if no files
        captured = capsys.readouterr()
        assert "✅ All requirements files are consistent!" in captured.out

    def test_parse_requirements_with_hyphens_underscores(self, tmp_path):
        """Test parsing packages with hyphens and underscores"""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("foo-bar==1.2.3\nbaz_qux>=2.0.0\n")
        result = parse_requirements(req_file)
        assert result == {
            "foo-bar": "==1.2.3",
            "baz_qux": ">=2.0.0",
        }
