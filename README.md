# DataCompare - Excel & CSV Comparison Tool

A high-performance Python application for comparing Excel and CSV files using Polars for lightning-fast data processing. Supports both CLI and GUI interfaces with parallel processing for optimal performance.

## Features

- **Multi-format support**: Excel (.xlsx, .xls) and CSV (.csv) files
- **Lightning-fast processing**: Pure Polars implementation for maximum performance
- **Parallel operations**: File loading, comparison, and writing operations run concurrently
- **Comprehensive analysis**: 
  - Missing rows in each file
  - Row-level mismatches
  - Value-level unpivoted mismatches
  - Duplicate key detection
- **Organized output**: Timestamped folders with descriptive file names
- **Dual interface**: Both command-line and graphical user interface
- **Performance monitoring**: Detailed timing information for each operation

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface (CLI)

Compare files with key columns
```commandline
python data_compare.py file1.xlsx file2.xlsx --keys KeyColumn1,KeyColumn2
```
Compare files with different schemas using mapping
```commandline
python data_compare.py sales_prod.csv sales_dev.csv --mapping column_mapping.csv
```
Mixed approach - mapping file with additional keys
```commandline
python data_compare.py data1.csv data2.csv --keys ID,Name --mapping field_mapping.csv
```

**Note**: Use commas (`,`) as separators for multiple key columns - spaces in column names are supported.

### Column Mapping File

When comparing files with different column names or schemas, use a CSV mapping file:

```csv
mapping_type,file1_column,file2_column
key,CustomerID,customer_id
key,ProductCode,product_code
data,CustomerName,customer_name
data,OrderDate,order_date
data,Amount,order_amount
ignore,InternalID,
ignore,,metadata_column
```

**Mapping Types:**
- `key`: Columns to use for joining/matching rows
- `data`: Columns to compare for differences  
- `ignore`: Columns to exclude from comparison

### Graphical User Interface (GUI)
```commandline
python data_compare.py --gui
```

The GUI provides:
- File browser with drag-and-drop support
- Column mapping file selection with validation
- Auto-populated key column suggestions
- Real-time comparison dashboard
- Direct links to open result files
- Performance metrics display

## Output Files

Each comparison creates a timestamped folder with the following files:
- `Missing_in_<file1_name>.csv` - Rows present in file2 but not in file1
- `Missing_in_<file2_name>.csv` - Rows present in file1 but not in file2  
- `Row_Mismatches_<file1>_vs_<file2>.csv` - Rows with same keys but different values
- `Value_Unpivoted_Mismatches_<file1>_vs_<file2>.csv` - Column-level differences in unpivoted format
- `Duplicates_in_<file_name>.csv` - Duplicate key entries (if found)

## Performance

- **CSV files**: Optimized for large datasets (1M+ rows)
- **Excel files**: Uses fastexcel engine for high-performance Excel processing
- **Parallel processing**: Concurrent file loading and comparison operations
- **Memory efficient**: Streaming operations where possible

## Requirements

- Python 3.8+
- polars
- pyarrow
- fastexcel (required for Excel file support)
- tkinterdnd2 (for GUI drag-and-drop)

## Example Output

```
--- Statistics ---
File 1 (sales_q1.csv): 1048556 rows, 12 columns
File 2 (sales_q2.csv): 1044022 rows, 12 columns
Rows missing in sales_q2: 20
Rows missing in sales_q1: 4567
Row Mismatches: 1673
Duplicate keys in sales_q1: 0
Duplicate keys in sales_q2: 14
Value (unpivoted) Mismatches: 1706
```

## Development

### AI-Powered Daily Refactoring

This project includes an automated AI refactoring workflow that runs daily to improve code quality and performance. See [AI_WORKFLOW.md](AI_WORKFLOW.md) for details on how the workflow operates and how to configure it.

Key features:
- Runs daily at 2 AM UTC
- Uses AI (aider) to apply Polars best practices
- Creates PRs only when tests pass
- Follows strict guidelines to keep changes minimal

To enable: Add `OPENAI_API_KEY` to repository secrets.

