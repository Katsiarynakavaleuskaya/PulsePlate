"""Guard native Ruby dependency source, compatibility and advisory contracts."""

from pathlib import Path

import yaml

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


def test_rubyzip_guard_is_wired_after_native_setup_without_replacing_jwt_guard() -> None:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["jwt_fastlane_unblock_guard"]
    steps = job["steps"]
    setup = next(index for index, step in enumerate(steps) if step.get("name") == "Setup Ruby")
    rubyzip = next(
        index
        for index, step in enumerate(steps)
        if step.get("run") == "ruby scripts/ci/check_rubyzip_fastlane.rb"
    )
    jwt = next(
        index
        for index, step in enumerate(steps)
        if step.get("run") == "python3 scripts/ci/check_jwt_fastlane_unblock.py"
    )
    native_tests = next(
        index
        for index, step in enumerate(steps)
        if step.get("run") == "ruby tests/test_rubyzip_fastlane.rb"
    )
    assert setup < native_tests < rubyzip < jwt
    assert steps[setup]["with"]["ruby-version"] == "3.4.10"
    assert steps[setup]["with"]["bundler"] == "2.4.22"
    assert "continue-on-error" not in steps[rubyzip]
    assert "if" not in steps[rubyzip]
    assert "continue-on-error" not in steps[native_tests]
    assert "if" not in steps[native_tests]
    guard = (REPO_ROOT / "scripts/ci/check_rubyzip_fastlane.rb").read_text(encoding="utf-8")
    assert "gem 'bundler', '= 2.4.22'" in guard
    native_fixture = REPO_ROOT / "tests/test_rubyzip_fastlane.rb"
    assert native_fixture.is_file()
