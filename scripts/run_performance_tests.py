#!/usr/bin/env python3
"""
Script to run performance tests.

This script provides convenient ways to run performance tests with different configurations.
"""
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime


def run_performance_tests(
    verbose: bool = True,
    iterations: int = None,
    test_file: str = None,
    output_format: str = "text",
):
    """
    Run performance tests with specified configuration.

    Args:
        verbose: Enable verbose output
        iterations: Number of iterations for tests
        test_file: Specific test file to run
        output_format: Output format (text, json, html)

    Returns:
        Exit code from pytest
    """
    # Build pytest command
    cmd = ["pytest", "-v", "--tb=short", "-m", "performance"]

    # Add iterations if specified
    if iterations:
        # Pass as pytest marker expression or env var
        import os
        os.environ["PERF_ITERATIONS"] = str(iterations)

    # Add specific test file if provided
    if test_file:
        cmd.append(test_file)
    else:
        cmd.append("tests/performance/")

    # Add output options
    if output_format == "json":
        cmd.extend(["--json-report", "--json-report-file=performance_report.json"])

    # Print command
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}")
    print(f"Starting performance tests at {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    # Run tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)

    print(f"\n{'='*60}")
    print(f"Performance tests completed at {datetime.now().isoformat()}")
    print(f"Exit code: {result.returncode}")
    print(f"{'='*60}")

    return result.returncode


def generate_performance_report():
    """Generate a performance report from test results."""
    # This would parse pytest output and generate a report
    # For now, just print a placeholder
    print("\n" + "="*60)
    print("PERFORMANCE REPORT")
    print("="*60)
    print("\nTo generate detailed reports:")
    print("1. Run tests with --json-report flag")
    print("2. Parse the JSON output")
    print("3. Generate HTML report with trends")
    print("\nReports would include:")
    print("- Response time percentiles (p50, p95, p99)")
    print("- Comparison against thresholds")
    print("- Historical trends")
    print("- Performance degradation alerts")
    print("="*60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run performance tests for Medical Agent"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_false",
        dest="verbose",
        help="Reduce output verbosity",
    )
    parser.add_argument(
        "-i", "--iterations",
        type=int,
        help="Number of iterations for each test",
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Specific test file to run",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        choices=["text", "json", "html"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate performance report after tests",
    )

    args = parser.parse_args()

    # Run performance tests
    exit_code = run_performance_tests(
        verbose=args.verbose,
        iterations=args.iterations,
        test_file=args.file,
        output_format=args.output,
    )

    # Generate report if requested
    if args.report:
        generate_performance_report()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
