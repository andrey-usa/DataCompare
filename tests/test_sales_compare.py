import sys
from pathlib import Path

import polars as pl
import pytest


def _get_compare():
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.compare import compare_dataframes  # type: ignore  # local package

    return compare_dataframes


def _series_to_list(df: pl.DataFrame, column: str) -> list:
    return df.select(column).to_series().to_list()


def test_compare_sales_summary() -> None:
    compare_dataframes = _get_compare()
    base_path = Path(__file__).parent / "data"
    df1 = pl.read_csv(base_path / "sales1.csv")
    df2 = pl.read_csv(base_path / "sales2.csv")

    results = compare_dataframes(df1, df2, keys=["id"], file1_name="sales1", file2_name="sales2")

    assert results.df1_shape == (99992, 10)
    assert results.df2_shape == (99996, 10)

    assert len(results.missing_in_file1) == 10
    assert len(results.missing_in_file2) == 5
    assert len(results.mismatches) == 92
    assert len(results.duplicates_file1) == 3
    assert len(results.duplicates_file2) == 2
    assert len(results.unpivoted_mismatches) == 294

    assert _series_to_list(results.missing_in_file1, "id") == list(range(10))
    assert _series_to_list(results.missing_in_file2, "id") == list(range(99995, 100000))
    assert set(_series_to_list(results.duplicates_file1, "id")) == {10}
    assert set(_series_to_list(results.duplicates_file2, "id")) == {99994}

    mismatch_row = results.mismatches.filter(pl.col("id") == 10).select("sales1_profit", "sales2_profit").to_dicts()[0]
    assert mismatch_row["sales1_profit"] == pytest.approx(2073.271527)
    assert mismatch_row["sales2_profit"] == pytest.approx(2112.389857)

    mismatch_detail = (
        results.unpivoted_mismatches.filter(pl.col("Identifier") == "10")
        .select("Column_Name", "Comparison")
        .to_dicts()[0]
    )
    assert mismatch_detail["Column_Name"] == "profit"
    assert mismatch_detail["Comparison"] == "2073.271527 vs 2112.389857"
