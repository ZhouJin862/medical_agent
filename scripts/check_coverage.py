#!/usr/bin/env python3
"""
Script to check and generate test coverage reports.

This script runs tests with coverage measurement and generates reports.
"""
import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime


def run_coverage_tests(
    source: str = "src",
    output_format: str = "term",
    fail_under: float = 80.0,
    branch_coverage: bool = True,
    html_report: bool = True,
    xml_report: bool = False,
):
    """
    Run tests with coverage measurement.

    Args:
        source: Source code directory to measure
        output_format: Report format (term, html, xml, json)
        fail_under: Minimum coverage percentage
        branch_coverage: Enable branch coverage
        html_report: Generate HTML report
        xml_report: Generate XML report

    Returns:
        Exit code from pytest
    """
    # Build pytest command
    cmd = [
        "pytest",
        "-v",
        "--tb=short",
        f"--cov={source}",
        f"--cov-report=term-missing",
    ]

    # Add branch coverage if requested
    if branch_coverage:
        cmd.append("--cov-branch")

    # Add HTML report
    if html_report:
        cmd.append("--cov-report=html:htmlcov")

    # Add XML report
    if xml_report:
        cmd.append("--cov-report=xml:coverage.xml")

    # Add fail under threshold
    cmd.append(f"--cov-fail-under={fail_under}")

    # Add test paths
    cmd.append("tests/")

    # Print command
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}")
    print(f"Coverage Analysis")
    print(f"{'='*60}")
    print(f"Source: {source}")
    print(f"Fail Under: {fail_under}%")
    print(f"Branch Coverage: {branch_coverage}")
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    # Run tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)

    print(f"\n{'='*60}")
    print(f"Coverage analysis completed at {datetime.now().isoformat()}")
    print(f"Exit code: {result.returncode}")
    print(f"{'='*60}")

    if html_report:
        print(f"\nHTML report generated: htmlcov/index.html")
        print(f"Open in browser: file://{Path.cwd() / 'htmlcov' / 'index.html'}")

    if xml_report:
        print(f"\nXML report generated: coverage.xml")

    return result.returncode


def generate_coverage_badge():
    """Generate a coverage badge for README."""
    # This would parse coverage output and generate a badge
    print("\nTo generate coverage badge:")
    print("1. Install coverage-badge: pip install coverage-badge")
    print("2. Run: coverage-badge -o coverage.svg")
    print("3. Add to README: ![Coverage](coverage.svg)")


def get_coverage_summary():
    """Parse and display coverage summary."""
    # Try to read .coverage file
    coverage_file = Path(".coverage")
    if not coverage_file.exists():
        print("\nNo coverage data found. Run tests first.")
        return

    print("\n" + "="*60)
    print("COVERAGE SUMMARY")
    print("="*60)
    print("\nFor detailed report, check:")
    print("- Terminal output (above)")
    print("- HTML report: htmlcov/index.html")
    print("- XML report: coverage.xml (if generated)")
    print("="*60)


def print_coverage_guidelines():
    """Print guidelines for improving test coverage."""
    print(f"\n{'='*60}")
    print("COVERAGE IMPROVEMENT GUIDELINES")
    print(f"{'='*60}\n")

    guidelines = [
        ("Target Coverage", "Aim for > 80% overall coverage"),
        ("", ""),
        ("Critical Paths", "Focus on high-value code paths:"),
        ("", "- API endpoints and controllers"),
        ("", "- Business logic and domain services"),
        ("", "- Data access and repositories"),
        ("", "- Error handling and edge cases"),
        ("", ""),
        ("Test Types", "Use appropriate test types:"),
        ("", "- Unit tests for pure functions"),
        ("", "- Integration tests for components"),
        ("", "- E2E tests for critical flows"),
        ("", ""),
        ("Missing Coverage", "Address missing coverage:"),
        ("", "- Add tests for unexecuted branches"),
        ("", "- Test error conditions"),
        ("", "- Cover edge cases and boundaries"),
        ("", "- Mock external dependencies"),
        ("", ""),
        ("Quality Over Quantity", "Coverage is a tool, not a goal:"),
        ("", "- Focus on meaningful tests"),
        ("", "- Test behavior, not implementation"),
        ("", "- Maintain test readability"),
        ("", "- Review and refactor tests"),
        ("", ""),
        ("Regular Checks", "Make coverage part of workflow:"),
        ("", "- Run coverage before commits"),
        ("", "- Include in CI/CD pipeline"),
        ("", "- Track coverage trends"),
        ("", "- Set minimum thresholds"),
    ]

    for title, text in guidelines:
        if title:
            print(f"{title}")
        if text:
            print(text)

    print(f"\n{'='*60}\n")


def print_module_coverage_targets():
    """Print coverage targets for key modules."""
    print(f"\n{'='*60}")
    print("MODULE COVERAGE TARGETS")
    print(f"{'='*60}\n")

    targets = [
        ("Domain Layer", "90%", "Core business logic"),
        ("Application Layer", "85%", "Application services"),
        ("Infrastructure Layer", "75%", "External integrations"),
        ("Interface Layer", "80%", "API controllers"),
        ("", "", ""),
        ("Critical Modules", "Target", "Notes"),
        ("-" * 40, "-" * 10, "-" * 30),
        ("domain/shared/", "95%", "Value objects, enums"),
        ("domain/consultation/", "90%", "Consultation aggregate"),
        ("domain/health_plan/", "90%", "Health plan aggregate"),
        ("application/services/", "85%", "Application services"),
        ("interface/api/", "80%", "REST API endpoints"),
        ("infrastructure/llm/", "70%", "LLM adapters"),
        ("infrastructure/database/", "75%", "Database models"),
    ]

    for module, target, notes in targets:
        print(f"{module:40} {target:10} {notes:30}")

    print(f"\n{'='*60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check test coverage for Medical Agent"
    )
    parser.add_argument(
        "-s", "--source",
        type=str,
        default="src",
        help="Source code directory to measure",
    )
    parser.add_argument(
        "-f", "--fail-under",
        type=float,
        default=80.0,
        help="Minimum coverage percentage (default: 80)",
    )
    parser.add_argument(
        "--no-branch",
        action="store_true",
        help="Disable branch coverage",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Skip HTML report generation",
    )
    parser.add_argument(
        "--xml",
        action="store_true",
        help="Generate XML report",
    )
    parser.add_argument(
        "--guidelines",
        action="store_true",
        help="Show coverage improvement guidelines",
    )
    parser.add_argument(
        "--targets",
        action="store_true",
        help="Show module coverage targets",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show coverage summary only",
    )

    args = parser.parse_args()

    # Show guidelines if requested
    if args.guidelines:
        print_coverage_guidelines()
        return 0

    # Show targets if requested
    if args.targets:
        print_module_coverage_targets()
        return 0

    # Show summary if requested
    if args.summary:
        get_coverage_summary()
        return 0

    # Run coverage tests
    return run_coverage_tests(
        source=args.source,
        fail_under=args.fail_under,
        branch_coverage=not args.no_branch,
        html_report=not args.no_html,
        xml_report=args.xml,
    )


if __name__ == "__main__":
    sys.exit(main())
