import polars as pl
import os
from datetime import datetime
import concurrent.futures
import time
import sys

def get_file_header(path: str) -> list[str]:
    """Quickly reads the header of a CSV or Excel file without loading the entire file."""
    if not path or not os.path.exists(path):
        return []
    try:
        path_lower = path.lower()
        if path_lower.endswith('.csv'):
            return pl.read_csv(path, n_rows=0, ignore_errors=True).columns
        elif path_lower.endswith(('.xlsx', '.xls')):
            # Use Polars' native Excel reading for headers
            return pl.read_excel(path, engine='calamine', read_options={'n_rows': 0}).columns
        else:
            # Basic fallback for other potential text files
            return pl.read_csv(path, n_rows=0, separator='\t', ignore_errors=True).columns
    except Exception as e:
        print(f"Could not read header from {os.path.basename(path)}: {e}", file=sys.stderr)
        return []

def read_file(path: str) -> pl.DataFrame:
    """Reads a single file (Excel or CSV) into a Polars DataFrame."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    file_ext = path.lower()

    try:
        if file_ext.endswith('.csv'):
            return pl.read_csv(path)
        elif file_ext.endswith(('.xlsx', '.xls')):
            return pl.read_excel(path, engine='calamine')
        else:
            raise ValueError(f"Unsupported file format: {path}. Supported formats: .csv, .xlsx, .xls")
    except Exception as e:
        raise Exception(f"Error reading file {path}: {str(e)}")

def _read_file_with_progress(args):
    """Internal helper for parallel file reading."""
    path, file_num = args
    print(f"  Starting to read file {file_num}: {os.path.basename(path)}")
    start_time = datetime.now()
    df = read_file(path)
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"  Completed file {file_num} in {elapsed:.2f} seconds ({len(df)} rows)")
    return df

def read_files_in_parallel(file1_path: str, file2_path: str) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Reads two files in parallel, showing progress."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(_read_file_with_progress, (file1_path, 1))
        future2 = executor.submit(_read_file_with_progress, (file2_path, 2))
        df1 = future1.result()
        df2 = future2.result()
    return df1, df2

def get_filename_without_extension(path: str) -> str:
    """Extract filename without extension from full path."""
    return os.path.splitext(os.path.basename(path))[0]

def create_output_folder() -> str:
    """Create timestamped output folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"comparison_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name

def find_missing_rows(df1: pl.DataFrame, df2: pl.DataFrame, keys: list[str]) -> tuple:
    """Finds rows that are in one dataframe but not the other."""
    missing_in_df2 = df1.join(df2, on=keys, how='anti')
    missing_in_df1 = df2.join(df1, on=keys, how='anti')
    return missing_in_df2, missing_in_df1

def find_duplicates(df: pl.DataFrame, key_columns: list, file_name: str) -> pl.DataFrame:
    """Finds duplicate rows based on key columns."""
    return (
        df
        .with_row_index("_row_idx")
        .with_columns([
            pl.concat_str([pl.col(k).cast(pl.Utf8) for k in key_columns], separator="|").alias("_combined_key")
        ])
        .with_columns([
            pl.col("_combined_key").count().over("_combined_key").alias("_key_count")
        ])
        .filter(pl.col("_key_count") > 1)
        .with_columns(pl.lit(file_name).alias("source_file"))
        .drop(["_row_idx", "_combined_key", "_key_count"])
        .sort(key_columns)
    )

def find_mismatches_and_unpivot(df1: pl.DataFrame, df2: pl.DataFrame, keys: list[str], file1_name: str = "file1", file2_name: str = "file2") -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Finds rows with the same keys but different values, and creates a detailed unpivoted report.
    This is done in one pass to avoid multiple joins.
    """
    # Use dynamic suffix based on file2 name
    file2_suffix = f"_{file2_name}"
    joined = df1.join(df2, on=keys, how='inner', suffix=file2_suffix)
    non_key_cols = [col for col in df1.columns if col not in keys]

    if not non_key_cols:
        return pl.DataFrame(), pl.DataFrame()

    # Vectorized mismatch detection with dynamic column names
    mismatch_mask = pl.lit(False)
    for col in non_key_cols:
        col_file2 = f"{col}{file2_suffix}"
        if col_file2 in joined.columns:
            mismatch_mask = mismatch_mask | (pl.col(col).ne_missing(pl.col(col_file2)))

    mismatched_rows = joined.filter(mismatch_mask)

    if len(mismatched_rows) == 0:
        return pl.DataFrame(), pl.DataFrame()

    # Rename columns to include file names as prefixes for clarity
    file1_prefix = f"{file1_name}_"
    file2_prefix = f"{file2_name}_"

    # Create renamed columns for file1 (original columns)
    file1_renames = {col: f"{file1_prefix}{col}" for col in non_key_cols}
    # Create renamed columns for file2 (suffixed columns)
    file2_renames = {f"{col}{file2_suffix}": f"{file2_prefix}{col}" for col in non_key_cols}

    # Apply renaming to get clear column names with file prefixes
    renamed_mismatches = mismatched_rows.rename({**file1_renames, **file2_renames})

    # Create identifier for unpivoted report
    identifier_expr = pl.concat_str([pl.col(k).cast(pl.Utf8) for k in keys], separator="|")
    mismatched_data = renamed_mismatches.with_columns(identifier_expr.alias("Identifier"))

    # Update column lists with new names
    file1_cols_renamed = [f"{file1_prefix}{col}" for col in non_key_cols]
    file2_cols_renamed = [f"{file2_prefix}{col}" for col in non_key_cols]

    id_vars = ["Identifier"] + keys
    file1_melted = mismatched_data.select(id_vars + file1_cols_renamed).melt(
        id_vars=id_vars, variable_name="Column_Name", value_name="File1_Value"
    )

    file2_melted = mismatched_data.select(id_vars + file2_cols_renamed).melt(
        id_vars=id_vars, variable_name="Column_Name", value_name="File2_Value"
    )

    # Clean up column names in melted data by removing file prefixes for matching
    file1_melted = file1_melted.with_columns(
        pl.col("Column_Name").str.replace(f"^{file1_prefix}", "", literal=False).alias("Column_Name")
    )
    file2_melted = file2_melted.with_columns(
        pl.col("Column_Name").str.replace(f"^{file2_prefix}", "", literal=False).alias("Column_Name")
    )

    unpivoted_mismatches = (
        file1_melted.join(file2_melted, on=id_vars + ["Column_Name"])
        .filter(pl.col("File1_Value").ne_missing(pl.col("File2_Value")))
        .select([
            pl.col("Identifier"),
            pl.col("Column_Name"),
            (pl.col("File1_Value").cast(pl.Utf8) + " vs " + pl.col("File2_Value").cast(pl.Utf8)).alias("Comparison")
        ])
        .sort(["Identifier", "Column_Name"])
    )

    return renamed_mismatches, unpivoted_mismatches

def compare_dataframes(df1: pl.DataFrame, df2: pl.DataFrame, keys: list[str], file1_name: str = "file1", file2_name: str = "file2") -> tuple:
    """
    Compares two Polars DataFrames and returns a comprehensive analysis including missing rows,
    mismatches, duplicates, and an unpivoted mismatch report.
    """
    print("Comparing files...")
    sys.stdout.flush()
    start_time = time.time()

    df1_shape = df1.shape
    df2_shape = df2.shape

    for key in keys:
        if key not in df1.columns:
            raise ValueError(f"Key column '{key}' not found in first dataframe.")
        if key not in df2.columns:
            raise ValueError(f"Key column '{key}' not found in second dataframe.")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_missing = executor.submit(find_missing_rows, df1, df2, keys)
        future_duplicates1 = executor.submit(find_duplicates, df1, keys, file1_name)
        future_duplicates2 = executor.submit(find_duplicates, df2, keys, file2_name)
        future_mismatches = executor.submit(find_mismatches_and_unpivot, df1, df2, keys, file1_name, file2_name)

        missing_in_file2, missing_in_file1 = future_missing.result()
        duplicates_file1 = future_duplicates1.result()
        duplicates_file2 = future_duplicates2.result()
        mismatches, unpivoted_mismatches = future_mismatches.result()

    end_time = time.time()
    print(f"Comparison completed in {end_time - start_time:.2f} seconds")
    sys.stdout.flush()

    return (
        missing_in_file1,
        missing_in_file2,
        mismatches,
        duplicates_file1,
        duplicates_file2,
        unpivoted_mismatches,
        df1_shape,
        df2_shape
    )

def write_results_in_parallel(results_dict: dict, output_folder: str) -> list:
    """Writes multiple DataFrames to CSV files in parallel."""
    def write_single_file(args):
        df, filename = args
        if isinstance(df, pl.DataFrame) and len(df) > 0:
            filepath = os.path.join(output_folder, filename)
            df.write_csv(filepath)
            return filepath
        return None

    write_tasks = [
        (df, filename) for _, (df, filename) in results_dict.items()
        if df is not None and len(df) > 0
    ]

    saved_files = []
    if write_tasks:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(write_tasks)) as executor:
            futures = [executor.submit(write_single_file, task) for task in write_tasks]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    saved_files.append(result)
    return saved_files
