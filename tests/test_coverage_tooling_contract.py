"""Focused compatibility contracts for the Coverage test tooling surface."""

from __future__ import annotations

from pathlib import Path
import runpy

import coverage


def test_coverage_html_context_is_safely_escaped(tmp_path: Path) -> None:
    raw_context = "</script><script>window.pulseplateCoverageProbe=1</script>"
    source = tmp_path / "coverage_probe.py"
    source.write_text("value = 42\n", encoding="utf-8")

    cov = coverage.Coverage(
        config_file=False,
        data_file=str(tmp_path / ".coverage"),
    )
    cov.start()
    cov.switch_context(raw_context)
    runpy.run_path(str(source))
    cov.stop()
    cov.save()

    report_dir = tmp_path / "htmlcov"
    cov.html_report(directory=str(report_dir), show_contexts=True)

    report_files = tuple(report_dir.rglob("*.html"))
    rendered_report = "\n".join(path.read_text(encoding="utf-8") for path in report_files)
    assert report_files
    assert raw_context not in rendered_report
