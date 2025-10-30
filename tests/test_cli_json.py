import importlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import polars as pl
import pytest


def _uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    path = Path(url2pathname(parsed.path))
    if parsed.netloc:
        path = Path(f"//{parsed.netloc}{path}")
    return path


def _series_values(df: pl.DataFrame, column: str) -> list:
    return df.select(column).to_series().to_list()


def test_cli_json_mode_outputs_expected_results(tmp_path, capsys, monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    data_compare = importlib.import_module("src.data_compare")

    base = Path(__file__).resolve().parent / "data"
    file1 = base / "sales1.csv"
    file2 = base / "sales2.csv"

    monkeypatch.chdir(tmp_path)

    sys.argv = [
        "datacompare",
        "--json",
        "--keys",
        "id",
        str(file1),
        str(file2),
    ]

    data_compare.cli_mode()
    captured = capsys.readouterr().out.strip()

    obj = json.loads(captured)

    assert obj["file1"]["rows"] == 99992
    assert obj["file2"]["rows"] == 99996
    assert obj["keys"] == ["id"]
    assert obj["mapping_file"] is None

    expected_stats = {
        "missing_in_file1": 10,
        "missing_in_file2": 5,
        "row_mismatches": 92,
        "duplicates_file1": 3,
        "duplicates_file2": 2,
        "value_mismatches": 294,
    }
    assert obj["stats"] == expected_stats

    output_paths = [_uri_to_path(uri) for uri in obj["outputs"]]
    assert len(output_paths) == 6

    files = {path.name: pl.read_csv(path) for path in output_paths}

    assert _series_values(files["Missing_in_sales1.csv"], "id") == list(range(10))
    assert _series_values(files["Missing_in_sales2.csv"], "id") == list(range(99995, 100000))
    assert files["Duplicates_in_sales1.csv"].height == 3
    assert set(_series_values(files["Duplicates_in_sales1.csv"], "id")) == {10}
    assert files["Duplicates_in_sales2.csv"].height == 2
    assert set(_series_values(files["Duplicates_in_sales2.csv"], "id")) == {99994}
    assert files["Row_Mismatches_sales1_vs_sales2.csv"].height == 92
    assert files["Value_Unpivoted_Mismatches_sales1_vs_sales2.csv"].height == 294

    mismatches_row = (
        files["Row_Mismatches_sales1_vs_sales2.csv"]
        .filter(pl.col("id") == 10)
        .select("sales1_profit", "sales2_profit")
        .to_dicts()[0]
    )
    assert mismatches_row["sales1_profit"] == pytest.approx(2073.271527)
    assert mismatches_row["sales2_profit"] == pytest.approx(2112.389857)

    unpivot_detail = (
        files["Value_Unpivoted_Mismatches_sales1_vs_sales2.csv"]
        .with_columns(pl.col("Identifier").cast(pl.Utf8))
        .filter(pl.col("Identifier") == "10")
        .select("Column_Name", "Comparison")
        .to_dicts()[0]
    )
    assert unpivot_detail == {
        "Column_Name": "profit",
        "Comparison": "2073.271527 vs 2112.389857",
    }
