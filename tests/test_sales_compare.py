import polars as pl
from pathlib import Path
from compare import compare_dataframes


def test_compare_sales():
    """Test compare_dataframes using pre-generated sales CSV files."""
    # Determine file paths for the pre-generated CSVs relative to this file
    base_path = Path(__file__).parent / "data"
    df1_read = pl.read_csv(base_path / "sales1.csv")
    df2_read = pl.read_csv(base_path / "sales2.csv")

    # Ensure shapes are as expected
    assert df1_read.shape == (100_000, 10)
    assert df2_read.shape == (100_000, 10)

    # Run comparison on the provided data
    (
        missing_in_file1,
        missing_in_file2,
        mismatches,
        duplicates_file1,
        duplicates_file2,
        unpivoted_mismatches,
        shape1,
        shape2,
    ) = compare_dataframes(
        df1_read,
        df2_read,
        keys=["id"],
        file1_name="sales1",
        file2_name="sales2",
    )

    # Validate the shapes returned by compare_dataframes
    assert shape1 == (100_000, 10)
    assert shape2 == (100_000, 10)

    # There should be some mismatches due to differences between the files
    assert mismatches.shape[0] > 0
