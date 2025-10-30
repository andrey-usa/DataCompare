# DataCompare - Excel & CSV Comparison Tool

A high-performance Python 3.14+ application for comparing Excel and CSV files using Polars for lightning-fast data processing. Supports both CLI and GUI interfaces with optimized ThreadPoolExecutor for exceptional performance.

## Features

- **Python 3.14+**: Modern Python with latest performance improvements
- **Multi-format support**: Excel (.xlsx, .xls) and CSV (.csv) files
- **Lightning-fast processing**: Pure Polars implementation for maximum performance
- **Optimized concurrency**: ThreadPoolExecutor leverages Polars' GIL-free Rust internals (~30x faster than ProcessPoolExecutor)
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

### Prerequisites

- **Python 3.14+** (required)
- **Git** (to clone the repository)

### Method 1: Using uv (Recommended - 10-100x faster)

**Why uv?** uv is a modern Python package manager written in Rust that's dramatically faster than pip, includes built-in Python version management, and provides reproducible builds via lockfiles.

```bash
# Step 1: Install uv (one-time setup)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Step 2: Clone and navigate to project
git clone https://github.com/andrey-usa/DataCompare.git
cd DataCompare

# Step 3: Install all dependencies (including dev tools)
uv sync

# Step 4: Run the application
uv run datacompare --gui
# or
uv run python src/data_compare.py --gui
```

**Features:**
- ✅ Automatic Python 3.14 installation if missing
- ✅ Reproducible builds via `uv.lock`
- ✅ No manual venv activation needed (`uv run` handles it)
- ✅ Parallel dependency resolution

### Method 2: Using pip (Traditional - works everywhere)

**Use this if:** You can't install uv, or prefer traditional Python tooling.

```bash
# Step 1: Ensure Python 3.14+ is installed
python --version  # Should show 3.14 or higher

# Step 2: Clone and navigate to project
git clone https://github.com/andrey-usa/DataCompare.git
cd DataCompare

# Step 3: Create virtual environment
python -m venv .venv

# Step 4: Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate

# Step 5: Install the package
pip install -e .

# Step 6: Install dev dependencies (optional)
pip install -r requirements-dev.txt

# Step 7: Run the application
datacompare --gui
# or
python src/data_compare.py --gui
```

**Note:** With pip, you must activate the virtual environment each time you open a new terminal. With uv, this is automatic.

### Verify Installation

```bash
# Using uv
uv run datacompare --help
uv run pytest -v

# Using pip (after activating the venv)
datacompare --help
pytest -v
```

## Usage

### Command Line Interface (CLI)

Compare files with key columns
```bash
uv run python src/data_compare.py file1.xlsx file2.xlsx --keys KeyColumn1,KeyColumn2
```
Compare files with different schemas using mapping
```bash
uv run python src/data_compare.py sales_prod.csv sales_dev.csv --mapping column_mapping.csv
```
Mixed approach - mapping file with additional keys
```bash
uv run python src/data_compare.py data1.csv data2.csv --keys ID,Name --mapping field_mapping.csv
```

**Note**: Use commas (`,`) as separators for multiple key columns - spaces in column names are supported.

#### CLI Flags

- `--json`: Emit a single machine-readable JSON summary to stdout (suppresses human-readable prints)
- `--strict`: Fail if any key column contains nulls in either file
- `-v` / `--verbose`: Enable verbose (DEBUG) logging
- `-q` / `--quiet`: Reduce logging to WARNING
- `--log-level LEVEL`: One of CRITICAL, ERROR, WARNING, INFO, DEBUG (overridden by -v/-q)

Examples:

```bash
# JSON summary (no extra prints)
uv run python src/data_compare.py --json --keys id tests/data/sales1.csv tests/data/sales2.csv

# Strict key validation + verbose logs
uv run python src/data_compare.py --strict --verbose --keys id tests/data/sales1.csv tests/data/sales2.csv

# Quiet logs
uv run python src/data_compare.py --quiet --keys id tests/data/sales1.csv tests/data/sales2.csv
```

The tool prints clickable file URIs for saved outputs, e.g. `file:///C:/path/to/Value_Unpivoted_Mismatches_...csv`.

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
```bash
# Using uv (recommended)
uv run python src/data_compare.py --gui

# Or using console script after installation
uv run datacompare --gui
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

- Python 3.14+
- polars>=1.34.0
- fastexcel>=0.16.0 (required for Excel file support)
- tkinterdnd2>=0.4.3 (for GUI drag-and-drop)

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

### Tests
```powershell
# Recommended
uv run pytest -v

# After pip installation + venv activation
pytest -v
```

### Lint & Format
```powershell
uvx ruff check .
uvx ruff format .
```

### Project Status
- Benchmarks have been retired; `benchmarks/benchmark_compare.py` remains as a placeholder only.
- Automated AI refactoring workflows are archived—see [AI_WORKFLOW.md](AI_WORKFLOW.md) for the historical note.

