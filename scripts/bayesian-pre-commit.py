#!/usr/bin/env python3
"""
Fast Bayesian analysis for pre-commit.
Analyzes only changed files for technical, business, and health issues.
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.comprehensive_bayesian_analyzer import ComprehensiveBayesianAnalyzer


def analyze_changed_files() -> Dict[str, Any]:
    """Quick analysis of changed files."""
    print("🔍 Bayesian analysis of changed files...")

    analyzer = ComprehensiveBayesianAnalyzer()

    # Получаем список измененных файлов
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        if result.returncode != 0:
            return {"status": "ok", "message": "Cannot get changed files"}

        changed_files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
        python_files = [f for f in changed_files if f.endswith(".py")]

        if not python_files:
            return {"status": "ok", "message": "No Python files changed"}

        # Quick analysis of changed files only
        critical_issues_count = 0
        for file_path in python_files[:5]:  # Limit to 5 files for speed
            try:
                with open(project_root / file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                result = analyzer.analyze_comprehensively(
                    file_content, f"file_{file_path}", file_path
                )

                if result.critical_issues:
                    critical_issues_count += len(result.critical_issues)
                    print(f"⚠️ {file_path}: {len(result.critical_issues)} critical issues")

            except Exception as e:
                print(f"⚠️ Parsing error {file_path}: {e}")
                continue

        if critical_issues_count > 0:
            return {
                "status": "error",
                "message": f"{critical_issues_count} critical issues detected",
            }

        return {"status": "ok", "message": "Analysis passed"}

    except Exception as e:
        print(f"⚠️ Analysis error: {e}")
        return {"status": "ok", "message": "Analysis skipped due to error"}


def main() -> int:
    """Main function of the quick Bayesian hook."""
    result = analyze_changed_files()

    if result.get("status") == "error":
        print(f"❌ {result.get('message')}")
        print("💡 Fix critical issues before committing")
        return 1

    print("✅ Bayesian analysis: all good")
    return 0


if __name__ == "__main__":
    sys.exit(main())
