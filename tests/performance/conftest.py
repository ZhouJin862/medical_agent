"""
Configuration and fixtures for performance tests.
"""
import pytest
import time
from typing import Dict, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PerformanceReport:
    """Performance test report."""

    test_name: str
    iterations: int
    durations: List[float] = field(default_factory=list)
    threshold: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def get_statistics(self) -> Dict[str, float]:
        """Calculate statistics."""
        if not self.durations:
            return {}

        from statistics import mean, median, stdev

        sorted_durations = sorted(self.durations)
        count = len(sorted_durations)

        return {
            "count": count,
            "mean": mean(sorted_durations),
            "median": median(sorted_durations),
            "min": min(sorted_durations),
            "max": max(sorted_durations),
            "stdev": stdev(sorted_durations) if count > 1 else 0,
            "p50": sorted_durations[int(count * 0.5)],
            "p95": sorted_durations[int(count * 0.95)] if count >= 20 else sorted_durations[-1],
            "p99": sorted_durations[int(count * 0.99)] if count >= 100 else sorted_durations[-1],
        }


@pytest.fixture
def performance_report():
    """Create a performance report for tracking test results."""

    class ReportCollector:
        def __init__(self):
            self.reports: List[PerformanceReport] = []

        def add_report(self, report: PerformanceReport):
            self.reports.append(report)

        def get_summary(self) -> Dict[str, Any]:
            """Get summary of all reports."""
            return {
                "total_tests": len(self.reports),
                "tests": [
                    {
                        "name": r.test_name,
                        "iterations": r.iterations,
                        "stats": r.get_statistics(),
                    }
                    for r in self.reports
                ],
            }

        def print_summary(self):
            """Print performance summary."""
            print("\n" + "=" * 80)
            print("PERFORMANCE TEST SUMMARY")
            print("=" * 80)

            for report in self.reports:
                stats = report.get_statistics()
                print(f"\n{report.test_name}:")
                print(f"  Iterations: {stats.get('count', 0)}")
                print(f"  Mean: {stats.get('mean', 0):.3f}s")
                print(f"  P50: {stats.get('p50', 0):.3f}s")
                print(f"  P95: {stats.get('p95', 0):.3f}s")
                print(f"  P99: {stats.get('p99', 0):.3f}s")

            print("\n" + "=" * 80)

    return ReportCollector()


@pytest.fixture
def performance_thresholds():
    """Provide performance threshold configurations."""
    return {
        "simple_query": {
            "max_p50": 0.5,
            "max_p95": 1.0,
            "max_p99": 1.5,
        },
        "health_assessment": {
            "max_p50": 1.0,
            "max_p95": 2.0,
            "max_p99": 2.5,
        },
        "complex_workflow": {
            "max_p50": 1.5,
            "max_p95": 3.0,
            "max_p99": 4.0,
        },
        "skill_execution": {
            "max_p50": 0.8,
            "max_p95": 1.5,
            "max_p99": 2.0,
        },
    }


@pytest.fixture
def benchmark():
    """
    Benchmark fixture for measuring code execution time.

    Usage:
        async def test_something(benchmark):
            async def operation():
                # code to benchmark
                pass

            result = await benchmark(operation, iterations=100)
            assert result["mean"] < 0.1
    """

    async def run_benchmark(
        func: Callable,
        iterations: int = 10,
        warmup: int = 2,
    ) -> Dict[str, Any]:
        """
        Run a benchmark on the given function.

        Args:
            func: Async function to benchmark
            iterations: Number of iterations
            warmup: Number of warmup iterations

        Returns:
            Dictionary with benchmark results
        """
        durations = []

        # Warmup
        for _ in range(warmup):
            try:
                await func()
            except Exception:
                pass

        # Measured iterations
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                result = await func()
                duration = time.perf_counter() - start
                durations.append(duration)
            except Exception as e:
                duration = time.perf_counter() - start
                durations.append(duration)
                raise

        from statistics import mean, median, stdev

        sorted_durations = sorted(durations)
        count = len(sorted_durations)

        return {
            "iterations": count,
            "durations": durations,
            "mean": mean(sorted_durations),
            "median": median(sorted_durations),
            "min": min(sorted_durations),
            "max": max(sorted_durations),
            "stdev": stdev(sorted_durations) if count > 1 else 0,
            "p50": sorted_durations[int(count * 0.5)],
            "p95": sorted_durations[int(count * 0.95)] if count >= 20 else sorted_durations[-1],
            "p99": sorted_durations[int(count * 0.99)] if count >= 100 else sorted_durations[-1],
            "result": result if durations else None,
        }

    return run_benchmark


@pytest.fixture
def memory_profiler():
    """
    Memory profiler fixture for tracking memory usage.

    Usage:
        def test_memory(memory_profiler):
            with memory_profiler.profile():
                # code to profile
                pass
    """

    import tracemalloc
    import gc

    class MemoryProfiler:
        def __init__(self):
            self.snapshots = []

        def start(self):
            """Start memory tracking."""
            tracemalloc.start()
            gc.collect()

        def snapshot(self, label: str = ""):
            """Take a memory snapshot."""
            if not tracemalloc.is_tracing():
                self.start()

            current, peak = tracemalloc.get_traced_memory()
            self.snapshots.append({
                "label": label,
                "timestamp": datetime.now(),
                "current_mb": current / 1024 / 1024,
                "peak_mb": peak / 1024 / 1024,
            })

        def get_summary(self) -> Dict[str, Any]:
            """Get memory usage summary."""
            if not self.snapshots:
                return {}

            return {
                "snapshots": self.snapshots,
                "peak_current_mb": max(s["current_mb"] for s in self.snapshots),
                "peak_overall_mb": max(s["peak_mb"] for s in self.snapshots),
            }

        def stop(self):
            """Stop memory tracking."""
            tracemalloc.stop()

    return MemoryProfiler()


# Performance markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
