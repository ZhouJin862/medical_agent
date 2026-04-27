#!/usr/bin/env python3
"""
Script to run E2E (End-to-End) tests.

This script provides convenient ways to run E2E tests with different configurations.
"""
import subprocess
import sys
from pathlib import Path


def run_e2e_tests(
    verbose: bool = True,
    coverage: bool = False,
    marker: str = "e2e",
    parallel: bool = False,
    test_file: str = None,
):
    """
    Run E2E tests with specified configuration.

    Args:
        verbose: Enable verbose output
        coverage: Generate coverage report
        marker: Pytest marker to filter tests
        parallel: Run tests in parallel (requires pytest-xdist)
        test_file: Specific test file to run
    """
    # Build pytest command
    cmd = ["pytest", "-v", "--tb=short"]

    # Add marker
    if marker:
        cmd.extend(["-m", marker])

    # Add coverage if requested
    if coverage:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
        ])

    # Add parallel execution if requested
    if parallel:
        cmd.extend(["-n", "auto"])

    # Add specific test file if provided
    if test_file:
        cmd.append(test_file)
    else:
        cmd.append("tests/e2e/")

    # Print command
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}")

    # Run tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)

    return result.returncode


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run E2E tests for Medical Agent"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_false",
        dest="verbose",
        help="Reduce output verbosity",
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report",
    )
    parser.add_argument(
        "-p", "--parallel",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)",
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Specific test file to run",
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Skip coverage even if enabled by default",
    )

    args = parser.parse_args()

    # Run E2E tests
    exit_code = run_e2e_tests(
        verbose=args.verbose,
        coverage=not args.no_coverage,
        parallel=args.parallel,
        test_file=args.file,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
