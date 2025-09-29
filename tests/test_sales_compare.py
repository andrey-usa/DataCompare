import polars as pl
import numpy as np
from compare import compare_dataframes


def generate_sales_data(n_rows: int = 100_000):
    """
    Generate dummy sales data with 10 columns and n_rows rows.
    Returns two Polars DataFrames: the original and a slightly modified copy.
    """
    rng = np.random.default_rng(seed=42)
    df1 = pl.DataFrame({
        "id": np.arange(n_rows),
        "product_id": rng.integers(1, 1000, size=n_rows),
        "quantity": rng.integers(1, 100, size=n_rows),
        "price": rng.random(size=n_rows) * 100.0,
        "customer_id": rng.integers(1, 10_000, size=n_rows),
        "region": rng.choice(["North", "South", "East", "West"], size=n_rows),
        "category": rng.choice(["Electronics", "Clothing", "Furniture", "Food"], size=n_rows),
        "discount": rng.random(size=n_rows) * 0.3,  # up to 30% discount
    })
    # Calculate revenue and profit columns
    df1 = df1.with_columns([
        (pl.col("quantity") * pl.col("price")).alias("revenue"),
    ])
    df1 = df1.with_columns([
        (pl.col("revenue") * (1 - pl.col("discount"))).alias("profit")
    ])

    # Clone df1 and make a slight modification to create differences
    df2 = df1.clone()
    # Increase quantity by 1 for the first 100 rows in df2
    df2 = df2.with_columns([
        pl.when(pl.col("id") < 100)
        .then(pl.col("quantity") + 1)
        .otherwise(pl.col("quantity"))
        .alias("quantity")
    ])
    return df1, df2


def test_compare_sales(tmp_path):
    df1, df2 = generate_sales_data()

    # Write the dataframes to CSV files in the temporary path
    file1 = tmp_path / "sales1.csv"
    file2 = tmp_path / "sales2.csv"
    df1.write_csv(file1)
    df2.write_csv(file2)

    # Read the CSV files back to Polars DataFrames
    df1_read = pl.read_csv(file1)
    df2_read = pl.read_csv(file2)

    # Ensure shapes are as expected
    assert df1_read.shape == (100_000, 10)
    assert df2_read.shape == (100_000, 10)

    # Run comparison on the generated data
    (
        missing_in_file1,
        missing_in_file2,
        mismatches,
        duplicates_file1,
        duplicates_file2,
        unpivoted_mismatches,
        shape1,
        shape2,
    ) = compare_dataframes(df1_read, df2_read, keys=["id"], file1_name="sales1", file2_name="sales2")

    # Validate the shapes returned by compare_dataframes
    assert shape1 == (100_000, 10)
    assert shape2 == (100_000, 10)

    # There should be some mismatches due to the quantity change in df2
    assert mismatches.shape[0] > 0
