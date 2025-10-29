#!/usr/bin/env python3
"""Nox sessions for local parity with CI.

Sessions:
- lint: ruff + black --check
- type: mypy
- tests_pr: pytest (no slow/MC/demo) + coverage xml
- tests_nightly: pytest (not demo) + coverage gates
"""

import nox


@nox.session(python="3.12")
def lint(session: nox.Session) -> None:
    session.install("-r", "requirements-dev.txt")
    session.run("ruff", ".")
    session.run("black", "--check", "--diff", ".")


@nox.session(python="3.12")
def type(session: nox.Session) -> None:
    session.install("-r", "requirements-dev.txt")
    session.run("mypy", ".")


@nox.session(python="3.12")
def tests_pr(session: nox.Session) -> None:
    session.install("-r", "requirements-dev.txt")
    session.install("-r", "requirements.txt")
    session.run(
        "pytest",
        "-c",
        "pyproject.toml",
        "-m",
        "not slow and not monte_carlo and not demo",
        "--cov=core",
        "--cov=app",
        "--cov-report=xml",
        "-ra",
        "tests",
    )
    session.run("diff-cover", "coverage.xml", "--compare-branch", "origin/main", "--fail-under", "90")


@nox.session(python="3.12")
def tests_nightly(session: nox.Session) -> None:
    session.install("-r", "requirements-dev.txt")
    session.install("-r", "requirements.txt")
    session.run(
        "pytest",
        "-c",
        "pyproject.toml",
        "-m",
        "not demo",
        "-n",
        "auto",
        "--cov=core",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "--cov-fail-under=97",
        "-ra",
    )

