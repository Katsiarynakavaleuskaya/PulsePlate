#!/usr/bin/env python3
"""
Bayesian analysis of failed tests from previous or fresh runs.
Analyzes specific failed tests and provides actionable recommendations.
"""

import sys
import os
import re
import shutil
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import xml.etree.ElementTree as ET

# Add project root directory to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.comprehensive_bayesian_analyzer import ComprehensiveBayesianAnalyzer
from core.error_classifier import classify_error


def load_failed_tests_fallback() -> List[Dict[str, Any]]:
    """Load fallback failed tests from JSON config (returns [] if missing)."""
    cfg = project_root / "config" / "failed_tests_fallback.json"
    try:
        if cfg.exists():
            import json

            with open(cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
    except Exception:
        pass
    return []


# Fallback list of failed tests loaded from external config file
FAILED_TESTS_FALLBACK = load_failed_tests_fallback()


def clear_test_caches() -> None:
    """Удаляет кэш pytest/coverage/временные артефакты перед свежим прогоном."""
    candidates = [
        project_root / ".pytest_cache",
        project_root / ".cache",
        project_root / "htmlcov",
        project_root / ".coverage",
        project_root / "coverage.xml",
        project_root / "cov.xml",
        project_root / "pytest_report.json",
    ]
    for path in candidates:
        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            # Безопасно игнорируем ошибки удаления кэшей
            pass


def run_pytest_and_collect_failed() -> List[Dict[str, Any]]:
    """Запускает pytest без кэша и собирает список упавших тестов из вывода.

    Возвращает список словарей с минимально необходимой информацией для анализа.
    """
    print("\n\033[36mЗапускаю свежий прогон pytest с очисткой кэша...\033[0m")
    clear_test_caches()

    try:
        # Run pytest, generating a JUnit report
        env = os.environ.copy()
        env["SKIP_BAYESIAN_PRECOMMIT"] = "1"
        env["BAYESIAN_FRESH_RUN"] = "1"
        junit_path = project_root / "pytest_report.xml"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--maxfail=0",
                "--cache-clear",
                f"--junitxml={junit_path}",
                "-rA",
                "--tb=short",
            ],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            timeout=900,
            env=env,
        )
        output = proc.stdout or ""
    except Exception as e:
        print(f"\033[31mНе удалось запустить pytest: {e}\033[0m")
        return []

    # Сохраним лог для отладки
    try:
        log_path = project_root / "pytest_last_run.log"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"# Pytest run at {datetime.now().isoformat()}\n\n")
            f.write(output)
    except Exception:
        pass

    # Пробуем распарсить JUnit-отчет для точных причин
    failed: List[Dict[str, Any]] = []
    try:
        junit_file = project_root / "pytest_report.xml"
        if junit_file.exists():
            tree = ET.parse(str(junit_file))
            root = tree.getroot()
            for testcase in root.iter("testcase"):
                failure = testcase.find("failure")
                error = testcase.find("error")
                if failure is None and error is None:
                    continue
                node = failure or error
                class_name = testcase.attrib.get("classname", "<Module>")
                file_rel = testcase.attrib.get("file") or ""
                if not file_rel:
                    parts = class_name.split(".") if class_name else []
                    if parts:
                        try:
                            start = parts.index("tests")
                            file_rel = "/".join(parts[start:]) + ".py"
                        except ValueError:
                            file_rel = (class_name or "").replace(".", "/") + ".py"
                method_name = testcase.attrib.get("name", "<unknown>")
                message = (node.attrib.get("message") or "").strip()
                text = (node.text or "").strip()
                error_text = message if message else (text[:500] if text else "from junit report")
                category = classify_error(error_text)

                failed.append(
                    {
                        "file": file_rel,
                        "class": class_name.split(".")[-1] if class_name else "<Module>",
                        "method": method_name,
                        "error": error_text,
                        "category": category,
                        "nodeid": f"{file_rel}::{class_name}::{method_name}",
                    }
                )
    except Exception:
        pass

    if failed:
        uniq: Dict[str, Dict[str, Any]] = {}
        for item in failed:
            key = f"{item['file']}::{item['class']}::{item['method']}"
            if key not in uniq:
                uniq[key] = item
        return list(uniq.values())

    # Ищем строки вида (fallback на stdout):
    # FAILED tests/path.py::TestClass::test_name
    # ERROR tests/path.py::test_something
    pattern = re.compile(r"^(FAILED|ERROR)\s+([\w\./\\:-]+)")
    lines = output.splitlines()
    for idx, raw in enumerate(lines):
        m = pattern.match(raw.strip())
        if not m:
            continue
        _status, nodeid = m.groups()
        # nodeid формата tests/file.py::Class::test
        parts = nodeid.split("::")
        file_rel = parts[0]
        test_class = (
            parts[1]
            if len(parts) >= 3
            else (parts[1] if len(parts) == 2 and parts[1].startswith("Test") else "<Module>")
        )
        test_method = parts[-1] if len(parts) >= 2 else parts[0]

        # Извлекаем сниппет вокруг совпадения из основного вывода
        start = idx
        end = min(len(lines), idx + 25)
        snippet = "\n".join(lines[start:end])
        err_line = next((ln for ln in snippet.splitlines() if ln.strip().startswith("E   ")), None)
        error_text = err_line or snippet or "from fresh run"

        category = classify_error(error_text)

        failed.append(
            {
                "file": file_rel,
                "class": test_class,
                "method": test_method,
                "error": error_text,
                "category": category,
                "nodeid": nodeid,
            }
        )

        # примечание: не перезапускаем nodeid, чтобы избежать флаков и зависаний

    # Убираем дубликаты по file+class+method
    uniq: Dict[str, Dict[str, Any]] = {}
    for item in failed:
        key = f"{item['file']}::{item['class']}::{item['method']}"
        if key not in uniq:
            uniq[key] = item
    return list(uniq.values())


def analyze_failed_test(
    test_info: Dict[str, Any], analyzer: ComprehensiveBayesianAnalyzer
) -> Dict[str, Any]:
    """Analyze a single failed test.

    Takes a minimal test descriptor and a comprehensive analyzer,
    runs a localized analysis and returns a concise result dict
    with scores, categorized issues, and recommendations.
    """
    file_rel = test_info.get("file") or ""
    file_path = project_root / file_rel

    if (not file_rel) or (not file_path.exists()) or file_path.is_dir():
        return {
            "test": f"{test_info['class']}::{test_info['method']}",
            "status": "file_not_found",
            "file": file_rel,
        }

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        # Создаем контекст для анализа
        test_context = f"""
Test File: {test_info['file']}
Test Class: {test_info['class']}
Test Method: {test_info['method']}
Error Type: {test_info['error']}
Category: {test_info['category']}

File Content (relevant parts):
{file_content[:2000]}
"""

        # Анализируем через байесовский метод
        result = analyzer.analyze_comprehensively(
            test_context,
            f"failed_test_{test_info['class']}_{test_info['method']}",
            test_info["file"],
        )

        return {
            "test": f"{test_info['class']}::{test_info['method']}",
            "file": test_info["file"],
            "error": test_info["error"],
            "category": test_info["category"],
            "technical_score": result.technical_score,
            "business_score": result.business_score,
            "overall_score": result.overall_score,
            "critical_issues": result.critical_issues[:3],
            "optimization_opportunities": result.optimization_opportunities[:2],
            "recommendations": [],
        }

    except Exception as e:
        return {
            "test": f"{test_info['class']}::{test_info['method']}",
            "file": test_info["file"],
            "error": test_info["error"],
            "status": "analysis_error",
            "error_message": str(e),
        }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bayesian failed-tests analyzer")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Run a fresh pytest pass (clear caches) and analyze current failures",
    )
    parser.add_argument(
        "--report",
        choices=["markdown"],
        help="Emit analysis report in given format (e.g., markdown)",
    )
    return parser.parse_args()


def print_header() -> None:
    print("\033[34m" + "=" * 80 + "\033[0m")
    print("\033[34m" + "🔍 BAYESIAN ANALYSIS OF FAILED TESTS" + "\033[0m")
    print("\033[34m" + "=" * 80 + "\033[0m")


def get_failed_tests(use_fresh: bool) -> List[Dict[str, Any]]:
    if use_fresh:
        failed_tests = run_pytest_and_collect_failed()
        if not failed_tests:
            print("\n\033[33mCould not collect fresh failures. Using fallback list.\033[0m\n")
            failed_tests = FAILED_TESTS_FALLBACK
    else:
        failed_tests = FAILED_TESTS_FALLBACK
    return failed_tests


def print_statistics(failed_tests: List[Dict[str, Any]]) -> None:
    print(f"\n📊 Total failed tests: {len(failed_tests)}\n")
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for test_info in failed_tests:
        category = test_info.get("category") or classify_error(test_info.get("error", ""))
        by_category.setdefault(category, []).append(test_info)
    print("\033[36m" + "📋 Category stats:" + "\033[0m")
    for category, tests in sorted(by_category.items()):
        print(f"  {category}: {len(tests)} tests")


def analyze_tests(
    failed_tests: List[Dict[str, Any]], analyzer: ComprehensiveBayesianAnalyzer
) -> List[Dict[str, Any]]:
    print("\n" + "\033[34m" + "=" * 80 + "\033[0m")
    print("\033[36m" + "🔬 DETAILED ANALYSIS" + "\033[0m")
    print("\033[34m" + "=" * 80 + "\033[0m" + "\n")

    results: List[Dict[str, Any]] = []
    for i, test_info in enumerate(failed_tests[:15], 1):  # limit for speed
        print(
            f"\n[{i}/{len(failed_tests)}] \033[33m{test_info.get('class', '')}::{test_info.get('method', '')}\033[0m"
        )
        print(f"   File: {test_info.get('file', '')}")
        print(f"   Error: \033[31m{test_info.get('error', '')}\033[0m")
        category = test_info.get("category") or classify_error(test_info.get("error", ""))
        print(f"   Category: {category}")

        test_info = dict(test_info)
        test_info["category"] = category
        result = analyze_failed_test(test_info, analyzer)

        if result.get("status") in {"file_not_found", "analysis_error"}:
            status_msg = (
                "File not found"
                if result.get("status") == "file_not_found"
                else (f"Analysis error: {result.get('error_message', '')}")
            )
            print(f"   \033[31m❌ {status_msg}\033[0m")
            continue

        try:
            recs: List[str] = []
            if isinstance(result.get("critical_issues"), list):
                recs.extend(result["critical_issues"][:2])
            if isinstance(result.get("optimization_opportunities"), list):
                recs.extend(result["optimization_opportunities"][:3])
            result["recommendations"] = recs
        except Exception:
            pass

        results.append(result)

        print(f"   Technical score: \033[36m{result.get('technical_score', 0):.2f}\033[0m")
        print(f"   Business score: \033[36m{result.get('business_score', 0):.2f}\033[0m")
        print(f"   Overall score: \033[36m{result.get('overall_score', 0):.2f}\033[0m")

        if result.get("critical_issues"):
            print("   \033[31m❌ Critical issues:\033[0m")
            for issue in result["critical_issues"]:
                print(f"      - {issue}")
        if result.get("optimization_opportunities"):
            print("   \033[32m💡 Optimization opportunities:\033[0m")
            for opt in result["optimization_opportunities"]:
                print(f"      - {opt}")
        if result.get("recommendations"):
            print("   \033[32m📌 Recommendations:\033[0m")
            for rec in result["recommendations"]:
                print(f"      - {rec}")

    return results


def print_diagnosis(analyzer: ComprehensiveBayesianAnalyzer) -> None:
    print("\n" + "\033[34m" + "=" * 80 + "\033[0m")
    print("\033[36m" + "📊 COMPREHENSIVE DIAGNOSIS" + "\033[0m")
    print("\033[34m" + "=" * 80 + "\033[0m" + "\n")
    diagnosis = analyzer.get_comprehensive_diagnosis()
    if not diagnosis or diagnosis.get("status") != "analyzed":
        print("\033[33m⚠️ Comprehensive diagnosis is not available yet.\033[0m")
        print("   Analyze more tests to obtain a diagnosis.\n")
        return

    tech_score = diagnosis.get("technical_score", 0)
    biz_score = diagnosis.get("business_score", 0)
    system_health = diagnosis.get("system_health", "unknown")
    if isinstance(tech_score, (int, float)):
        print(f"Technical score: \033[36m{tech_score:.2f}\033[0m")
    else:
        print(f"Technical score: \033[36m{tech_score}\033[0m")
    if isinstance(biz_score, (int, float)):
        print(f"Business score: \033[36m{biz_score:.2f}\033[0m")
    else:
        print(f"Business score: \033[36m{biz_score}\033[0m")

    health_colors = {
        "excellent": "\033[32m",
        "good": "\033[36m",
        "fair": "\033[33m",
        "poor": "\033[31m",
    }
    color = health_colors.get(system_health, "\033[0m")
    print(f"System health: {color}{system_health}\033[0m")

    recommendations = diagnosis.get("recommendations", [])
    if recommendations:
        print("\n\033[32m💡 FIX RECOMMENDATIONS:\033[0m")
        for i, rec in enumerate(recommendations[:10], 1):
            print(f"  {i}. {rec}")

    cost_savings = diagnosis.get("cost_savings_recommendations", [])
    revenue_growth = diagnosis.get("revenue_optimization_recommendations", [])
    if cost_savings:
        print("\n\033[33m💰 COST SAVINGS:\033[0m")
        for i, rec in enumerate(cost_savings[:5], 1):
            print(f"  {i}. {rec}")
    if revenue_growth:
        print("\n\033[32m📈 REVENUE GROWTH:\033[0m")
        for i, rec in enumerate(revenue_growth[:5], 1):
            print(f"  {i}. {rec}")


def print_top_problematic_tests(results: List[Dict[str, Any]]) -> None:
    print("\n" + "\033[34m" + "=" * 80 + "\033[0m")
    print("\033[36m" + "🎯 TOP-5 MOST PROBLEMATIC TESTS" + "\033[0m")
    print("\033[34m" + "=" * 80 + "\033[0m" + "\n")
    sorted_results = sorted(results, key=lambda x: x.get("overall_score", 0))
    for i, result in enumerate(sorted_results[:5], 1):
        print(f"{i}. \033[33m{result.get('test', '')}\033[0m")
        print(f"   File: {result.get('file', '')}")
        print(f"   Error: \033[31m{result.get('error', '')}\033[0m")
        print(f"   Score: \033[36m{result.get('overall_score', 0):.2f}\033[0m")
        if result.get("critical_issues"):
            print(f"   Problems: {len(result['critical_issues'])}")
        print()


def _write_markdown_report(
    results: List[Dict[str, Any]], analyzer: ComprehensiveBayesianAnalyzer
) -> None:
    """Write a concise markdown report to failed_tests_analysis.md."""
    out_path = project_root / "failed_tests_analysis.md"
    lines: List[str] = []
    lines.append("# Failed Tests Analysis (Local)\n")
    lines.append(f"Total analyzed: {len(results)}\n")
    if results:
        lines.append("## Details\n")
        for r in results:
            lines.append(
                f"- **{r.get('test', '')}**: score={r.get('overall_score', 0):.2f}; file={r.get('file', '')}"
            )
            if r.get("critical_issues"):
                lines.append(f"  - Critical: {', '.join(r['critical_issues'])}")
            if r.get("optimization_opportunities"):
                lines.append(f"  - Optimize: {', '.join(r['optimization_opportunities'])}")
            if r.get("recommendations"):
                lines.append(f"  - Recs: {', '.join(r['recommendations'])}")
            lines.append("")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    """Main entrypoint: orchestrate argument parsing, analysis, and printing."""
    args = parse_arguments()
    print_header()
    failed_tests = get_failed_tests(args.fresh)
    print_statistics(failed_tests)
    analyzer = ComprehensiveBayesianAnalyzer()
    results = analyze_tests(failed_tests, analyzer)
    print_diagnosis(analyzer)
    print_top_problematic_tests(results)
    if args.report == "markdown":
        _write_markdown_report(results, analyzer)
        print("\n\033[32mMarkdown report written to failed_tests_analysis.md\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
