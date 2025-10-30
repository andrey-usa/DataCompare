import concurrent.futures
import logging
import multiprocessing as mp
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import polars as pl

logger = logging.getLogger("datacompare")


class ColumnMapper:
    """Handles column mapping between two datasets with different schemas."""

    def __init__(self, mapping_file_path: str | None = None):
        self.mapping_file_path = mapping_file_path
        self.key_mappings: dict[str, str] = {}
        self.data_mappings: dict[str, str] = {}
        self.ignore_file1: list[str] = []
        self.ignore_file2: list[str] = []

        if mapping_file_path:
            self._load_mapping()

    def _load_mapping(self):
        """Load and parse the mapping file."""
        try:
            if not os.path.exists(self.mapping_file_path):
                raise FileNotFoundError(f"Mapping file not found: {self.mapping_file_path}")

            mapping_df = pl.read_csv(self.mapping_file_path)

            # Validate required columns
            required_cols = ["mapping_type", "file1_column", "file2_column"]
            missing_cols = [col for col in required_cols if col not in mapping_df.columns]
            if missing_cols:
                raise ValueError(f"Mapping file missing required columns: {missing_cols}")

            # Process each mapping row
            for row in mapping_df.iter_rows(named=True):
                mapping_type = row["mapping_type"].lower() if row["mapping_type"] else ""
                file1_col = row["file1_column"] if row["file1_column"] else None
                file2_col = row["file2_column"] if row["file2_column"] else None

                if mapping_type == "key":
                    if file1_col and file2_col:
                        self.key_mappings[file1_col] = file2_col
                elif mapping_type == "data":
                    if file1_col and file2_col:
                        self.data_mappings[file1_col] = file2_col
                elif mapping_type == "ignore":
                    if file1_col and not file2_col:
                        self.ignore_file1.append(file1_col)
                    elif file2_col and not file1_col:
                        self.ignore_file2.append(file2_col)

        except Exception as e:
            raise Exception(f"Error loading mapping file: {str(e)}")

    def apply_mapping(self, df1: pl.DataFrame, df2: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame, list[str]]:
        """Apply column mapping to both dataframes and return mapped key columns."""
        mapped_df1 = df1.clone()
        mapped_df2 = df2.clone()

        # Validate that mapped columns exist
        self._validate_columns(df1, df2)

        # Remove ignored columns
        if self.ignore_file1:
            existing_ignore_file1 = [col for col in self.ignore_file1 if col in mapped_df1.columns]
            if existing_ignore_file1:
                mapped_df1 = mapped_df1.drop(existing_ignore_file1)

        if self.ignore_file2:
            existing_ignore_file2 = [col for col in self.ignore_file2 if col in mapped_df2.columns]
            if existing_ignore_file2:
                mapped_df2 = mapped_df2.drop(existing_ignore_file2)

        # Apply data column mappings (rename file2 columns to match file1)
        rename_map_file2 = {}
        for file1_col, file2_col in self.data_mappings.items():
            if file2_col in mapped_df2.columns:
                rename_map_file2[file2_col] = file1_col

        if rename_map_file2:
            mapped_df2 = mapped_df2.rename(rename_map_file2)

        # Apply key column mappings (rename file2 key columns to match file1)
        key_rename_map_file2 = {}
        for file1_key, file2_key in self.key_mappings.items():
            if file2_key in mapped_df2.columns:
                key_rename_map_file2[file2_key] = file1_key

        if key_rename_map_file2:
            mapped_df2 = mapped_df2.rename(key_rename_map_file2)

        # Determine the final key columns (use file1 column names)
        mapped_key_columns = list(self.key_mappings.keys()) if self.key_mappings else []

        return mapped_df1, mapped_df2, mapped_key_columns

    def _validate_columns(self, df1: pl.DataFrame, df2: pl.DataFrame):
        """Validate that all mapped columns exist in their respective dataframes."""
        errors = []

        # Check file1 columns
        for file1_col in list(self.key_mappings.keys()) + list(self.data_mappings.keys()) + self.ignore_file1:
            if file1_col and file1_col not in df1.columns:
                errors.append(f"Column '{file1_col}' not found in file1")

        # Check file2 columns
        for file2_col in list(self.key_mappings.values()) + list(self.data_mappings.values()) + self.ignore_file2:
            if file2_col and file2_col not in df2.columns:
                errors.append(f"Column '{file2_col}' not found in file2")

        if errors:
            raise ValueError("Column mapping validation failed:\n" + "\n".join(errors))

    def get_mapping_summary(self) -> str:
        """Return a summary of the applied mappings."""
        summary = []
        if self.key_mappings:
            summary.append(f"Key mappings: {len(self.key_mappings)}")
            for f1, f2 in self.key_mappings.items():
                summary.append(f"  {f1} ↔ {f2}")

        if self.data_mappings:
            summary.append(f"Data mappings: {len(self.data_mappings)}")
            for f1, f2 in self.data_mappings.items():
                summary.append(f"  {f1} ↔ {f2}")

        if self.ignore_file1 or self.ignore_file2:
            summary.append(f"Ignored columns: {len(self.ignore_file1 + self.ignore_file2)}")
            for col in self.ignore_file1:
                summary.append(f"  {col} (file1)")
            for col in self.ignore_file2:
                summary.append(f"  {col} (file2)")

        return "\n".join(summary) if summary else "No mappings applied"


def get_file_header(path: str | Path) -> list[str]:
    """Quickly reads the header of a CSV or Excel file without loading the entire file."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        suffix = p.suffix.lower()
        if suffix == ".csv":
            return pl.read_csv(p, n_rows=0, ignore_errors=True).columns
        elif suffix in (".xlsx", ".xls"):
            # Use Polars' native Excel reading for headers
            return pl.read_excel(p, engine="calamine", read_options={"n_rows": 0}).columns
        else:
            # Basic fallback for other potential text files
            return pl.read_csv(p, n_rows=0, separator="\t", ignore_errors=True).columns
    except Exception as e:
        print(f"Could not read header from {p.name}: {e}", file=sys.stderr)
        return []


def read_file(path: str | Path) -> pl.DataFrame:
    """Reads a single file (Excel or CSV) into a Polars DataFrame."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    file_ext = p.suffix.lower()

    try:
        if file_ext == ".csv":
            return pl.read_csv(p)
        elif file_ext in (".xlsx", ".xls"):
            return pl.read_excel(p, engine="calamine")
        else:
            raise ValueError(f"Unsupported file format: {p}. Supported formats: .csv, .xlsx, .xls")
    except Exception as e:
        raise Exception(f"Error reading file {p}: {str(e)}")


def _read_file_with_progress(args):
    """Internal helper for parallel file reading."""
    path, file_num = args
    logger.info(f"  Starting to read file {file_num}: {Path(path).name}")
    start_time = datetime.now()
    df = read_file(path)
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"  Completed file {file_num} in {elapsed:.2f} seconds ({len(df)} rows)")
    return df


def read_files_in_parallel(file1_path: str, file2_path: str) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Reads two files in parallel using ThreadPoolExecutor.

    ThreadPoolExecutor is used instead of ProcessPoolExecutor because:
    - Polars releases the GIL internally (written in Rust), allowing true parallelism
    - No process spawning overhead (~30x faster for typical workloads)
    - No pickling/unpickling overhead for data transfer
    - Shared memory access is more efficient
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(_read_file_with_progress, (file1_path, 1))
        future2 = executor.submit(_read_file_with_progress, (file2_path, 2))
        df1 = future1.result()
        df2 = future2.result()
    return df1, df2


def get_filename_without_extension(path: str | Path) -> str:
    """Extract filename without extension from full path."""
    return Path(path).stem


def create_output_folder() -> str:
    """Create timestamped output folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = Path(f"comparison_{timestamp}")
    folder.mkdir(exist_ok=True)
    return str(folder)


def find_missing_rows(df1: pl.DataFrame, df2: pl.DataFrame, keys: list[str]) -> tuple:
    """Finds rows that are in one dataframe but not the other."""
    missing_in_df2 = df1.join(df2, on=keys, how="anti")
    missing_in_df1 = df2.join(df1, on=keys, how="anti")
    return missing_in_df2, missing_in_df1


def find_duplicates(df: pl.DataFrame, key_columns: list[str], file_name: str) -> pl.DataFrame:
    """Finds duplicate rows based on key columns."""
    return (
        df.with_row_index("_row_idx")
        .with_columns(
            [pl.concat_str([pl.col(k).cast(pl.Utf8) for k in key_columns], separator="|").alias("_combined_key")]
        )
        .with_columns([pl.col("_combined_key").count().over("_combined_key").alias("_key_count")])
        .filter(pl.col("_key_count") > 1)
        .with_columns(pl.lit(file_name).alias("source_file"))
        .drop(["_row_idx", "_combined_key", "_key_count"])
        .sort(key_columns)
    )


def find_mismatches_and_unpivot(
    df1: pl.DataFrame, df2: pl.DataFrame, keys: list[str], file1_name: str = "file1", file2_name: str = "file2"
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Finds rows with the same keys but different values, and creates a detailed unpivoted report.
    This is done in one pass to avoid multiple joins.
    """
    # Use dynamic suffix based on file2 name
    file2_suffix = f"_{file2_name}"
    joined = df1.join(df2, on=keys, how="inner", suffix=file2_suffix)
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
    file1_melted = mismatched_data.select(id_vars + file1_cols_renamed).unpivot(
        index=id_vars, variable_name="Column_Name", value_name="File1_Value"
    )

    file2_melted = mismatched_data.select(id_vars + file2_cols_renamed).unpivot(
        index=id_vars, variable_name="Column_Name", value_name="File2_Value"
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
        .select(
            [
                pl.col("Identifier"),
                pl.col("Column_Name"),
                (pl.col("File1_Value").cast(pl.Utf8) + " vs " + pl.col("File2_Value").cast(pl.Utf8)).alias(
                    "Comparison"
                ),
            ]
        )
        .sort(["Identifier", "Column_Name"])
    )

    return renamed_mismatches, unpivoted_mismatches


class CompareResults(NamedTuple):
    missing_in_file1: pl.DataFrame
    missing_in_file2: pl.DataFrame
    mismatches: pl.DataFrame
    duplicates_file1: pl.DataFrame
    duplicates_file2: pl.DataFrame
    unpivoted_mismatches: pl.DataFrame
    df1_shape: tuple[int, int]
    df2_shape: tuple[int, int]


def compare_dataframes(
    df1: pl.DataFrame,
    df2: pl.DataFrame,
    keys: list[str],
    file1_name: str = "file1",
    file2_name: str = "file2",
    mapping_file: str | None = None,
    strict: bool = False,
) -> CompareResults:
    """
    Compares two Polars DataFrames and returns a comprehensive analysis including missing rows,
    mismatches, duplicates, and an unpivoted mismatch report.
    """
    logger.info("Comparing files...")
    # Use perf_counter for precise duration measurement
    start_time = time.perf_counter()

    # Apply column mapping if provided
    column_mapper = None
    if mapping_file:
        logger.info("Applying column mapping...")
        column_mapper = ColumnMapper(mapping_file)
        df1, df2, mapped_keys = column_mapper.apply_mapping(df1, df2)

        # Use mapped keys if available, otherwise fall back to provided keys
        if mapped_keys:
            keys = mapped_keys
            logger.info(f"Using mapped key columns: {', '.join(keys)}")

        logger.info("Mapping applied successfully.")
        logger.info("Mapping summary:\n%s", column_mapper.get_mapping_summary())

    df1_shape = df1.shape
    df2_shape = df2.shape

    for key in keys:
        if key not in df1.columns:
            raise ValueError(f"Key column '{key}' not found in first dataframe.")
        if key not in df2.columns:
            raise ValueError(f"Key column '{key}' not found in second dataframe.")

    if strict:
        # In strict mode, disallow nulls in key columns
        for key in keys:
            if df1.select(pl.col(key).is_null().any()).item():
                raise ValueError(f"Strict mode: Null values found in key column '{key}' of first dataframe.")
            if df2.select(pl.col(key).is_null().any()).item():
                raise ValueError(f"Strict mode: Null values found in key column '{key}' of second dataframe.")

    # ThreadPoolExecutor provides optimal performance for Polars operations
    # (Polars releases GIL internally, avoiding process spawning overhead)
    max_workers = min(4, mp.cpu_count())
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_missing = executor.submit(find_missing_rows, df1, df2, keys)
        future_duplicates1 = executor.submit(find_duplicates, df1, keys, file1_name)
        future_duplicates2 = executor.submit(find_duplicates, df2, keys, file2_name)
        future_mismatches = executor.submit(find_mismatches_and_unpivot, df1, df2, keys, file1_name, file2_name)

        missing_in_file2, missing_in_file1 = future_missing.result()
        duplicates_file1 = future_duplicates1.result()
        duplicates_file2 = future_duplicates2.result()
        mismatches, unpivoted_mismatches = future_mismatches.result()

    end_time = time.perf_counter()
    logger.info("Comparison completed in %.2f seconds", end_time - start_time)

    return CompareResults(
        missing_in_file1,
        missing_in_file2,
        mismatches,
        duplicates_file1,
        duplicates_file2,
        unpivoted_mismatches,
        df1_shape,
        df2_shape,
    )


def _write_single_file(args: tuple[pl.DataFrame | None, str, str]) -> str | None:
    """Helper for parallel file writing.

    Kept at module level for potential process-based execution; currently used with threads.
    """
    df, filename, output_folder = args
    if isinstance(df, pl.DataFrame) and len(df) > 0:
        filepath = Path(output_folder) / filename
        df.write_csv(str(filepath))
        return str(filepath)
    return None


def write_results_in_parallel(
    results_dict: dict[str, tuple[pl.DataFrame | None, str]], output_folder: str
) -> list[str]:
    """Writes multiple DataFrames to CSV files in parallel using ThreadPoolExecutor."""
    write_tasks = [
        (df, filename, output_folder) for _, (df, filename) in results_dict.items() if df is not None and len(df) > 0
    ]

    saved_files = []
    if write_tasks:
        # ThreadPoolExecutor is optimal for I/O operations (file writing)
        max_workers = min(len(write_tasks), mp.cpu_count())
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_write_single_file, task) for task in write_tasks]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    saved_files.append(result)
    return saved_files
