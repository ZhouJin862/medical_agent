#!/usr/bin/env python3
"""
Script to run load tests.

This script provides convenient ways to run load tests with different scenarios.
"""
import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime


def run_load_tests(
    scenario: str = "all",
    verbose: bool = True,
    output_file: str = None,
):
    """
    Run load tests with specified scenario.

    Args:
        scenario: Load test scenario (light, medium, heavy, stress, all)
        verbose: Enable verbose output
        output_file: File to write test results

    Returns:
        Exit code from pytest
    """
    # Build pytest command
    cmd = ["pytest", "-v", "-s", "--tb=short", "-m", "load"]

    # Add specific test if scenario specified
    if scenario != "all":
        test_map = {
            "light": "test_load.py::test_light_load",
            "medium": "test_load.py::test_medium_load",
            "heavy": "test_load.py::test_heavy_load",
            "stress": "test_load.py::test_heavy_load",  # Use heavy for stress
            "sustained": "test_load.py::test_sustained_load",
            "rampup": "test_load.py::test_ramp_up_load",
        }
        if scenario in test_map:
            cmd.append(f"tests/load/{test_map[scenario]}")
        else:
            print(f"Unknown scenario: {scenario}")
            print(f"Available scenarios: light, medium, heavy, stress, sustained, rampup, all")
            return 1
    else:
        cmd.append("tests/load/")

    # Print command
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}")
    print(f"Starting load tests at {datetime.now().isoformat()}")
    print(f"Scenario: {scenario}")
    print(f"{'='*60}\n")

    # Run tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)

    print(f"\n{'='*60}")
    print(f"Load tests completed at {datetime.now().isoformat()}")
    print(f"Exit code: {result.returncode}")
    print(f"{'='*60}")

    return result.returncode


def print_load_test_info():
    """Print information about load test scenarios."""
    print(f"\n{'='*60}")
    print("LOAD TEST SCENARIOS")
    print(f"{'='*60}\n")

    scenarios = [
        ("light", "10 users, 10 RPS, 60s", "Basic load test"),
        ("medium", "50 users, 50 RPS, 120s", "Normal operational load"),
        ("heavy", "100 users, 100 RPS, 180s", "Peak load test"),
        ("stress", "200 users, 200 RPS, 300s", "Stress test (extreme)"),
        ("sustained", "50 users, 2 minutes", "Sustained load over time"),
        ("rampup", "Ramp to 50 users over 30s", "Gradual ramp-up test"),
    ]

    for name, desc, purpose in scenarios:
        print(f"{name.upper():12} - {desc:30} - {purpose}")

    print(f"\n{'='*60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run load tests for Medical Agent"
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        choices=["light", "medium", "heavy", "stress", "sustained", "rampup", "all"],
        default="all",
        help="Load test scenario to run",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_false",
        dest="verbose",
        help="Reduce output verbosity",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Write test results to file",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show load test scenario information",
    )

    args = parser.parse_args()

    # Show info if requested
    if args.info:
        print_load_test_info()
        return 0

    # Run load tests
    return run_load_tests(
        scenario=args.scenario,
        verbose=args.verbose,
        output_file=args.output,
    )


if __name__ == "__main__":
    sys.exit(main())
