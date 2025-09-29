"""
Simple microbenchmark for the DataCompare Polars comparison function.

This uses pytest-benchmark to measure the performance of comparing two
Polars DataFrames with the core `compare_dataframes` function. The data sizes
here are intentionally small enough to keep the test fast while still
exercising hot paths.
"""

import polars as pl

try:
    from compare import compare_dataframes  # Import from the project package
except ImportError:
    # Fallback for package names if the project structure changes
    from data_compare import compare_dataframes


def test_compare_speed(benchmark):
    """
    Benchmark the speed of comparing two simple DataFrames.

    This function creates two DataFrames with matching `id` and `value` columns
    and then runs the comparison. The benchmark measures the time taken to run
    the comparison function once.
    """
    df1 = pl.DataFrame({"id": range(10_000), "value": range(10_000)})
    df2 = pl.DataFrame({"id": range(10_000), "value": range(10_000)})

    def run():
        compare_dataframes(
            df1,
            df2,
            keys=["id"],
            file1_name="file1",
            file2_name="file2",
        )

    # Run the benchmark on the comparison function
    benchmark(run)
