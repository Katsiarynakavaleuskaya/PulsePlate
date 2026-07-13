"""Guard the Ruby 3.4-compatible CFPropertyList resolver contract."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cfpropertylist_is_exactly_pinned_without_widening_fastlane_graph() -> None:
    gemfile = (REPO_ROOT / "ios" / "Gemfile").read_text(encoding="utf-8")
    lockfile = (REPO_ROOT / "ios" / "Gemfile.lock").read_text(encoding="utf-8")

    assert gemfile.splitlines()[0] == 'source "https://rubygems.org"'
    assert gemfile.count('gem "CFPropertyList", "= 3.0.8"') == 1
    assert "    CFPropertyList (3.0.8)" in lockfile
    assert "  CFPropertyList (= 3.0.8)" in lockfile

    assert 'gem "fastlane", "= 2.237.0"' in gemfile
    assert "    fastlane (2.237.0)" in lockfile
    assert "      CFPropertyList (>= 2.3, < 5.0.0)" in lockfile
    assert "      nkf (~> 0.2)" in lockfile
    assert "    nkf (0.2.0)" in lockfile
    assert "    xcodeproj (1.27.0)" in lockfile
    assert "      CFPropertyList (>= 2.3.3, < 4.0)" in lockfile
    assert lockfile.endswith("BUNDLED WITH\n   2.4.22\n")
